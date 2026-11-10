#!/usr/bin/env python3
"""Check the deployable archive, including references to local static assets."""

from html.parser import HTMLParser
import gzip
import json
from pathlib import PurePosixPath
import posixpath
import sys
import tarfile
from urllib.parse import unquote, urlsplit


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.links = []
        self.ids = set()
        self.duplicates = []
        self.images = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "img":
            self.images.append(attrs)
        for key in ["data-search-module", "data-search-index", "data-planet-module"]:
            if attrs.get(key):
                self.urls.append(attrs[key])
        if tag in {"img", "source"} and attrs.get("srcset"):
            self.urls.extend(item.strip().split()[0] for item in attrs["srcset"].split(","))
        anchors = {attrs.get("id"), attrs.get("name") if tag == "a" else None} - {None, ""}
        for anchor in anchors:
            if anchor in self.ids:
                self.duplicates.append(anchor)
            self.ids.add(anchor)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag in {"script", "img", "source"} and attrs.get("src"):
            self.urls.append(attrs["src"])
        if tag == "link" and attrs.get("href"):
            if set(attrs.get("rel", "").split()) & {"stylesheet", "icon", "apple-touch-icon", "mask-icon"}:
                self.urls.append(attrs["href"])


def main():
    with tarfile.open(sys.argv[1], "r:gz") as archive:
        members = archive.getmembers()
        names = {member.name for member in members}
        assert len(names) == len(members), "Duplicate files in archive"
        assert {"index.html", "404.html", "css/app.css", "js/site.js", "js/article.js", "js/search.js", "js/planet.js", "search.json"} <= names
        forbidden = {"scripts", "deploy", "content", ".git", ".github", ".release", "README.md", "CNAME"}
        for member in members:
            path = PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and ".." not in path.parts
            assert path.parts[0] not in forbidden and not path.parts[0].startswith(".")
            if member.name.endswith(".gz"):
                original = member.name[:-3]
                assert original in names, f"Orphan compressed file: {member.name}"
                assert gzip.decompress(archive.extractfile(member).read()) == archive.extractfile(original).read(), f"Stale compressed file: {member.name}"
            elif path.suffix in {".html", ".css", ".js", ".json"} and member.size >= 512:
                assert member.name + ".gz" in names, f"Missing compressed file: {member.name}"
        checked = 0
        parsers = {}
        for member in members:
            if not member.name.endswith(".html"):
                continue
            parser = Resources()
            parser.feed(archive.extractfile(member).read().decode("utf-8"))
            assert not parser.duplicates, f"Duplicate anchors: {member.name}: {parser.duplicates}"
            for image in parser.images:
                assert int(image.get("width", 0)) > 0 and int(image.get("height", 0)) > 0, f"Missing image dimensions: {member.name}"
                assert image.get("loading") in {"lazy", "eager"} and image.get("decoding") == "async", f"Missing image loading policy: {member.name}"
            parsers[member.name] = parser
            for reference in parser.urls:
                url = urlsplit(reference)
                if url.scheme or url.netloc or not url.path:
                    continue
                path = unquote(url.path)
                target = posixpath.normpath(path.lstrip("/") if path.startswith("/") else posixpath.join(posixpath.dirname(member.name), path))
                assert target in names, f"Missing asset: {member.name} -> {reference}"
                checked += 1
        links_checked = 0
        for name, parser in parsers.items():
            for reference in parser.links:
                url = urlsplit(reference)
                if url.scheme or url.netloc:
                    continue
                path = unquote(url.path)
                if not path:
                    target = name
                else:
                    target = path.lstrip("/") if path.startswith("/") else posixpath.join(posixpath.dirname(name), path)
                    if path.endswith("/"):
                        target += "index.html"
                    target = posixpath.normpath(target)
                    if target not in names and target + "/index.html" in names:
                        target += "/index.html"
                assert target in names, f"Missing page or link: {name} -> {reference}"
                if url.fragment and target in parsers:
                    assert unquote(url.fragment) in parsers[target].ids, f"Missing anchor: {name} -> {reference}"
                links_checked += 1
        print(json.dumps({"archive_files": len(members), "local_asset_references_checked": checked, "local_links_and_anchors_checked": links_checked}))


if __name__ == "__main__":
    main()
