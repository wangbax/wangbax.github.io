#!/usr/bin/env python3
"""Package the generated blog for a root-level, self-hosted deployment."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
from urllib.parse import urlsplit

from render_site import PAGES, build_site


ASSET_DIRECTORIES = {"images", "js"}
GENERATED_FILES = set(PAGES) | {"css/app.css", "search.json"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", required=True, help="Public origin, such as https://blog.example.com")
    parser.add_argument("--output", type=Path, default=Path(".release/site.tar.gz"))
    args = parser.parse_args()
    origin = args.site_url.rstrip("/")
    try:
        url = urlsplit(origin)
        valid_port = url.port is None or 1 <= url.port <= 65535
    except ValueError:
        parser.error("--site-url has an invalid host or port")
    if (
        url.scheme not in {"http", "https"} or not url.hostname
        or url.username is not None or url.password is not None
        or url.path or url.query or url.fragment or not valid_port
        or any(char.isspace() or char in '<>\"' or ord(char) < 32 for char in origin)
        or chr(39) in origin or chr(92) in origin
    ):
        parser.error("--site-url must be an HTTP(S) origin without credentials, a path, query or fragment")

    root = Path(__file__).resolve().parent.parent
    build_site()
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    names = GENERATED_FILES | {name.decode("utf-8") for name in tracked.split(bytes([0])) if name}
    selected = []
    for name in sorted(names):
        if name == "js/theme.js":
            continue
        relative = Path(name)
        if relative.parts[0] not in ASSET_DIRECTORIES and name not in GENERATED_FILES:
            continue
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise SystemExit("Refusing to package a symlink or external file: " + name)
        if not path.is_file():
            raise SystemExit("Site file is missing: " + name)
        selected.append((name, path))
    required = {"index.html", "404.html", "css/app.css", "js/site.js", "js/article.js", "js/search.js", "js/planet.js", "search.json"}
    if not required.issubset({name for name, _ in selected}):
        raise SystemExit("Required site files are missing")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    files = precompressed = text_bytes = gzip_bytes = 0
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as archive:
                for name, path in sorted(selected):
                    content = path.read_bytes()
                    if path.suffix in {".html", ".json"}:
                        for source_origin in (b"https://www.wangbaxai.top", b"http://www.wangbaxai.top"):
                            content = content.replace(source_origin, origin.encode("utf-8"))
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    info.mode = 0o644
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(content))
                    files += 1
                    if path.suffix in {".html", ".css", ".js", ".json"} and len(content) >= 512:
                        buffer = io.BytesIO()
                        with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, compresslevel=9, mtime=0) as compressed_file:
                            compressed_file.write(content)
                        compressed_content = buffer.getvalue()
                        info = tarfile.TarInfo(name + ".gz")
                        info.size = len(compressed_content)
                        info.mode = 0o644
                        info.mtime = 0
                        archive.addfile(info, io.BytesIO(compressed_content))
                        files += 1
                        precompressed += 1
                        text_bytes += len(content)
                        gzip_bytes += len(compressed_content)

    manifest = {
        "site_url": origin, "source_commit": commit, "files": files,
        "precompressed_files": precompressed, "text_bytes": text_bytes, "gzip_bytes": gzip_bytes,
        "archive": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    output.with_suffix(".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + chr(10))
    print(json.dumps({**manifest, "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
