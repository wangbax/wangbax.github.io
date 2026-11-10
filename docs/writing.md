# 写一篇文章

在 `content/posts/` 新建一个 Markdown 文件，例如 `my-first-post.md`：

````markdown
---
title: 我的第一篇文章
date: 2026-11-10 20:00:00
category: 开发笔记
summary: 用一句话介绍这篇文章。
---

## 为什么写这篇

直接用 Markdown 写正文，支持标题、列表、表格、图片和代码块。

```python
print("Hello, world!")
```
````

`title`、`date` 必填；`category`、`summary` 可以省略，摘要默认取首段。日期未写时区时按北京时间处理。文件名使用小写英文、数字和连字符。

提交并合并到 `main` 后，网站会自动生成文章页、首页最新手记、归档和搜索索引，并发布到 ECS。不需要手动编辑 HTML 或文章列表。

CI 会把生成的 HTML、合并后的 CSS 和搜索索引自动 commit 回同一个 `main` 分支；产物没有变化时不新增 commit。删除文章时，对应的旧 HTML 也会删除。本地继续修改前，先运行 `git pull --ff-only` 获取这些自动提交。

文章地址默认是 `/年/月/日/文件名/`。旧文章已保留原地址；需要固定地址时，在文件头增加 `permalink: /2026/11/10/my-first-post/`，以后改标题或文件名也不会改变链接。修改文章可增加 `updated` 日期。

图片放在 `images/` 中，正文使用 `![图片说明](/images/example.png)`；也支持图片的完整网络地址。图片会使用懒加载，现有图片继续使用压缩后的 WebP 资源。

## 本地预览

需要 Python 3.12 或更新版本。首次准备：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

生成页面并启动预览：

```sh
.venv/bin/python scripts/render_site.py
.venv/bin/python -m http.server 8000
```

打开 `http://localhost:8000`。修改 Markdown 后重新运行生成命令，再刷新页面。
