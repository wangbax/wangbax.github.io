#!/usr/bin/env python3
"""Generate responsive WebP images and their manifest (requires Pillow with WebP)."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence


ROOT = Path(__file__).resolve().parent.parent


def main():
    manifest = {}
    sources = sorted(path for path in (ROOT / "images").rglob("*")
                     if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"})
    for source in sources:
        relative = source.relative_to(ROOT)
        with Image.open(source) as image:
            animated = getattr(image, "n_frames", 1) > 1
            width, height = image.size
            widths = [64, 96, 160, width] if relative.name == "avatar.png" else ([480, width] if width > 800 else [width])
            variants = []
            for size in sorted(set(widths)):
                destination = ROOT / "images/optimized" / relative.relative_to("images").parent / (source.stem + "-" + str(size) + ".webp")
                destination.parent.mkdir(parents=True, exist_ok=True)
                options = {"format": "WEBP", "method": 6, "lossless": True, "exact": True}
                if animated:
                    durations = [frame.info.get("duration", 100) for frame in ImageSequence.Iterator(image)]
                    image.seek(0)
                    image.save(destination, save_all=True, duration=durations, loop=image.info.get("loop", 0), **options)
                else:
                    frame = ImageOps.exif_transpose(image).convert("RGBA")
                    if size != width:
                        frame = frame.resize((size, round(height * size / width)), Image.Resampling.LANCZOS)
                    if source.suffix.lower() in {".jpg", ".jpeg"} or (size != width and relative.name != "avatar.png"):
                        options.update(lossless=False, quality=90)
                    frame.save(destination, **options)
                    if source.suffix.lower() in {".jpg", ".jpeg"}:
                        for quality in [85, 80, 75]:
                            if destination.stat().st_size < source.stat().st_size:
                                break
                            frame.save(destination, **dict(options, quality=quality))
                variants.append({"path": "/" + destination.relative_to(ROOT).as_posix(), "width": size,
                                 "bytes": destination.stat().st_size, "lossless": options["lossless"]})
            manifest["/" + relative.as_posix()] = {
                "width": width, "height": height, "animated": animated,
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "variants": variants,
            }
    target = ROOT / "content/images.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"original_bytes": sum(path.stat().st_size for path in sources),
                      "webp_full_size_bytes": sum(item["variants"][-1]["bytes"] for item in manifest.values()),
                      "originals": len(sources), "variants": sum(len(item["variants"]) for item in manifest.values())}))


if __name__ == "__main__":
    main()
