from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sync_generated


class SyncGeneratedTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "work"
        self.remote = Path(self.directory.name) / "origin.git"
        self.root.mkdir()
        self.git_call(self.remote.parent, "init", "--bare", "-q", str(self.remote))
        self.git_call(self.root, "init", "-qb", "main")
        self.git_call(self.root, "config", "user.name", "Test fixture")
        self.git_call(self.root, "config", "user.email", "fixture@example.invalid")
        self.git_call(self.root, "config", "core.hooksPath", "/dev/null")
        self.git_call(self.root, "config", "commit.gpgsign", "false")
        for name, content in {"README.md": "source", "index.html": "old index",
                              "2017/01/01/removed-post/index.html": "old article"}.items():
            self.write(name, content)
        self.git_call(self.root, "add", ".")
        self.commit(self.root, "source fixture")
        self.git_call(self.root, "remote", "add", "origin", str(self.remote))
        self.git_call(self.root, "push", "-q", "origin", "main")
        self.source_sha = self.git_call(self.root, "rev-parse", "HEAD")
        self.outputs = {"index.html", "2026/11/10/new-post/index.html", "css/app.css", "search.json"}

    @staticmethod
    def git_call(root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE).strip()

    def commit(self, root, message):
        self.git_call(root, "commit", "-qm", message + "\n\nAssisted-by: Cindy (https://cindy.app)")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def generate(self):
        for name in self.outputs:
            self.write(name, "generated " + name)

    def remote_tip(self):
        return self.git_call(self.remote, "rev-parse", "refs/heads/main")

    def advance_main(self):
        other = Path(self.directory.name) / "other"
        self.git_call(self.root.parent, "clone", "-qb", "main", str(self.remote), str(other))
        self.git_call(other, "config", "user.name", "Test fixture")
        self.git_call(other, "config", "user.email", "fixture@example.invalid")
        self.git_call(other, "config", "core.hooksPath", "/dev/null")
        self.git_call(other, "config", "commit.gpgsign", "false")
        (other / "README.md").write_text("new source from another commit")
        self.git_call(other, "add", "README.md")
        self.commit(other, "next source")
        self.git_call(other, "push", "-q", "origin", "main")
        return self.git_call(other, "rev-parse", "HEAD")

    def test_add_update_remove_only_generated_files(self):
        self.generate()
        self.write("README.md", "unrelated unstaged source")
        result = sync_generated.sync_generated(self.root, self.source_sha, self.outputs)
        self.assertTrue(result["ready"])
        self.assertTrue(result["changed"])
        self.assertEqual(self.remote_tip(), result["commit"])
        self.assertEqual(self.git_call(self.remote, "rev-parse", "main^"), self.source_sha)
        names = self.git_call(self.remote, "diff-tree", "--no-commit-id", "--name-only", "-r", "main").splitlines()
        self.assertEqual(set(names), self.outputs | {"2017/01/01/removed-post/index.html"})
        self.assertEqual(self.git_call(self.remote, "show", "main:README.md"), "source")
        self.assertIn("Source-commit: " + self.source_sha, self.git_call(self.remote, "log", "-1", "--format=%B", "main"))
        self.assertIn("Assisted-by: Cindy", self.git_call(self.remote, "log", "-1", "--format=%B", "main"))
        self.assertEqual(self.git_call(self.remote, "log", "-1", "--format=%an", "main"), "github-actions[bot]")
        self.assertEqual(self.git_call(self.root, "diff", "--name-only"), "README.md")

    def test_unchanged_outputs_do_not_add_a_commit(self):
        outputs = {"index.html", "2017/01/01/removed-post/index.html"}
        result = sync_generated.sync_generated(self.root, self.source_sha, outputs)
        self.assertTrue(result["ready"])
        self.assertFalse(result["changed"])
        self.assertEqual(self.remote_tip(), self.source_sha)

    def test_stale_build_does_not_stage_or_push(self):
        self.generate()
        latest = self.advance_main()
        result = sync_generated.sync_generated(self.root, self.source_sha, self.outputs)
        self.assertFalse(result["ready"])
        self.assertEqual(self.remote_tip(), latest)
        self.assertEqual(self.git_call(self.root, "diff", "--cached", "--name-only"), "")

    def test_push_race_keeps_the_newer_main(self):
        self.generate()
        original = sync_generated.git
        latest = None
        def concurrent_git(root, *args):
            nonlocal latest
            if args[0] == "push":
                latest = self.advance_main()
            return original(root, *args)
        with patch.object(sync_generated, "git", side_effect=concurrent_git):
            result = sync_generated.sync_generated(self.root, self.source_sha, self.outputs)
        self.assertFalse(result["ready"])
        self.assertEqual(self.remote_tip(), latest)

    def test_successful_push_with_lost_acknowledgement_is_recognized(self):
        self.generate()
        original = sync_generated.git
        def ambiguous_git(root, *args):
            result = original(root, *args)
            if args[0] == "push":
                raise subprocess.CalledProcessError(128, ["git", "push"], stderr="connection closed after push")
            return result
        with patch.object(sync_generated, "git", side_effect=ambiguous_git):
            result = sync_generated.sync_generated(self.root, self.source_sha, self.outputs)
        self.assertTrue(result["ready"])
        self.assertEqual(self.remote_tip(), result["commit"])

    def test_push_errors_are_not_silently_ignored(self):
        self.generate()
        original = sync_generated.git
        def rejected_git(root, *args):
            if args[0] == "push":
                raise subprocess.CalledProcessError(128, ["git", "push"], stderr="permission denied")
            return original(root, *args)
        with patch.object(sync_generated, "git", side_effect=rejected_git):
            with self.assertRaises(subprocess.CalledProcessError):
                sync_generated.sync_generated(self.root, self.source_sha, self.outputs)
        self.assertEqual(self.remote_tip(), self.source_sha)

    def test_sources_and_pre_staged_changes_are_rejected(self):
        self.generate()
        with self.assertRaisesRegex(ValueError, "不是有效的生成文件"):
            sync_generated.sync_generated(self.root, self.source_sha, self.outputs | {"README.md"})
        self.git_call(self.root, "add", "index.html")
        with self.assertRaisesRegex(ValueError, "暂存区"):
            sync_generated.sync_generated(self.root, self.source_sha, self.outputs)
        self.assertEqual(self.remote_tip(), self.source_sha)


if __name__ == "__main__":
    unittest.main()
