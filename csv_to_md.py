#!/usr/bin/env python3
"""
csv_to_md.py  —  Two-way sync between index.csv and content/*.md

Usage:
  python csv_to_md.py           # CSV → .md  (create missing files from index.csv)
  python csv_to_md.py --update  # CSV → .md  (update frontmatter of ALL files, keep body)
  python csv_to_md.py --export  # .md → CSV  (rebuild index.csv from existing files)
"""

import csv
import sys
import yaml
from pathlib import Path

CONTENT_DIR = Path(__file__).parent / "content"
CSV_PATH = Path(__file__).parent / "index.csv"

FIELDS = ["title", "date", "type", "author", "description", "slug", "book", "chapter", "image", "image_copyright"]

CSV_FIELD_MAP = {"image_copyright": "image copyrights"}

LINK_COLUMNS = ["link 1", "link 2", "link 3"]


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
        csv_key = CSV_FIELD_MAP.get(field, field)
        val = (row.get(csv_key) or row.get(" " + csv_key) or "").strip()
        if not val:
            continue
        if field in ("book", "chapter"):
            try:
                result[field] = int(val)
            except ValueError:
                result[field] = val
        else:
            result[field] = val

    # Collect link columns (handle leading spaces in header)
    sources = []
    for col in LINK_COLUMNS:
        val = (row.get(col) or row.get(" " + col) or "").strip()
        if val:
            sources.append(val)
    if sources:
        result["sources"] = sources

    return result


def write_md(path, meta, body):
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    path.write_text(f"---\n{fm}---\n\n{body}\n", encoding="utf-8")


def csv_to_md():
    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found.")
        sys.exit(1)

    created = skipped = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            meta = coerce_row(row)
            slug = meta.get("slug", "")
            if not slug:
                print(f"  Skipping row with no slug: {row.get('title', '(no title)')}")
                continue

            out_path = CONTENT_DIR / f"{slug}.md"
            if out_path.exists():
                print(f"  Skipping (already exists): {slug}.md")
                skipped += 1
                continue

            write_md(out_path, meta, "")
            print(f"  Created: {slug}.md")
            created += 1

    print(f"\nDone — {created} created, {skipped} skipped.")


def update_md():
    """Update frontmatter of existing .md files from CSV; keep body intact."""
    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found.")
        sys.exit(1)

    updated = created = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            meta = coerce_row(row)
            slug = meta.get("slug", "")
            if not slug:
                continue

            out_path = CONTENT_DIR / f"{slug}.md"
            if out_path.exists():
                _, body = parse_frontmatter(out_path.read_text(encoding="utf-8"))
                write_md(out_path, meta, body)
                print(f"  Updated: {slug}.md")
                updated += 1
            else:
                write_md(out_path, meta, "")
                print(f"  Created: {slug}.md")
                created += 1

    print(f"\nDone — {updated} updated, {created} created.")


def export_csv():
    entries = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(raw)
        meta.setdefault("slug", path.stem)
        entries.append(meta)

    entries.sort(key=lambda e: (int(e.get("book") or 0), int(e.get("chapter") or 0)))

    export_fields = FIELDS + LINK_COLUMNS
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=export_fields, extrasaction="ignore")
        writer.writeheader()
        for entry in entries:
            row = {k: entry.get(k, "") for k in export_fields}
            sources = entry.get("sources", [])
            if isinstance(sources, list):
                for i, col in enumerate(LINK_COLUMNS):
                    row[col] = sources[i] if i < len(sources) else ""
            writer.writerow(row)

    print(f"Exported {len(entries)} entries → {CSV_PATH}")


if __name__ == "__main__":
    if "--export" in sys.argv:
        export_csv()
    elif "--update" in sys.argv:
        update_md()
    else:
        csv_to_md()
