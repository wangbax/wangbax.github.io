"""Read Markdown posts and render them into the site's existing article layout."""

from datetime import date, datetime, time, timedelta, timezone
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import re
from xml.etree.ElementTree import Element

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token
from pygments.util import ClassNotFound
import yaml


LOCAL_TIMEZONE = timezone(timedelta(hours=8))
POST_URL = re.compile(r"/[0-9]{4}/[0-9]{2}/[0-9]{2}/[a-z0-9]+(?:-[a-z0-9]+)*/")


class FrontMatterLoader(yaml.SafeLoader):
    """Reject accidental duplicate keys rather than silently losing metadata."""

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("文章信息的字段名需要是文字")
            if key in result:
                raise ValueError(f"文章信息重复：{key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


class PlainText(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.parts = []
        self.feed(source)

    def handle_data(self, text):
        self.parts.append(text)


def heading_slug(value, separator):
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s-]+", separator, value) or "section"


class HeadingLinksProcessor(Treeprocessor):
    def run(self, root):
        for heading in root.iter():
            if heading.tag in {"h2", "h3", "h4"} and heading.get("id"):
                link = Element("a", {"href": "#" + heading.get("id"), "class": "headerlink", "title": "链接到此段落"})
                link.tail, heading.text = heading.text, None
                heading.insert(0, link)


class HeadingLinks(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(HeadingLinksProcessor(md), "heading_links", 4)


def highlight_code(code, language="text"):
    language = language or "text"
    try:
        lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
    except ClassNotFound:
        lexer = get_lexer_by_name("text", stripnl=False, ensurenl=False)
    classes = [(Token.Comment, "comment"), (Token.Keyword, "keyword"),
               (Token.Name.Builtin, "built_in"), (Token.Name.Function, "function"),
               (Token.Name.Class, "title"), (Token.Literal.String, "string"),
               (Token.Literal.Number, "number"), (Token.Name.Tag, "selector-tag"),
               (Token.Name.Attribute, "attr"), (Token.Generic.Heading, "title")]
    parts = []
    for token, value in lex(code, lexer):
        class_name = next((name for kind, name in classes if token in kind), None)
        text = escape(value)
        parts.append(f'<span class="{class_name}">{text}</span>' if class_name else text)
    return f'<figure class="highlight {escape(language, quote=True)}"><table><tr><td class="code"><pre>{"".join(parts)}</pre></td></tr></table></figure>'


def fence_format(source, language, css_class, options, md, **kwargs):
    return highlight_code(source, language)


def render_markdown(source):
    body = markdown.markdown(
        source, extensions=["pymdownx.superfences", "tables", "toc", "attr_list", "sane_lists", HeadingLinks()],
        extension_configs={"toc": {"slugify": heading_slug, "marker": ""},
                           "pymdownx.superfences": {"custom_fences": [{"name": "*", "class": "highlight", "format": fence_format}]}},
        output_format="html",
    )
    return re.sub(r'<pre><code>(.*?)</code></pre>', lambda match: highlight_code(unescape(match[1])), body, flags=re.S)


def timestamp(value, field):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, time())
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{field} 不是有效日期：{value}") from error
    else:
        raise ValueError(f"请填写 {field} 日期，例如 2026-11-10")
    return result.replace(tzinfo=LOCAL_TIMEZONE) if result.tzinfo is None else result


def text_field(metadata, name, default=None):
    value = metadata.get(name, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} 需要填写文字")
    return value.strip()


def load_posts(directory):
    posts = []
    urls = set()
    for path in sorted(Path(directory).glob("*.md")):
        try:
            if path.is_symlink():
                raise ValueError("文章不能使用符号链接")
            source = path.read_text(encoding="utf-8")
            match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)\Z", source, re.S)
            if not match:
                raise ValueError("文件开头需要用 --- 包住文章信息")
            metadata = yaml.load(match[1], Loader=FrontMatterLoader)
            if not isinstance(metadata, dict):
                raise ValueError("文章信息需要包含 title 和 date")
            title = text_field(metadata, "title")
            published = timestamp(metadata.get("date"), "date")
            updated = timestamp(metadata.get("updated", published), "updated")
            if updated < published:
                raise ValueError("updated 不能早于 date")
            slug = path.stem
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
                raise ValueError("文件名请使用小写英文、数字和连字符")
            url = metadata.get("permalink", f"/{published:%Y/%m/%d}/{slug}/")
            if not isinstance(url, str) or not POST_URL.fullmatch(url):
                raise ValueError("permalink 格式应为 /年/月/日/英文文件名/，不能包含路径跳转")
            if url in urls:
                raise ValueError(f"文章地址重复：{url}")
            urls.add(url)
            if not match[2].strip():
                raise ValueError("文章正文不能为空")
            body = render_markdown(match[2])
            first_paragraph = re.search(r"<p>(.*?)</p>", body, re.S)
            excerpt = "".join(PlainText(first_paragraph[1] if first_paragraph else title).parts).strip()
            excerpt = re.sub(r"\s+", " ", excerpt)
            summary = text_field(metadata, "summary", excerpt[:160])
            posts.append({"slug": slug, "title": title, "url": url,
                          "published": published.isoformat(), "updated": updated.isoformat(),
                          "summary": summary, "category": text_field(metadata, "category", "开发笔记"),
                          "body": body})
        except (ValueError, yaml.YAMLError) as error:
            raise ValueError(f"{path}: {error}") from error
    return sorted(posts, key=lambda post: (datetime.fromisoformat(post["published"]), post["slug"]), reverse=True)
