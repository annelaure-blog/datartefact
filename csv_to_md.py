#!/usr/bin/env python3
"""
csv_to_md.py  —  Two-way sync between index.csv and content/*.md

Usage:
  python csv_to_md.py           # CSV → .md  (create missing files from index.csv)
  python csv_to_md.py --export  # .md → CSV  (rebuild index.csv from existing files)
"""

import csv
import sys
import yaml
from pathlib import Path

CONTENT_DIR = Path(__file__).parent / "content"
CSV_PATH = Path(__file__).parent / "index.csv"

FIELDS = ["title", "date", "type", "author", "description", "slug", "book", "chapter", "image"]


def parse_frontmatter(text):
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    meta = yaml.safe_load(parts[1]) or {}
    return meta, parts[2].strip()


def coerce_row(row):
    """Convert CSV string values to appropriate Python types."""
    result = {}
    for field in FIELDS:
        val = row.get(field, "").strip()
        if not val:
            continue
        if field in ("book", "chapter"):
            try:
                result[field] = int(val)
            except ValueError:
                result[field] = val
        else:
            result[field] = val
    return result


def csv_to_md():
    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found.")
        print("Run with --export first to generate it from your existing .md files.")
        sys.exit(1)

    created = skipped = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            meta = coerce_row(row)
            slug = meta.get("slug", "")
            if not slug:
                title = row.get("title", "(no title)")
                print(f"  Skipping row with no slug: {title}")
                continue

            out_path = CONTENT_DIR / f"{slug}.md"
            if out_path.exists():
                print(f"  Skipping (already exists): {slug}.md")
                skipped += 1
                continue

            fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
            out_path.write_text(f"---\n{fm}---\n\n(write your content here)\n", encoding="utf-8")
            print(f"  Created: {slug}.md")
            created += 1

    print(f"\nDone — {created} created, {skipped} skipped.")


def export_csv():
    entries = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(raw)
        meta.setdefault("slug", path.stem)
        entries.append(meta)

    entries.sort(key=lambda e: (int(e.get("book") or 0), int(e.get("chapter") or 0)))

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for entry in entries:
            writer.writerow({k: entry.get(k, "") for k in FIELDS})

    print(f"Exported {len(entries)} entries → {CSV_PATH}")


if __name__ == "__main__":
    if "--export" in sys.argv:
        export_csv()
    else:
        csv_to_md()
