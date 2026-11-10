from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from markdown_posts import load_posts, render_markdown


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.text = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, value):
        self.text.append(value)


class MarkdownPostsTest(unittest.TestCase):
    def test_markdown_features_and_nested_code(self):
        source = '''## 中文标题

正文 **加粗**、`inline()` 和 [链接](https://example.com) 。

| 字段 | 值 |
| --- | --- |
| a | b |

* 操作步骤

    ```xml
    <activity android:name=".MainActivity">
        <intent-filter />
    </activity>
    ```

## 中文标题

## 保留旧链接 {#Old-Anchor}
'''
        output = render_markdown(source)
        parsed = Elements(output)
        headings = [attrs["id"] for tag, attrs in parsed.tags if tag == "h2"]
        self.assertEqual(headings, ["中文标题", "中文标题_1", "Old-Anchor"])
        self.assertIn(("strong", {}), parsed.tags)
        self.assertEqual(sum(tag == "figure" for tag, _ in parsed.tags), 1)
        self.assertEqual(sum(tag == "table" for tag, _ in parsed.tags), 2)
        self.assertIn('<activity android:name=".MainActivity">', "".join(parsed.text))
        self.assertNotIn("<activity ", output)
        self.assertIn("class=\"highlight xml\"", output)
        self.assertIn("&lt;intent-filter", output)

    def test_unknown_language_and_code_escaping(self):
        output = render_markdown('```not-a-language\n<script>alert("test")</script>\n```')
        self.assertIn("&lt;script&gt;", output)
        self.assertNotIn("<script>", output)
        self.assertIn("figure", output)

    def test_markdown_images_keep_lazy_loading_and_webp(self):
        from render_site import article_images
        output = article_images(render_markdown('![外部图片](https://example.com/image.png)\n\n![原有图片](/images/2017/20170424121603.png)'))
        parsed = Elements(output)
        images = [attrs for tag, attrs in parsed.tags if tag == "img"]
        self.assertEqual(len(images), 2)
        self.assertTrue(all(attrs["loading"] == "lazy" and attrs["decoding"] == "async" for attrs in images))
        self.assertEqual(images[0]["alt"], "外部图片")
        self.assertIn("width", images[1])
        self.assertTrue(any(tag == "source" and attrs["type"] == "image/webp" for tag, attrs in parsed.tags))

    def test_metadata_and_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "my-first-post.md"
            path.write_text('---\ntitle: 第一篇\ndate: 2026-11-10\n---\n\n## 标题\n\n这是**正文**。\n')
            post, = load_posts(directory)
            self.assertEqual(post["url"], "/2026/11/10/my-first-post/")
            self.assertEqual(post["published"], "2026-11-10T00:00:00+08:00")
            self.assertEqual(post["updated"], post["published"])
            self.assertEqual(post["category"], "开发笔记")
            self.assertEqual(post["summary"], "这是正文。")

    def test_invalid_metadata_stops_the_build(self):
        cases = [
            "title: test", "title: test\ndate: impossible",
            "title: test\ntitle: duplicated\ndate: 2026-11-10",
            "title: test\ndate: 2026-11-10\nupdated: 2026-01-01",
            "title: test\ndate: 2026-11-10\npermalink: /../../index.html",
            "title: test\ndate: 2026-11-10\ncategory: [one, two]",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.md"
            for metadata in cases:
                with self.subTest(metadata=metadata):
                    path.write_text(f"---\n{metadata}\n---\n\n正文")
                    with self.assertRaisesRegex(ValueError, "invalid.md"):
                        load_posts(directory)

    def test_duplicate_permalink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ["one", "two"]:
                (Path(directory) / (name + ".md")).write_text('---\ntitle: test\ndate: 2026-11-10\npermalink: /2026/11/10/same/\n---\n正文')
            with self.assertRaisesRegex(ValueError, "文章地址重复"):
                load_posts(directory)

    def test_post_order_uses_dates_instead_of_file_names(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, date in [("aaa-new", "2026-11-10"), ("zzz-old", "2025-01-01")]:
                (Path(directory) / (name + ".md")).write_text(f"---\ntitle: {name}\ndate: {date}\n---\n正文")
            self.assertEqual([post["slug"] for post in load_posts(directory)], ["aaa-new", "zzz-old"])

    def test_markdown_only_changes_reach_the_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["scripts", "css", "js", "images"]:
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "content", root / "content", ignore=shutil.ignore_patterns("posts"))
            posts = root / "content/posts"
            posts.mkdir()
            def post(name, date):
                (posts / (name + ".md")).write_text(f"---\ntitle: {name}\ndate: {date}\n---\n\n## 正文\n\n可搜索的内容-{name}\n")
            post("old-post", "2017-01-01")
            def git(*args):
                return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args], stderr=subprocess.STDOUT, text=True)
            git("init", "-q")
            git("add", ".")
            git("-c", "user.name=Test fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", "test fixture\n\nAssisted-by: Cindy (https://cindy.app)")
            post("new-post", "2026-11-10")
            git("add", "content/posts/new-post.md")
            def package():
                subprocess.run([sys.executable, "scripts/package_site.py", "--site-url", "https://www.wangbaxai.top"], cwd=root, check=True, stdout=subprocess.PIPE)
                subprocess.run([sys.executable, "scripts/check_site.py", ".release/site.tar.gz"], cwd=root, check=True, stdout=subprocess.PIPE)
                with tarfile.open(root / ".release/site.tar.gz") as archive:
                    return {item.name: archive.extractfile(item).read() for item in archive.getmembers()}
            files = package()
            self.assertIn("2026/11/10/new-post/index.html", files)
            self.assertNotIn("2026/11/10/new-post/index.html", git("ls-files").splitlines())
            self.assertIn(b"new-post", files["index.html"])
            self.assertIn(b"new-post", files["archives/index.html"])
            self.assertEqual(json.loads(files["search.json"])[0]["title"], "new-post")
            self.assertFalse(any(name.startswith(("content/", "scripts/")) or name.endswith(".md") for name in files))
            (posts / "old-post.md").unlink()
            files = package()
            self.assertNotIn("2017/01/01/old-post/index.html", files, "Removed posts must not remain in the release")
            self.assertNotIn(b"old-post", files["search.json"])


if __name__ == "__main__":
    unittest.main()
