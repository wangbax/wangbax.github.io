#!/usr/bin/env python3
"""Check the deployable archive, including references to local static assets."""

from html.parser import HTMLParser
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

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
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
        assert {"index.html", "404.html", "css/main.css", "search.xml"} <= names
        forbidden = {"scripts", "deploy", ".git", ".github", ".release", "README.md", "CNAME"}
        for member in members:
            path = PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and ".." not in path.parts
            assert path.parts[0] not in forbidden and not path.parts[0].startswith(".")
        checked = 0
        for member in members:
            if not member.name.endswith(".html"):
                continue
            parser = Resources()
            parser.feed(archive.extractfile(member).read().decode("utf-8"))
            for reference in parser.urls:
                url = urlsplit(reference)
                if url.scheme or url.netloc or not url.path:
                    continue
                path = unquote(url.path)
                target = posixpath.normpath(path.lstrip("/") if path.startswith("/") else posixpath.join(posixpath.dirname(member.name), path))
                assert target in names, f"Missing asset: {member.name} -> {reference}"
                checked += 1
        print(json.dumps({"archive_files": len(members), "local_asset_references_checked": checked}))


if __name__ == "__main__":
    main()
