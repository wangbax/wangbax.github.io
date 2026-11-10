#!/usr/bin/env python3
"""Commit generated pages back to main from the publishing workflow."""

import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent.parent
FIXED_OUTPUTS = {"index.html", "404.html", "about/index.html", "project/index.html",
                 "archives/index.html", "search/index.html", "css/app.css", "search.json"}
POST_PAGE = re.compile(r"[0-9]{4}/[0-9]{2}/[0-9]{2}/[a-z0-9]+(?:-[a-z0-9]+)*/index\.html")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE).strip()


def remote_head(root):
    return git(root, "ls-remote", "--exit-code", "origin", "refs/heads/main").split()[0]


def is_generated(name):
    return name in FIXED_OUTPUTS or POST_PAGE.fullmatch(name) is not None


def sync_generated(root, source_sha, outputs):
    if git(root, "rev-parse", "HEAD") != source_sha:
        raise ValueError("当前 checkout 与本次构建的源码版本不一致，停止回写。")
    if git(root, "diff", "--cached", "--name-only"):
        raise ValueError("暂存区已有改动，停止回写，避免提交非生成文件。")
    if remote_head(root) != source_sha:
        print("main 已有更新，跳过本次旧构建的回写和部署。")
        return {"ready": False, "commit": source_sha, "changed": False}

    outputs = set(outputs)
    if not outputs:
        raise ValueError("生成文件列表为空，停止回写。")
    for name in outputs:
        path = root / name
        if not is_generated(name) or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("不是有效的生成文件：" + name)
    tracked = set(git(root, "ls-files", "-z").split("\0"))
    stale = {name for name in tracked if is_generated(name)} - outputs
    if stale:
        git(root, "rm", "--", *sorted(stale))
    git(root, "add", "--", *sorted(outputs))
    if not git(root, "diff", "--cached", "--name-only"):
        print("生成产物没有变化，无需新增 commit。")
        return {"ready": True, "commit": source_sha, "changed": False}

    message = ("chore: sync generated site\n\nSource-commit: " + source_sha
               + "\n\nAssisted-by: Cindy (https://cindy.app)")
    git(root, "-c", "user.name=github-actions[bot]", "-c",
        "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "-c", "commit.gpgsign=false", "commit", "-m", message)
    commit = git(root, "rev-parse", "HEAD")
    try:
        git(root, "push", "origin", "HEAD:refs/heads/main")
    except subprocess.CalledProcessError:
        latest = remote_head(root)
        if latest == commit:
            pass  # The server accepted the push before the connection failed.
        elif latest != source_sha:
            print("回写前 main 已有新提交，跳过本次旧构建的回写和部署。")
            return {"ready": False, "commit": source_sha, "changed": False}
        else:
            raise
    print("生成产物已提交到 main：" + commit)
    return {"ready": True, "commit": commit, "changed": True}


def main():
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_EVENT_NAME") not in {"push", "workflow_dispatch"}):
        raise SystemExit("产物回写仅允许由 main 的 GitHub Actions 发布流程执行。")
    from render_site import PAGES, build_site
    build_site()
    result = sync_generated(ROOT, os.environ["GITHUB_SHA"], set(PAGES) | {"css/app.css", "search.json"})
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write("ready=" + str(result["ready"]).lower() + "\n")
        output.write("commit=" + result["commit"] + "\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        raise SystemExit("产物回写失败：" + (detail or str(error))) from error
