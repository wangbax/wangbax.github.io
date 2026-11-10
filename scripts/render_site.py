#!/usr/bin/env python3
"""Render the personal website from article fragments and site content."""

import argparse
from collections import Counter
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SITE = json.loads((CONTENT / "site.json").read_text())
POSTS = json.loads((CONTENT / "posts.json").read_text())
PAGES = json.loads((CONTENT / "pages.json").read_text())
POST_BY_URL = {post["url"]: post for post in POSTS}
ARROW = '<span class="arrow" aria-hidden="true">↗</span>'
SEARCH_ICON = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 4.5 4.5"/></svg>'


def e(value):
    return escape(str(value), quote=True)


def asset(path):
    digest = hashlib.sha256((ROOT / path.lstrip("/")).read_bytes()).hexdigest()[:12]
    return path + "?v=" + digest


class ArticleInfo(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.headings = []
        self.text = []
        self.current = None
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"h2", "h3", "h4"} and attrs.get("id"):
            self.current = {"id": attrs["id"], "level": int(tag[1]), "parts": []}

    def handle_data(self, data):
        self.text.append(data)
        if self.current is not None:
            self.current["parts"].append(data)

    def handle_endtag(self, tag):
        if self.current is not None and tag == "h" + str(self.current["level"]):
            self.current["name"] = "".join(self.current.pop("parts")).strip()
            self.headings.append(self.current)
            self.current = None


def header(active=""):
    links = [("projects", "/#projects", "项目"), ("notes", "/archives/", "文章"), ("about", "/about/", "关于")]
    nav = "".join(
        '<a href="{}"{}>{}</a>'.format(e(url), ' aria-current="page"' if key == active else "", label)
        for key, url, label in links
    )
    return f'''<a class="skip-link" href="#main">跳到正文</a>
<header class="site-header"><div class="wrap top">
  <a class="brand" href="/" aria-label="wangbax 首页"><img class="mark profile-image" src="{e(SITE['avatar'])}" width="29" height="29" alt="">wangbax</a>
  <nav class="nav" aria-label="主导航">{nav}<button class="search-trigger" type="button" data-open-search aria-label="搜索文章">{SEARCH_ICON}</button><a class="github desktop" href="{e(SITE['github'])}" target="_blank" rel="noopener">GitHub ↗</a></nav>
</div></header>'''


def footer():
    return f'''<footer class="wrap foot"><span class="signature">© {SITE['copyright_year']} wangbax</span><div><a href="/tags/">标签</a><a href="/categories/">分类</a><a href="/about/">关于我</a><a href="{e(SITE['github'])}" target="_blank" rel="noopener">GitHub ↗</a></div></footer>'''


def search_form(standalone=False):
    field_id = "page-search" if standalone else "dialog-search"
    return f'''<div class="search-widget" data-search-widget>
  <label class="sr-only" for="{field_id}">搜索文章</label>
  <input id="{field_id}" data-search-input type="search" placeholder="搜索标题、正文或关键词…" autocomplete="off" spellcheck="false">
  <p class="search-status" data-search-status aria-live="polite">输入关键词，查找开发手记。</p>
  <div class="search-results" data-search-results></div>
</div>'''


def search_dialog():
    return '''<dialog class="search-dialog" id="site-search" aria-labelledby="search-title">
<div class="search-dialog-head"><h2 id="search-title">找一篇手记</h2><form method="dialog"><button type="submit" class="search-close" aria-label="关闭搜索">×</button></form></div>
''' + search_form() + '<p class="search-key-hint">按 Esc 关闭</p></dialog>'


def document(title, url, body, active="", description=None, post=None, home=False):
    description = description or SITE["description"]
    page_title = "wangbax · 在代码与灵感之间" if home else title + " | wangbax"
    canonical = SITE["origin"] + url
    article_meta = ""
    if post:
        article_meta = f'<meta property="article:published_time" content="{e(post["published"])}"><meta property="article:modified_time" content="{e(post["updated"])}">'
    scripts = f'<script src="{asset("/js/site.js")}" defer></script>'
    if home:
        scripts += f'<script src="{asset("/js/planet.js")}" defer></script>'
    return f'''<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#faf7f1"><title>{e(page_title)}</title>
<meta name="description" content="{e(description)}"><meta name="author" content="wangbax">
<link rel="canonical" href="{e(canonical)}"><link rel="icon" type="image/png" href="{e(SITE['avatar'])}">
<meta property="og:type" content="{'article' if post else 'website'}"><meta property="og:site_name" content="wangbax"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(canonical)}"><meta property="og:image" content="{e(SITE['origin'] + SITE['avatar'])}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(description)}">{article_meta}
<link rel="stylesheet" href="{asset('/css/site.css')}"><link rel="stylesheet" href="{asset('/css/pages.css')}">{scripts}
</head><body class="{'home-page' if home else 'reading-page' if post else 'collection-page'}">
{header(active)}{body}{footer()}{search_dialog()}
</body></html>
'''


def projects():
    icons = [
        '<circle cx="16" cy="16" r="12"/><circle cx="19" cy="14" r="7"/><circle cx="12" cy="22" r="2" fill="currentColor"/>',
        '<path d="M7 5H16C24 5 27 8 27 16V25H18C10 25 7 22 7 14V5Z"/><path d="M5 11H21V28" opacity=".45"/>',
    ]
    return '<div class="project-grid">' + "".join(
        f'''<a class="project" href="{e(project['url'])}" target="_blank" rel="noopener"><div class="project-meta"><svg class="icon" viewBox="0 0 32 32" fill="none" stroke="currentColor" aria-hidden="true">{icons[index % 2]}</svg><span class="stack">{e(project['stack'].upper())}</span></div><h3>{e(project['name'])}</h3><p>{e(project['description'])}</p>{ARROW}</a>'''
        for index, project in enumerate(SITE["projects"])
    ) + "</div>"


def note(post, title=None):
    category = post["categories"][-1]["name"] if post["categories"] else "开发手记"
    return f'''<a class="note" href="{e(post['url'])}"><time datetime="{e(post['published'][:10])}">{post['published'][:10].replace('-', '.')}</time><h3>{e(title or post['title'])}</h3><span class="category">{e(category)}</span>{ARROW}</a>'''


def home_page():
    notes = "".join(note(POST_BY_URL[item["url"]], item["title"]) for item in SITE["notes"])
    body = f'''<main id="main" class="wrap">
<section class="hero" aria-labelledby="home-name"><div class="space" aria-hidden="true"><canvas id="universe"></canvas></div><div class="hero-content"><div class="eyebrow reveal">A SPACE FOR CURIOSITY</div><h1 class="reveal" id="home-name">wangbax<span>.</span></h1><h2 class="reveal">在代码与灵感之间。</h2><p class="reveal">你好，欢迎来到我的一小片宇宙。<br>这里有做过的小项目，也有开发路上的问题与发现。</p><div class="hero-actions reveal"><a class="primary" href="#projects">探索项目 {ARROW}</a><a class="secondary" href="#notes">读一篇手记 ↓</a></div></div><div class="orbit-label" aria-hidden="true">IDEAS IN ORBIT</div><div class="hero-foot">保持耐心，持续探索。 &nbsp; / &nbsp; BE PATIENT, BE LEARNING.</div></section>
<section class="work" id="projects"><div class="section-head"><h2>探索与作品 <small>PROJECTS</small></h2><a href="{e(SITE['github'])}?tab=repositories" target="_blank" rel="noopener">全部项目 ↗</a></div>{projects()}</section>
<section class="notes" id="notes"><div class="section-head"><h2>沿途的手记 <small>NOTES</small></h2><a href="/archives/">文章归档 ↗</a></div>{notes}</section>
</main>'''
    return document("wangbax · 在代码与灵感之间", "/", body, home=True)


def toc_links(headings):
    if not headings:
        return ""
    minimum = min(item["level"] for item in headings)
    return '<ol class="toc-list">' + "".join(
        f'<li class="toc-level-{min(item["level"] - minimum, 2)}"><a href="#{e(quote(item["id"]))}">{e(item["name"])}</a></li>'
        for item in headings
    ) + "</ol>"


def article_page(post):
    body = (CONTENT / post["body"]).read_text()
    info = ArticleInfo(body)
    text = " ".join(info.text)
    minutes = max(1, round(len(re.findall(r"[\u4e00-\u9fff]", text)) / 380 + len(re.findall(r"[a-zA-Z]+", text)) / 200))
    category = post["categories"][-1] if post["categories"] else {"name": "开发手记", "url": "/archives/"}
    categories = "".join(f'<a href="{e(item["url"])}">{e(item["name"])}</a>' for item in post["categories"])
    tags = "".join(f'<a href="{e(item["url"])}"># {e(item["name"])}</a>' for item in post["tags"])
    index = POSTS.index(post)
    neighbors = []
    for offset, label in [(1, "上一篇"), (-1, "下一篇")]:
        if 0 <= index + offset < len(POSTS):
            item = POSTS[index + offset]
            neighbors.append(f'<a href="{e(item["url"])}"><span>{label}</span><strong>{e(item["title"])}</strong>{ARROW}</a>')
    toc = toc_links(info.headings)
    aside = f'''<aside class="reading-aside" aria-label="文章导航"><div class="toc-sticky"><p class="toc-heading">本文目录 <span data-reading-percent>0%</span></p><nav aria-label="桌面文章目录">{toc}</nav><div class="toc-bottom"><a href="#main">回到顶部 ↑</a><span>慢慢读，也慢慢想。</span></div></div></aside>''' if toc else ""
    mobile_toc = f'<details class="mobile-toc"><summary>本文目录 <span aria-hidden="true">＋</span></summary><nav aria-label="手机文章目录">{toc}</nav></details>' if toc else ""
    updated = f'<span class="article-updated">更新于 {post["updated"][:10]}</span>' if post["updated"][:10] != post["published"][:10] else ""
    sigil = '<svg class="article-sigil" viewBox="0 0 160 160" fill="none" aria-hidden="true"><circle cx="80" cy="80" r="44"/><ellipse cx="80" cy="80" rx="71" ry="22" transform="rotate(-30 80 80)"/><ellipse cx="80" cy="80" rx="63" ry="30" transform="rotate(34 80 80)"/><circle cx="133" cy="50" r="3" fill="currentColor"/></svg>'
    page = f'''<div class="reading-progress" aria-hidden="true"><span id="reading-progress"></span></div>
<main id="main" class="wrap article-main">
<header class="article-hero"><div class="breadcrumb"><a href="/archives/">← 开发手记</a><span>/</span><a href="{e(category['url'])}">{e(category['name'])}</a></div><h1>{e(post['title'])}</h1><div class="article-meta"><a class="article-author" href="/about/"><img src="{e(SITE['avatar'])}" width="30" height="30" alt=""><span>wangbax</span></a><time datetime="{e(post['published'])}">{post['published'][:10]}</time><span>约 {minutes} 分钟</span>{updated}</div>{sigil}</header>
<div class="reading-layout"><article class="article-column" aria-label="{e(post['title'])}">{mobile_toc}<div class="article-body" id="article-body">{body}</div><footer class="article-footer"><div class="article-tags">{tags}</div><div class="article-category">收录于 {categories}</div><a class="back-to-notes" href="/archives/">← 返回全部文章</a></footer><nav class="neighbor-notes" aria-label="相邻文章">{''.join(neighbors)}</nav></article>{aside}</div>
</main>'''
    return document(post["title"], post["url"], page, active="notes", description=post["summary"], post=post)


def collection(title, eyebrow, intro, inner, url, active="notes"):
    body = f'<main id="main" class="wrap collection-main"><header class="collection-hero"><p class="eyebrow">{e(eyebrow)}</p><h1>{e(title)}</h1><p>{e(intro)}</p></header>{inner}</main>'
    return document(title, url, body, active=active)


def listing(posts, path, title, context):
    page_match = re.search(r"/page/(\d+)/", path)
    page_number = int(page_match.group(1)) if page_match else 1
    base = re.sub(r"page/\d+/", "", path)
    if base == "/" and path.startswith("/page/"):
        base = "/archives/"
    selected = posts[(page_number - 1) * 10:page_number * 10]
    years = []
    for year in dict.fromkeys(post["published"][:4] for post in selected):
        entries = "".join(note(post) for post in selected if post["published"].startswith(year))
        years.append(f'<section class="archive-year" aria-labelledby="year-{year}"><h2 id="year-{year}">{year}<span>年</span></h2><div>{entries}</div></section>')
    pagination = ""
    if len(posts) > 10:
        page_links = []
        for number in range(1, (len(posts) + 9) // 10 + 1):
            link = base if number == 1 else base + "page/" + str(number) + "/"
            current = ' aria-current="page"' if number == page_number else ""
            page_links.append(f'<a href="{e(link)}"{current} aria-label="第 {number} 页">{number:02d}</a>')
        pagination = '<nav class="pagination" aria-label="文章分页">' + "".join(page_links) + "</nav>"
    inner = '<div class="archive-list">' + "".join(years) + "</div>" + pagination
    return collection(title, context, f"共 {len(posts)} 篇手记，把问题与解决过程留在这里。", inner, path)


def taxonomy_index(key, title, path):
    names = {}
    counts = Counter()
    for post in POSTS:
        for item in post[key]:
            counts[item["url"]] += 1
            names[item["url"]] = item["name"]
    items = "".join(
        f'<a class="taxonomy-item" href="{e(url)}"><span>{e(names[url])}</span><span>{counts[url]:02d} 篇 {ARROW}</span></a>'
        for url in sorted(names)
    )
    return collection(title, "TOPICS" if key == "categories" else "KEYWORDS", "换一个入口，找到感兴趣的内容。", '<div class="taxonomy-list">' + items + "</div>", path)


def about_page():
    body = f'''<main id="main" class="wrap about-main"><div class="about-intro"><img class="about-avatar" src="{e(SITE['avatar'])}" width="80" height="80" alt="wangbax 的头像"><p class="eyebrow">A LITTLE ABOUT ME</p><h1>你好，我是 wangbax。</h1><p>这里记录开发中遇到的问题、解决过程和学习笔记，<br class="desktop">主要围绕 Android、PHP 和开发工具。</p><p>写博客是为了给自己留个备忘。如果你也遇到了类似的问题，<br class="desktop">希望这些记录能帮上忙。</p><a class="about-github" href="{e(SITE['github'])}" target="_blank" rel="noopener">在 GitHub 找到我 {ARROW}</a><blockquote>Be Patient, Be Learning.</blockquote></div><div class="about-links"><a href="/#projects">看看我的项目 {ARROW}</a><a href="/archives/">读一篇开发手记 {ARROW}</a></div></main>'''
    return document("关于我", "/about/", body, active="about", description="我是 wangbax。这里记录 Android、PHP 和开发工具相关的实践与学习笔记。")


def render_page(page):
    name = page["path"]
    url = "/" + name.removesuffix("index.html") if name.endswith("index.html") else "/" + name
    if name == "index.html":
        return home_page()
    if url in POST_BY_URL:
        return article_page(POST_BY_URL[url])
    if name == "google954e5c596c6310df.html":
        return "google-site-verification: google954e5c596c6310df.html\n"
    if name == "about/index.html":
        return about_page()
    if name == "404.html":
        inner = '<div class="empty-state"><p>这个地址可能已经搬走，或是链接里多了一个字符。</p><a class="primary" href="/">返回首页 ↗</a><a href="/archives/">去文章归档看看 →</a></div>'
        return collection("这页走丢了。", "404 / NOT FOUND", "还有别的地方值得逛逛。", inner, url, active="")
    if name == "search/index.html":
        return collection("找一篇手记", "SEARCH", "按标题、正文或关键词搜索。", search_form(standalone=True), url)
    if name == "project/index.html":
        return collection("一些小作品", "PROJECTS", "写一点代码，把小想法变成可以用的东西。", projects(), url, active="projects")
    if name == "link/index.html":
        inner = f'<div class="taxonomy-list"><a class="taxonomy-item" href="{e(SITE["github"])}" target="_blank" rel="noopener"><span>GitHub · wangbax</span>{ARROW}</a><a class="taxonomy-item" href="https://github.com/wangbax/BlogHexo" target="_blank" rel="noopener"><span>文章原稿 · BlogHexo</span>{ARROW}</a></div>'
        return collection("一些链接", "ELSEWHERE", "在别处，也留下一些记录。", inner, url, active="")
    if name == "tags/index.html":
        return taxonomy_index("tags", "按标签阅读", url)
    if name == "categories/index.html":
        return taxonomy_index("categories", "按主题阅读", url)
    if url.startswith(("/tags/", "/categories/")):
        key = "tags" if url.startswith("/tags/") else "categories"
        base = re.sub(r"page/\d+/", "", url)
        posts = [post for post in POSTS if any(item["url"] == base for item in post[key])]
        assert posts, "No posts match " + url
        label = next(item["name"] for item in posts[0][key] if item["url"] == base)
        return listing(posts, url, label, "TAGGED NOTES" if key == "tags" else "IN THIS TOPIC")
    if url.startswith(("/archives/", "/page/")):
        archive = re.match(r"/archives/(\d{4})(?:/(\d{2}))?/", url)
        posts = POSTS
        title = "开发手记"
        if archive:
            prefix = archive[1] + ("-" + archive[2] if archive[2] else "")
            posts = [post for post in posts if post["published"].startswith(prefix)]
            title = archive[1] + " 年" + (" " + archive[2] + " 月" if archive[2] else "")
        return listing(posts, url, title, "FIELD NOTES")
    raise ValueError("Unhandled site page: " + name)


def render_search():
    root = ET.Element("search")
    for post in POSTS:
        entry = ET.SubElement(root, "entry")
        ET.SubElement(entry, "title").text = post["title"]
        ET.SubElement(entry, "url").text = post["url"]
        ET.SubElement(entry, "content", {"type": "html"}).text = (CONTENT / post["body"]).read_text()
    return '<?xml version="1.0" encoding="UTF-8"?>' + chr(10) + ET.tostring(root, encoding="unicode") + chr(10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when generated pages differ from their source")
    args = parser.parse_args()
    changed = []
    outputs = {page["path"]: render_page(page) for page in PAGES}
    outputs["search.xml"] = render_search()
    for path, rendered in outputs.items():
        target = ROOT / path
        if not target.is_file() or target.read_text() != rendered:
            changed.append(path)
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rendered)
    if args.check and changed:
        raise SystemExit("Regenerate the site with scripts/render_site.py: " + ", ".join(changed))
    print(json.dumps({"pages": len(PAGES), "articles": len(POSTS), "changed": len(changed), "mode": "check" if args.check else "render"}))


if __name__ == "__main__":
    main()
