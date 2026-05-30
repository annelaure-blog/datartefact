#!/usr/bin/env python3
"""
Apply grayscale + Floyd-Steinberg dithering to all images referenced in content/*.md.
Output goes to images/dithered/ — originals are never modified.
Run: python3 process_images.py
"""

import re
import yaml
from pathlib import Path
from PIL import Image

CONTENT_DIR = Path("content")
IMAGES_DIR = Path("images")
DITHERED_DIR = IMAGES_DIR / "dithered"


def parse_frontmatter(text):
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def collect_image_paths():
    paths = set()
    for md_file in CONTENT_DIR.glob("*.md"):
        meta = parse_frontmatter(md_file.read_text(encoding="utf-8"))
        image = meta.get("image", "")
        if image:
            paths.add(image.strip())
    return paths


def dither_image(src_path: Path, dst_path: Path):
    if dst_path.exists() and dst_path.stat().st_mtime >= src_path.stat().st_mtime:
        print(f"  Skipped (up to date): {dst_path}")
        return
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        grayscale = img.convert("L")
        dithered = grayscale.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
        dithered.convert("L").save(dst_path, format="PNG", optimize=True)
    print(f"  Dithered: {dst_path}")


def process_all():
    image_paths = collect_image_paths()
    if not image_paths:
        print("No images found in content files.")
        return

    processed = skipped = 0
    for rel_path in sorted(image_paths):
        src = Path(rel_path)
        if not src.exists():
            print(f"  Missing source: {src}")
            continue
        dst = DITHERED_DIR / src.name
        dst = dst.with_suffix(".png")
        dither_image(src, dst)
        processed += 1

    print(f"\nDone — {processed} processed, {skipped} skipped.")


if __name__ == "__main__":
    process_all()
