#!/usr/bin/env python3
"""
Rebuild index.html and posts/*.html from content/*.md files.
Run: python build.py
"""

from __future__ import annotations

import json
import re
import yaml
from urllib.parse import urlparse
import markdown as md_lib
from datetime import date, datetime
from pathlib import Path
from process_images import process_all as process_images


CONTENT_DIR = Path("content")
POSTS_DIR = Path("posts")
BLOG_DIR = Path("blog")
BLOG_POSTS_DIR = Path("blog-posts")
NOTES_DIR = Path("notes")
NOTES_FILE = Path("notes.html")
INDEX_FILE = Path("collection.html")

MD = md_lib.Markdown(extensions=["extra", "smarty"])

_chapters_raw = json.loads(Path("chapters.json").read_text(encoding="utf-8"))
CHAPTERS = {int(b): {int(c): t for c, t in chaps.items()} for b, chaps in _chapters_raw.items()}

def chapter_title(book, chapter) -> str:
    try:
        return CHAPTERS[int(book)][int(chapter)]
    except (KeyError, TypeError, ValueError):
        return ""


def _url_label(url: str) -> str:
    try:
        host = urlparse(url).netloc.removeprefix("www.")
        return host if host else url
    except Exception:
        return url


def parse_sources(raw) -> list[tuple[str, str]]:
    if not raw:
        return []
    items = raw if isinstance(raw, list) else [s.strip() for s in raw.split("|") if s.strip()]
    result = []
    for item in items:
        if isinstance(item, dict):
            url = item.get("url", "")
            label = item.get("label", "") or _url_label(url)
            result.append((label, url))
        elif isinstance(item, str) and item.strip():
            item = item.strip()
            if "::" in item:
                label, url = item.split("::", 1)
                result.append((label.strip(), url.strip()))
            else:
                result.append((_url_label(item), item))
    return result


def parse_year(date_val) -> int | None:
    if date_val is None:
        return None
    if isinstance(date_val, (int, float)):
        return int(date_val)
    if isinstance(date_val, (date, datetime)):
        return date_val.year
    s = str(date_val)
    s_clean = re.sub(r'(\d)\s+(\d)', r'\1\2', s)  # collapse "5 000" → "5000"
    m = re.search(r'(?<!\d)(\d{3,5})(?!\d)', s_clean)
    if not m:
        return None
    year = int(m.group(1))
    if re.search(r'\bBC\b|\bBCE\b', s, re.IGNORECASE):
        year = -year
    return year


def render_timeline_entry(entry: dict, margin_top: int) -> str:
    type_key = entry.get("type", "article")
    title = entry.get("title", "Untitled")
    author = entry.get("author", "")
    description = entry.get("description", "")
    slug = entry["slug"]
    book = entry.get("book")
    chapter = entry.get("chapter")
    ch_title = chapter_title(book, chapter)
    chapter_str = f"Chapter {chapter} · {ch_title}" if ch_title else (f"Chapter {chapter}" if chapter else "")

    raw_date = entry.get("date")
    if isinstance(raw_date, (int, float)):
        year_label = str(int(raw_date))
    elif isinstance(raw_date, str) and raw_date:
        year_label = raw_date
    elif isinstance(raw_date, (date, datetime)):
        year_label = str(raw_date.year)
    else:
        year_label = "—"

    image = entry.get("image", "")
    if image:
        dithered = f"images/dithered/{Path(image).stem}.png"
        img_html = f'<img src="{dithered}" alt="{title}" class="object-cover border-r border-gray-900 flex-shrink-0" style="width:160px;height:200px;">'
    else:
        img_html = '<div class="bg-gray-100 border-r border-gray-900 flex-shrink-0 flex items-center justify-center" style="width:160px;height:200px;"><span class="text-xs text-gray-400">—</span></div>'

    return f"""\
      <div class="timeline-entry flex items-start" data-chapter="{chapter or ''}" data-type="{type_key}" data-book="{book or ''}" style="margin-top: {margin_top}px;">
        <div class="flex-shrink-0 w-24 text-right pr-3 leading-tight pt-1.5 overflow-hidden">
          <span class="text-sm font-bold text-gray-900 font-sans">{year_label}</span>
        </div>
        <div class="flex-shrink-0 flex justify-center pt-2 relative z-10" style="width: 16px;">
          <div class="w-3.5 h-3.5 rounded-full border-2 border-gray-900" style="background:#FFFBF5;"></div>
        </div>
        <a href="posts/{slug}.html" class="ml-6 flex border border-gray-900 hover:border-[#B69188] transition-colors group" style="max-width: 560px; flex: 1 1 auto;">
          {img_html}
          <div class="p-5 flex-1 min-w-0">
            {f'<span class="text-sm font-semibold uppercase tracking-widest text-gray-500 block truncate">{chapter_str}</span>' if chapter_str else ''}
            <h3 class="font-display text-2xl font-bold mt-2 leading-tight text-gray-900 group-hover:underline">{title}</h3>
            {f'<p class="text-sm text-gray-500 mt-2">{author}</p>' if author else ''}
            {f'<p class="text-base text-gray-600 mt-3 leading-relaxed">{description}</p>' if description else ''}
          </div>
        </a>
      </div>"""


def render_timeline_h_entry(entry: dict, margin_left: int) -> str:
    CARD_WIDTH = 240
    YEAR_H    = 28    # reserved above spine for year label
    DOT_SIZE  = 12
    CONN_H    = 12
    SPINE_TOP = YEAR_H + DOT_SIZE // 2          # 34px — spine centre
    CARD_TOP  = SPINE_TOP + DOT_SIZE // 2 + CONN_H  # 52px — top of card

    type_key    = entry.get("type", "article")
    title       = entry.get("title", "Untitled")
    author      = entry.get("author", "")
    description = entry.get("description", "")
    slug        = entry["slug"]
    book        = entry.get("book")
    chapter     = entry.get("chapter")
    ch_title    = chapter_title(book, chapter)
    chapter_str = f"Ch.{chapter} · {ch_title}" if ch_title else (f"Ch.{chapter}" if chapter else "")

    raw_date = entry.get("date")
    if isinstance(raw_date, (int, float)):        year_label = str(int(raw_date))
    elif isinstance(raw_date, str) and raw_date:  year_label = raw_date
    elif isinstance(raw_date, (date, datetime)):  year_label = str(raw_date.year)
    else:                                         year_label = "—"

    image = entry.get("image", "")
    if image:
        dithered = f"images/dithered/{Path(image).stem}.png"
        img_html = f'<img src="{dithered}" alt="{title}" class="w-full object-cover flex-shrink-0" style="height:130px;">'
    else:
        img_html = '<div class="w-full flex-shrink-0 bg-gray-100 flex items-center justify-center" style="height:130px;"><span class="text-xs text-gray-400">—</span></div>'

    return f"""\
          <div class="timeline-h-entry relative flex-shrink-0 group" data-chapter="{chapter or ''}" data-type="{type_key}" data-book="{book or ''}" style="width:{CARD_WIDTH}px; margin-left:{margin_left}px; padding-top:{CARD_TOP}px;">
            <div class="absolute text-xs font-bold text-gray-900 whitespace-nowrap text-center font-sans" style="top:0;left:50%;transform:translateX(-50%);">{year_label}</div>
            <div class="absolute rounded-full border-2 border-gray-900 z-10" style="background:#FFFBF5;width:{DOT_SIZE}px;height:{DOT_SIZE}px;top:{SPINE_TOP - DOT_SIZE // 2}px;left:50%;transform:translateX(-50%);"></div>
            <div class="absolute" style="width:1px;background:#202020;left:50%;transform:translateX(-50%);top:{SPINE_TOP + DOT_SIZE // 2}px;height:{CONN_H}px;"></div>
            <a href="posts/{slug}.html" class="block border border-gray-900 hover:border-[#B69188] transition-colors group">
              {img_html}
              <div class="p-3">
                {f'<span class="text-xs text-gray-500 font-semibold uppercase tracking-widest block leading-snug">{chapter_str}</span>' if chapter_str else ''}
                <h3 class="font-display text-lg font-bold leading-tight mt-1 text-gray-900 group-hover:underline">{title}</h3>
                {f'<p class="text-xs text-gray-500 mt-1">{author}</p>' if author else ''}
                {f'<p class="text-xs text-gray-600 mt-2 leading-snug">{description}</p>' if description else ''}
              </div>
            </a>
          </div>"""


def build_timeline_h(entries: list[dict]) -> str:
    PX_PER_YEAR = 0.8
    MIN_GAP     = 64
    MAX_GAP     = 500
    FIRST_LEFT  = 80
    YEAR_H      = 28
    DOT_SIZE    = 12
    SPINE_TOP   = YEAR_H + DOT_SIZE // 2   # 34
    CONTAINER_H = 460

    dated, undated = [], []
    for e in entries:
        y = parse_year(e.get("date"))
        if y is not None:
            dated.append((y, e))
        else:
            undated.append(e)
    dated.sort(key=lambda x: x[0])

    rows = []
    prev_year = None
    for year, entry in dated:
        ml = FIRST_LEFT if prev_year is None else min(MAX_GAP, max(MIN_GAP, int(max(0, year - prev_year) * PX_PER_YEAR)))
        rows.append(render_timeline_h_entry(entry, ml))
        prev_year = year
    for entry in undated:
        rows.append(render_timeline_h_entry(entry, MIN_GAP))

    entries_html = "\n".join(rows)
    return f"""\
      <div class="relative">
        <button id="tl-h-prev" class="hidden md:flex absolute left-0 top-0 bottom-0 z-20 items-center px-3 bg-gradient-to-r from-[#FFFBF5] to-transparent" aria-label="Scroll left">
          <span class="border border-gray-900 bg-[#FFFBF5] w-8 h-8 flex items-center justify-center text-gray-900 hover:bg-gray-900 hover:text-white transition-colors text-lg">←</span>
        </button>
        <button id="tl-h-next" class="hidden md:flex absolute right-0 top-0 bottom-0 z-20 items-center px-3 bg-gradient-to-l from-[#FFFBF5] to-transparent" aria-label="Scroll right">
          <span class="border border-gray-900 bg-[#FFFBF5] w-8 h-8 flex items-center justify-center text-gray-900 hover:bg-gray-900 hover:text-white transition-colors text-lg">→</span>
        </button>
        <div id="tl-h-scroll" class="overflow-x-auto overflow-y-hidden" style="height:{CONTAINER_H}px; cursor:grab; scrollbar-width:none;">
          <div class="relative flex items-start" style="min-width:max-content; height:100%; padding-right:{FIRST_LEFT}px;">
            <div class="absolute pointer-events-none" style="top:{SPINE_TOP}px; left:0; right:0; height:1px; background:#202020;"></div>
{entries_html}
          </div>
        </div>
        <p class="text-center text-xs text-gray-400 mt-3 font-sans">Scroll to explore →</p>
      </div>"""


def build_timeline(entries: list[dict]) -> str:
    PX_PER_YEAR = 1.5
    MIN_GAP = 80
    FIRST_TOP = 40

    dated, undated = [], []
    for e in entries:
        y = parse_year(e.get("date"))
        if y is not None:
            dated.append((y, e))
        else:
            undated.append(e)
    dated.sort(key=lambda x: x[0])

    rows = []
    prev_year = None
    for year, entry in dated:
        if prev_year is None:
            margin = FIRST_TOP
        else:
            gap = max(0, year - prev_year)
            margin = max(MIN_GAP, int(gap * PX_PER_YEAR))
        rows.append(render_timeline_entry(entry, margin))
        prev_year = year

    for entry in undated:
        rows.append(render_timeline_entry(entry, MIN_GAP))

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2].strip()
    return {}, text.strip()


def load_entries() -> list[dict]:
    entries = []
    for path in CONTENT_DIR.glob("*.md"):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        meta.setdefault("slug", path.stem)
        meta.setdefault("type", "article")
        meta["body"] = body
        raw_date = meta.get("date")
        if isinstance(raw_date, (date, datetime)):
            meta["date_obj"] = raw_date if isinstance(raw_date, date) else raw_date.date()
        else:
            meta["date_obj"] = None
        entries.append(meta)
    entries.sort(key=lambda e: e["date_obj"] or date.min, reverse=True)
    return entries


def fmt_date(d) -> str:
    if isinstance(d, (date, datetime)):
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    return str(d) if d else ""


TYPE_LABELS = {
    "article":  "Book 1",
    "note":     "Contemporary Creation",
    "resource": "Historical Artefact",
}

def type_label(key: str) -> str:
    return TYPE_LABELS.get(key, key.replace("-", " ").title())


# ---------------------------------------------------------------------------
# HTML snippets
# ---------------------------------------------------------------------------

_ARROW = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" class="inline-block w-3 h-3 mb-1" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1.5 8.5L8.5 1.5M4 1.5h4.5V6"/></svg>'

_NAV_ITEMS = [
    ("book", "{p}book", "Book"),
    ("collection", "{p}collection", "Collection"),
    ("about", "{p}about", "About"),
]
_NAV_EXTERNAL = [
    ("https://www.instagram.com/annelaurefre/", "Instagram"),
    ("https://datartefacts.hypotheses.org/", "Notebook"),
]

def _nav_link_class(active: bool) -> str:
    return "text-[#ea7662] transition-colors" if active else "hover:text-[#ea7662] transition-colors"

def _build_nav_links(prefix: str, current: str) -> str:
    lines = []
    for key, href_tpl, label in _NAV_ITEMS:
        href = href_tpl.format(p=prefix)
        lines.append(f'        <a href="{href}" class="{_nav_link_class(key == current)}">{label}</a>')
    for href, label in _NAV_EXTERNAL:
        lines.append(
            f'        <a href="{href}" target="_blank" rel="noopener noreferrer" '
            f'class="{_nav_link_class(False)}">{label} {_ARROW}</a>'
        )
    return "\n".join(lines)

def _build_nav(prefix: str, current: str = "") -> str:
    links = _build_nav_links(prefix, current)
    return f"""  <header class="border-b border-gray-900 sticky top-0 bg-[#FFFBF5] z-10">
    <div class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
      <a href="{prefix}book" class="flex items-end gap-3 font-display text-4xl font-bold tracking-normal text-[#202020]">Datartefact</a>
      <nav class="hidden md:flex gap-8 text-base text-gray-900 font-medium font-sans">
{links}
      </nav>
      <button id="menu-toggle" class="md:hidden flex flex-col justify-center gap-1.5 p-1" aria-label="Toggle menu">
        <span class="block w-6 h-0.5 bg-[#202020]"></span>
        <span class="block w-6 h-0.5 bg-[#202020]"></span>
        <span class="block w-6 h-0.5 bg-[#202020]"></span>
      </button>
    </div>
    <div id="mobile-menu" class="hidden border-t border-gray-900">
      <nav class="max-w-6xl mx-auto px-6 py-5 flex flex-col gap-5 text-base text-gray-900 font-medium font-sans">
{links}
      </nav>
    </div>
  </header>"""

NAV       = _build_nav("../")
NAV_INDEX = _build_nav("")

def build_footer(year: int, prefix: str = "") -> str:
    return f"""  <footer class="border-t border-gray-900 mt-auto">
    <div class="max-w-6xl mx-auto px-6 pt-10 pb-6 flex flex-col items-center gap-6">
      <p class="text-[#202020] text-center leading-relaxed tracking-wide md:whitespace-nowrap" style="font-family: 'Press Start 2P', monospace; font-size: 11px;">
        01000100 01100001 01110100 01100001 01110010 01110100 01100101 01100110 01100001 01100011 01110100
      </p>
      <div class="w-full flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-900 border-t border-gray-200 pt-6">
        <span>© {year} Datartefact</span>
        <div class="flex gap-6">
          <a href="https://www.instagram.com/annelaurefre/" target="_blank" rel="noopener noreferrer" class="hover:text-[#B69188] transition-colors">Instagram</a>
          <a href="#newsletter" class="hover:text-[#B69188] transition-colors">Newsletter</a>
          <a href="mailto:info@datartefact.com" class="hover:text-[#B69188] transition-colors">Contact</a>
          <a href="{prefix}legal" class="hover:text-[#B69188] transition-colors">Legal</a>
        </div>
      </div>
    </div>
  </footer>"""

HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — Datartefact</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = {{ theme: {{ extend: {{ fontFamily: {{ sans: ['"IBM Plex Mono"', 'monospace'], display: ['Stedelijk', 'sans-serif'] }} }} }} }}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Press+Start+2P&display=swap" rel="stylesheet" />
  <style>@font-face {{ font-family: 'Stedelijk'; src: url('{font_path}fonts/Stedelijk-Regular.otf') format('opentype'); font-weight: normal; font-style: normal; }}</style>
  <style>
    .card-wrapper {{ perspective: 1200px; height: 320px; }}
    .card-inner {{ position: relative; width: 100%; height: 100%; transform-style: preserve-3d; transition: transform 0.55s cubic-bezier(0.4,0.2,0.2,1); }}
    .card-wrapper:hover .card-inner {{ transform: rotateY(180deg); }}
    .card-front, .card-back {{ position: absolute; inset: 0; backface-visibility: hidden; -webkit-backface-visibility: hidden; }}
    .card-back {{ transform: rotateY(180deg); }}
    .card-front:hover .card-title {{ text-decoration: underline; }}
    .prose a {{ text-decoration: underline; }}
    .prose h2 {{ font-size: 1.5rem; font-weight: 600; margin-top: 2.5rem; margin-bottom: 0.75rem; }}
    .prose h3 {{ font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 0.5rem; }}
    .prose p {{ font-size: 1.125rem; margin-bottom: 1.25rem; line-height: 1.85; }}
    .prose ul {{ font-size: 1.125rem; list-style: disc; padding-left: 1.5rem; margin-bottom: 1.25rem; }}
    .prose ol {{ font-size: 1.125rem; list-style: decimal; padding-left: 1.5rem; margin-bottom: 1.25rem; }}
    .prose li {{ margin-bottom: 0.35rem; }}
    .prose strong {{ font-weight: 600; }}
  </style>
</head>
<body class="bg-[#FFFBF5] text-gray-900 font-sans antialiased min-h-screen flex flex-col">
  <script>
    document.addEventListener('DOMContentLoaded', function() {{
      var toggle = document.getElementById('menu-toggle');
      if (toggle) toggle.addEventListener('click', function() {{
        document.getElementById('mobile-menu').classList.toggle('hidden');
      }});
    }});
  </script>
"""


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

def render_card(entry: dict) -> str:
    type_key = entry.get("type", "article")
    label = type_label(type_key)
    date_str = fmt_date(entry.get("date_obj") or entry.get("date"))
    title = entry.get("title", "Untitled")
    author = entry.get("author", "")
    description = entry.get("description", "")
    slug = entry["slug"]
    book = entry.get("book")
    chapter = entry.get("chapter")
    ch_title = chapter_title(book, chapter)
    chapter_str = f"Chapter {chapter} · {ch_title}" if ch_title else (f"Chapter {chapter}" if chapter else "")
    book_chapter = f"Book {book} · {chapter_str}" if book and chapter_str else ""
    meta_parts = [p for p in [author, date_str] if p]
    meta_line = " · ".join(meta_parts)

    image = entry.get("image", "")
    if image:
        dithered = f"images/dithered/{Path(image).stem}.png"
        back_content = f'<img src="{dithered}" alt="{title}" class="w-full h-full object-cover">'
    else:
        back_content = f'<div class="w-full h-full bg-gray-900 flex items-center justify-center"><span class="text-white text-xs font-semibold uppercase tracking-widest">No image yet</span></div>'

    search_text = f"{title} {description} {label} book {book or ''} chapter {chapter or ''}".lower()
    return f"""\
      <div class="card-wrapper border border-gray-900" data-type="{type_key}" data-book="{book or ''}" data-chapter="{chapter or ''}" data-search="{search_text}">
        <div class="card-inner">
          <a href="posts/{slug}.html" class="card-front overflow-hidden">
            {back_content}
          </a>
          <a href="posts/{slug}.html" class="card-back p-8 block overflow-hidden" style="background:#FFFBF5;">
            <div class="flex items-center justify-between">
              {f'<span class="text-xs font-semibold uppercase tracking-widest text-gray-900">{book_chapter}</span>' if book_chapter else ''}
            </div>
            <h2 class="card-title font-display mt-4 text-4xl font-bold leading-none text-gray-900">{title}</h2>
            <div class="mt-2 space-y-0.5">
              {f'<p class="text-xs text-gray-500"><span class="font-semibold text-gray-900">Author</span> {author}</p>' if author else ''}
              {f'<p class="text-xs text-gray-500"><span class="font-semibold text-gray-900">Date of creation</span> {date_str}</p>' if date_str else ''}
            </div>
            <p class="mt-3 text-sm text-gray-900 leading-snug">{description}</p>
          </a>
        </div>
      </div>"""


def build_filter_tabs(entries: list[dict]) -> str:
    EXCLUDE_FROM_FILTERS = {"article"}
    types = [e.get("type", "article") for e in entries]
    tabs = [('all', 'All')]
    tabs += [(f'type:{t}', type_label(t)) for t in sorted(set(types)) if t not in EXCLUDE_FROM_FILTERS]

    for book_num in sorted(CHAPTERS):
        for ch_num in sorted(CHAPTERS[book_num]):
            ch_t = CHAPTERS[book_num][ch_num]
            label = f"Chapter {ch_num} · {ch_t}"
            tabs.append((f'chapter:{ch_num}', label))

    buttons = []
    for i, (key, label) in enumerate(tabs):
        active = 'bg-gray-900 text-white border-gray-900' if i == 0 else 'text-gray-900 border-gray-900 hover:bg-gray-900 hover:text-white'
        buttons.append(
            f'      <button onclick="filter(\'{key}\')" data-filter="{key}" '
            f'class="filter-btn {active} px-4 py-1.5 rounded-full text-sm font-medium border transition-all">{label}</button>'
        )
    return "\n".join(buttons)


def build_index(entries: list[dict]) -> str:
    cards      = "\n".join(render_card(e) for e in entries)
    timeline_h = build_timeline_h(entries)
    year       = datetime.now().year

    return HTML_HEAD.format(title="Collection", font_path="") + f"""\
{_build_nav("", "collection")}
  <section class="max-w-6xl mx-auto px-6 pt-16 pb-10">
    <h1 class="font-display text-7xl font-bold tracking-tight text-gray-900">Collection</h1>
    <div class="mt-5 max-w-2xl">
      <p class="text-sm text-gray-600 leading-snug">The Collection is the companion archive to the <em>Datartefact</em> book series, bringing together the artifacts, instruments, recording systems, and material objects discussed throughout the project. Spanning early accounting devices, cartographic objects, textiles, scientific instruments, photography, sound recording, and computation, it explores how objects themselves can function as documents, or as systems of documents used to encode, store, measure, and transmit knowledge.</p>
      <p class="mt-2 text-sm text-gray-600 leading-snug">The collection can be browsed through a grid view or along a chronological timeline connecting artifacts across centuries and disciplines. Conceived as an expanding research archive, it will continue to grow over time alongside the development of the books.</p>
    </div>
  </section>
  <div id="filter-badge" class="hidden max-w-6xl mx-auto px-6 pb-3 flex justify-center">
    <button onclick="clearFilter()" class="text-sm text-gray-500 hover:text-gray-900 transition-colors">← All entries</button>
  </div>
  <section class="max-w-6xl mx-auto px-6 pb-4 flex justify-center gap-2">
      <button onclick="setView('grid')" id="btn-grid"
        class="border border-gray-900 px-6 py-2 text-sm font-medium bg-gray-900 text-white transition-all">Grid</button>
      <button onclick="shuffleGrid()" id="btn-shuffle"
        class="border border-gray-900 px-6 py-2 text-sm font-medium text-gray-900 hover:bg-gray-900 hover:text-white transition-all">⇄ Shuffle</button>
      <button onclick="setView('timeline-h')" id="btn-timeline-h"
        class="border border-gray-900 px-6 py-2 text-sm font-medium text-gray-900 hover:bg-gray-900 hover:text-white transition-all">↔ Timeline</button>
  </section>

  <main class="w-full pb-24 flex-1 px-4">
    <div class="max-w-6xl mx-auto">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" id="card-grid">
{cards}
      </div>
    </div>
    <div id="timeline-h-view" class="hidden pt-6 pb-16 px-0">
{timeline_h}
    </div>
  </main>
{build_footer(year)}
  <script>
    let activeFilter = 'all';

    function updateDisplay() {{
      ['#card-grid .card-wrapper', '#timeline-h-view .timeline-h-entry'].forEach(sel => {{
        document.querySelectorAll(sel).forEach(item => {{
          let matches = true;
          if (activeFilter !== 'all') {{
            if (activeFilter.startsWith('chapter:')) matches = item.dataset.chapter == activeFilter.split(':')[1];
            else if (activeFilter.startsWith('type:'))  matches = item.dataset.type === activeFilter.split(':')[1];
          }}
          item.style.display = matches ? '' : 'none';
        }});
      }});
    }}

    function filter(type) {{
      activeFilter = type;
      document.querySelectorAll('.filter-btn').forEach(btn => {{
        const active = btn.dataset.filter === type;
        btn.classList.toggle('bg-gray-900', active);
        btn.classList.toggle('text-white', active);
      }});
      const badge = document.getElementById('filter-badge');
      if (badge) badge.classList.toggle('hidden', type === 'all');
      updateDisplay();
    }}

    function clearFilter() {{
      history.replaceState(null, '', window.location.pathname);
      filter('all');
    }}

    function setView(view) {{
      const views = {{ grid: 'card-grid', 'timeline-h': 'timeline-h-view' }};
      const btns  = {{ grid: 'btn-grid', 'timeline-h': 'btn-timeline-h' }};
      Object.entries(views).forEach(([v, id]) => {{
        const el = document.getElementById(id);
        if (el) el.classList.toggle('hidden', v !== view);
      }});
      Object.entries(btns).forEach(([v, id]) => {{
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.classList.toggle('bg-gray-900', v === view);
        btn.classList.toggle('text-white',  v === view);
        btn.classList.toggle('text-gray-900', v !== view);
      }});
    }}

    function shuffleGrid() {{
      setView('grid');
      const grid = document.getElementById('card-grid');
      const cards = Array.from(grid.querySelectorAll('.card-wrapper'));
      for (let i = cards.length - 1; i > 0; i--) {{
        const j = Math.floor(Math.random() * (i + 1));
        [cards[i], cards[j]] = [cards[j], cards[i]];
      }}
      cards.forEach(c => grid.appendChild(c));
    }}

    // Horizontal timeline: arrows + drag-to-scroll
    (function() {{
      const scroll = document.getElementById('tl-h-scroll');
      if (!scroll) return;
      const prev = document.getElementById('tl-h-prev');
      const next = document.getElementById('tl-h-next');
      function updateArrows() {{
        const atStart = scroll.scrollLeft <= 0;
        const atEnd   = scroll.scrollLeft >= scroll.scrollWidth - scroll.clientWidth - 1;
        prev.style.display = atStart ? 'none' : '';
        next.style.display = atEnd   ? 'none' : '';
      }}
      updateArrows();
      scroll.addEventListener('scroll', updateArrows);
      prev.addEventListener('click', () => scroll.scrollBy({{ left: -480, behavior: 'smooth' }}));
      next.addEventListener('click', () => scroll.scrollBy({{ left:  480, behavior: 'smooth' }}));
      let down = false, startX, startScroll;
      scroll.addEventListener('mousedown',  e => {{ down = true; startX = e.pageX; startScroll = scroll.scrollLeft; scroll.style.cursor = 'grabbing'; }});
      scroll.addEventListener('mouseleave', ()  => {{ down = false; scroll.style.cursor = 'grab'; }});
      scroll.addEventListener('mouseup',    ()  => {{ down = false; scroll.style.cursor = 'grab'; }});
      scroll.addEventListener('mousemove',  e  => {{ if (!down) return; e.preventDefault(); scroll.scrollLeft = startScroll - (e.pageX - startX); }});
    }})();

    (function() {{
      const params = new URLSearchParams(window.location.search);
      if (params.get('chapter')) filter('chapter:' + params.get('chapter'));
      else filter('all');
    }})();
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Individual post pages
# ---------------------------------------------------------------------------

def build_post(entry: dict) -> str:
    MD.reset()
    type_key = entry.get("type", "article")
    title = entry.get("title", "Untitled")
    author = entry.get("author", "")
    date_str = fmt_date(entry.get("date_obj") or entry.get("date"))
    description = entry.get("description", "")
    body_html = MD.convert(entry["body"])
    year = datetime.now().year
    book = entry.get("book")
    chapter = entry.get("chapter")
    image = entry.get("image", "")

    chips_html = ""
    if book:
        chips_html += f'<span class="inline-block border border-gray-900 text-xs font-semibold uppercase tracking-widest px-3 py-1 mr-2">Book {book}</span>'
    if chapter:
        chips_html += f'<span class="inline-block border border-gray-900 text-xs font-semibold uppercase tracking-widest px-3 py-1">Chapter {chapter}</span>'

    dithered_image = f"images/dithered/{Path(image).stem}.png" if image else ""
    image_copyright = entry.get("image_copyright", "")
    copyright_html = f'<p class="mt-2 mb-4 text-xs text-gray-400 italic">{image_copyright}</p>' if image_copyright else ""
    image_html = (f'<img src="../{dithered_image}" alt="{title}" class="w-full">{copyright_html}') if dithered_image else ""
    ch_title = chapter_title(book, chapter)
    chapter_label = f"Chapter {chapter} · {ch_title}" if ch_title else f"Chapter {chapter}"
    book_chip = f'<a href="../collection.html?book={book}" class="inline-block border border-gray-900 text-xs font-semibold uppercase tracking-widest px-3 py-1 mr-2 hover:bg-gray-900 hover:text-white transition-colors">Book {book}</a>' if book else ""
    chapter_chip = f'<a href="../collection.html?chapter={chapter}" class="inline-block border border-gray-900 text-xs font-bold uppercase tracking-widest px-3 py-1 hover:bg-gray-900 hover:text-white transition-colors">{chapter_label}</a>' if chapter else ""

    sources = parse_sources(entry.get("sources"))
    if sources:
        _arrow = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" class="inline-block w-3 h-3 mb-0.5" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1.5 8.5L8.5 1.5M4 1.5h4.5V6"/></svg>'
        _links = "\n".join(
            f'        <li><a href="{url}" target="_blank" rel="noopener noreferrer" class="hover:underline">{label} {_arrow}</a></li>'
            for label, url in sources
        )
        sources_html = f"""    <div class="mt-12 font-sans">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Further reading</p>
      <ul class="space-y-2 text-sm text-gray-900">
{_links}
      </ul>
    </div>"""
    else:
        sources_html = ""

    return HTML_HEAD.format(title=title, font_path="../") + f"""\
{_build_nav("../", "collection")}
  <main class="max-w-6xl mx-auto px-6 pt-16 pb-24 flex-1 w-full">
    <a href="../collection.html" class="text-sm text-gray-900 hover:underline transition-colors">&larr; Back to collection</a>
    <div class="w-full border border-gray-900 mt-8 flex flex-col md:flex-row">
      <div class="p-6 md:w-1/4 border-b md:border-b-0 md:border-r border-gray-900">
        <div class="flex flex-wrap gap-2">
          {book_chip}{chapter_chip}
        </div>
        {f'<p class="mt-4 text-xs text-gray-500"><span class="font-semibold text-gray-900">Author</span> {author}</p>' if author else ''}
        {f'<p class="mt-1 text-xs text-gray-500"><span class="font-semibold text-gray-900">Date of creation</span> {date_str}</p>' if date_str else ''}
      </div>
      <div class="p-6 md:w-3/4">
        <span class="font-display text-4xl md:text-6xl font-bold leading-none text-gray-900">{title}</span>
        {f'<p class="mt-4 text-base text-gray-900 leading-relaxed">{description}</p>' if description else ''}
      </div>
    </div>
    {image_html}
    <div class="mt-10 prose text-gray-900 text-base">
      {body_html}
    </div>
{sources_html}
  </main>
{build_footer(year, prefix="../")}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Instagram page
# ---------------------------------------------------------------------------

# To add a post: go to instagram.com, open the post, click ··· → Embed,
# copy the <blockquote>…</blockquote> block and paste it into INSTAGRAM_POSTS below.
INSTAGRAM_POSTS = [
    """<blockquote class="instagram-media" data-instgrm-captioned data-instgrm-permalink="https://www.instagram.com/p/DYFj2qVjQHv/?utm_source=ig_embed&amp;utm_campaign=loading" data-instgrm-version="14" style=" background:#FFF; border:0; border-radius:3px; box-shadow:0 0 1px 0 rgba(0,0,0,0.5),0 1px 10px 0 rgba(0,0,0,0.15); margin: 1px; max-width:540px; min-width:326px; padding:0; width:99.375%; width:-webkit-calc(100% - 2px); width:calc(100% - 2px);"><div style="padding:16px;"> <a href="https://www.instagram.com/p/DYFj2qVjQHv/?utm_source=ig_embed&amp;utm_campaign=loading" style=" background:#FFFFFF; line-height:0; padding:0 0; text-align:center; text-decoration:none; width:100%;" target="_blank"> <div style=" display: flex; flex-direction: row; align-items: center;"> <div style="background-color: #F4F4F4; border-radius: 50%; flex-grow: 0; height: 40px; margin-right: 14px; width: 40px;"></div> <div style="display: flex; flex-direction: column; flex-grow: 1; justify-content: center;"> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; margin-bottom: 6px; width: 100px;"></div> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; width: 60px;"></div></div></div><div style="padding: 19% 0;"></div> <div style="display:block; height:50px; margin:0 auto 12px; width:50px;"><svg width="50px" height="50px" viewBox="0 0 60 60" version="1.1" xmlns="https://www.w3.org/2000/svg" xmlns:xlink="https://www.w3.org/1999/xlink"><g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"><g transform="translate(-511.000000, -20.000000)" fill="#000000"><g><path d="M556.869,30.41 C554.814,30.41 553.148,32.076 553.148,34.131 C553.148,36.186 554.814,37.852 556.869,37.852 C558.924,37.852 560.59,36.186 560.59,34.131 C560.59,32.076 558.924,30.41 556.869,30.41 M541,60.657 C535.114,60.657 530.342,55.887 530.342,50 C530.342,44.114 535.114,39.342 541,39.342 C546.887,39.342 551.658,44.114 551.658,50 C551.658,55.887 546.887,60.657 541,60.657 M541,33.886 C532.1,33.886 524.886,41.1 524.886,50 C524.886,58.899 532.1,66.113 541,66.113 C549.9,66.113 557.115,58.899 557.115,50 C557.115,41.1 549.9,33.886 541,33.886 M565.378,62.101 C565.244,65.022 564.756,66.606 564.346,67.663 C563.803,69.06 563.154,70.057 562.106,71.106 C561.058,72.155 560.06,72.803 558.662,73.347 C557.607,73.757 556.021,74.244 553.102,74.378 C549.944,74.521 548.997,74.552 541,74.552 C533.003,74.552 532.056,74.521 528.898,74.378 C525.979,74.244 524.393,73.757 523.338,73.347 C521.94,72.803 520.942,72.155 519.894,71.106 C518.846,70.057 518.197,69.06 517.654,67.663 C517.244,66.606 516.755,65.022 516.623,62.101 C516.479,58.943 516.448,57.996 516.448,50 C516.448,42.003 516.479,41.056 516.623,37.899 C516.755,34.978 517.244,33.391 517.654,32.338 C518.197,30.938 518.846,29.942 519.894,28.894 C520.942,27.846 521.94,27.196 523.338,26.654 C524.393,26.244 525.979,25.756 528.898,25.623 C532.057,25.479 533.004,25.448 541,25.448 C548.997,25.448 549.943,25.479 553.102,25.623 C556.021,25.756 557.607,26.244 558.662,26.654 C560.06,27.196 561.058,27.846 562.106,28.894 C563.154,29.942 563.803,30.938 564.346,32.338 C564.756,33.391 565.244,34.978 565.378,37.899 C565.522,41.056 565.552,42.003 565.552,50 C565.552,57.996 565.522,58.943 565.378,62.101 M570.82,37.631 C570.674,34.438 570.167,32.258 569.425,30.349 C568.659,28.377 567.633,26.702 565.965,25.035 C564.297,23.368 562.623,22.342 560.652,21.575 C558.743,20.834 556.562,20.326 553.369,20.18 C550.169,20.033 549.148,20 541,20 C532.853,20 531.831,20.033 528.631,20.18 C525.438,20.326 523.257,20.834 521.349,21.575 C519.376,22.342 517.703,23.368 516.035,25.035 C514.368,26.702 513.342,28.377 512.574,30.349 C511.834,32.258 511.326,34.438 511.181,37.631 C511.035,40.831 511,41.851 511,50 C511,58.147 511.035,59.17 511.181,62.369 C511.326,65.562 511.834,67.743 512.574,69.651 C513.342,71.625 514.368,73.296 516.035,74.965 C517.703,76.634 519.376,77.658 521.349,78.425 C523.257,79.167 525.438,79.673 528.631,79.82 C531.831,79.965 532.853,80.001 541,80.001 C549.148,80.001 550.169,79.965 553.369,79.82 C556.562,79.673 558.743,79.167 560.652,78.425 C562.623,77.658 564.297,76.634 565.965,74.965 C567.633,73.296 568.659,71.625 569.425,69.651 C570.167,67.743 570.674,65.562 570.82,62.369 C570.966,59.17 571,58.147 571,50 C571,41.851 570.966,40.831 570.82,37.631"></path></g></g></g></svg></div><div style="padding-top: 8px;"> <div style=" color:#3897f0; font-family:Arial,sans-serif; font-size:14px; font-style:normal; font-weight:550; line-height:18px;">View this post on Instagram</div></div><div style="padding: 12.5% 0;"></div> <div style="display: flex; flex-direction: row; margin-bottom: 14px; align-items: center;"><div> <div style="background-color: #F4F4F4; border-radius: 50%; height: 12.5px; width: 12.5px; transform: translateX(0px) translateY(7px);"></div> <div style="background-color: #F4F4F4; height: 12.5px; transform: rotate(-45deg) translateX(3px) translateY(1px); width: 12.5px; flex-grow: 0; margin-right: 14px; margin-left: 2px;"></div> <div style="background-color: #F4F4F4; border-radius: 50%; height: 12.5px; width: 12.5px; transform: translateX(9px) translateY(-18px);"></div></div><div style="margin-left: 8px;"> <div style=" background-color: #F4F4F4; border-radius: 50%; flex-grow: 0; height: 20px; width: 20px;"></div> <div style=" width: 0; height: 0; border-top: 2px solid transparent; border-left: 6px solid #f4f4f4; border-bottom: 2px solid transparent; transform: translateX(16px) translateY(-4px) rotate(30deg)"></div></div><div style="margin-left: auto;"> <div style=" width: 0px; border-top: 8px solid #F4F4F4; border-right: 8px solid transparent; transform: translateY(16px);"></div> <div style=" background-color: #F4F4F4; flex-grow: 0; height: 12px; width: 16px; transform: translateY(-4px);"></div> <div style=" width: 0; height: 0; border-top: 8px solid #F4F4F4; border-left: 8px solid transparent; transform: translateY(-4px) translateX(8px);"></div></div></div> <div style="display: flex; flex-direction: column; flex-grow: 1; justify-content: center; margin-bottom: 24px;"> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; margin-bottom: 6px; width: 224px;"></div> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; width: 144px;"></div></div></a><p style=" color:#c9c8cd; font-family:Arial,sans-serif; font-size:14px; line-height:17px; margin-bottom:0; margin-top:8px; overflow:hidden; padding:8px 0 7px; text-align:center; text-overflow:ellipsis; white-space:nowrap;"><a href="https://www.instagram.com/p/DYFj2qVjQHv/?utm_source=ig_embed&amp;utm_campaign=loading" style=" color:#c9c8cd; font-family:Arial,sans-serif; font-size:14px; font-style:normal; font-weight:normal; line-height:17px; text-decoration:none;" target="_blank">A post shared by Anne-Laure (@annelaurefre)</a></p></div></blockquote>""",
    """<blockquote class="instagram-media" data-instgrm-captioned data-instgrm-permalink="https://www.instagram.com/p/DYH6KMWDVVR/?utm_source=ig_embed&amp;utm_campaign=loading" data-instgrm-version="14" style=" background:#FFF; border:0; border-radius:3px; box-shadow:0 0 1px 0 rgba(0,0,0,0.5),0 1px 10px 0 rgba(0,0,0,0.15); margin: 1px; max-width:540px; min-width:326px; padding:0; width:99.375%; width:-webkit-calc(100% - 2px); width:calc(100% - 2px);"><div style="padding:16px;"> <a href="https://www.instagram.com/p/DYH6KMWDVVR/?utm_source=ig_embed&amp;utm_campaign=loading" style=" background:#FFFFFF; line-height:0; padding:0 0; text-align:center; text-decoration:none; width:100%;" target="_blank"> <div style=" display: flex; flex-direction: row; align-items: center;"> <div style="background-color: #F4F4F4; border-radius: 50%; flex-grow: 0; height: 40px; margin-right: 14px; width: 40px;"></div> <div style="display: flex; flex-direction: column; flex-grow: 1; justify-content: center;"> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; margin-bottom: 6px; width: 100px;"></div> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; width: 60px;"></div></div></div><div style="padding: 19% 0;"></div> <div style="display:block; height:50px; margin:0 auto 12px; width:50px;"><svg width="50px" height="50px" viewBox="0 0 60 60" version="1.1" xmlns="https://www.w3.org/2000/svg" xmlns:xlink="https://www.w3.org/1999/xlink"><g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"><g transform="translate(-511.000000, -20.000000)" fill="#000000"><g><path d="M556.869,30.41 C554.814,30.41 553.148,32.076 553.148,34.131 C553.148,36.186 554.814,37.852 556.869,37.852 C558.924,37.852 560.59,36.186 560.59,34.131 C560.59,32.076 558.924,30.41 556.869,30.41 M541,60.657 C535.114,60.657 530.342,55.887 530.342,50 C530.342,44.114 535.114,39.342 541,39.342 C546.887,39.342 551.658,44.114 551.658,50 C551.658,55.887 546.887,60.657 541,60.657 M541,33.886 C532.1,33.886 524.886,41.1 524.886,50 C524.886,58.899 532.1,66.113 541,66.113 C549.9,66.113 557.115,58.899 557.115,50 C557.115,41.1 549.9,33.886 541,33.886 M565.378,62.101 C565.244,65.022 564.756,66.606 564.346,67.663 C563.803,69.06 563.154,70.057 562.106,71.106 C561.058,72.155 560.06,72.803 558.662,73.347 C557.607,73.757 556.021,74.244 553.102,74.378 C549.944,74.521 548.997,74.552 541,74.552 C533.003,74.552 532.056,74.521 528.898,74.378 C525.979,74.244 524.393,73.757 523.338,73.347 C521.94,72.803 520.942,72.155 519.894,71.106 C518.846,70.057 518.197,69.06 517.654,67.663 C517.244,66.606 516.755,65.022 516.623,62.101 C516.479,58.943 516.448,57.996 516.448,50 C516.448,42.003 516.479,41.056 516.623,37.899 C516.755,34.978 517.244,33.391 517.654,32.338 C518.197,30.938 518.846,29.942 519.894,28.894 C520.942,27.846 521.94,27.196 523.338,26.654 C524.393,26.244 525.979,25.756 528.898,25.623 C532.057,25.479 533.004,25.448 541,25.448 C548.997,25.448 549.943,25.479 553.102,25.623 C556.021,25.756 557.607,26.244 558.662,26.654 C560.06,27.196 561.058,27.846 562.106,28.894 C563.154,29.942 563.803,30.938 564.346,32.338 C564.756,33.391 565.244,34.978 565.378,37.899 C565.522,41.056 565.552,42.003 565.552,50 C565.552,57.996 565.522,58.943 565.378,62.101 M570.82,37.631 C570.674,34.438 570.167,32.258 569.425,30.349 C568.659,28.377 567.633,26.702 565.965,25.035 C564.297,23.368 562.623,22.342 560.652,21.575 C558.743,20.834 556.562,20.326 553.369,20.18 C550.169,20.033 549.148,20 541,20 C532.853,20 531.831,20.033 528.631,20.18 C525.438,20.326 523.257,20.834 521.349,21.575 C519.376,22.342 517.703,23.368 516.035,25.035 C514.368,26.702 513.342,28.377 512.574,30.349 C511.834,32.258 511.326,34.438 511.181,37.631 C511.035,40.831 511,41.851 511,50 C511,58.147 511.035,59.17 511.181,62.369 C511.326,65.562 511.834,67.743 512.574,69.651 C513.342,71.625 514.368,73.296 516.035,74.965 C517.703,76.634 519.376,77.658 521.349,78.425 C523.257,79.167 525.438,79.673 528.631,79.82 C531.831,79.965 532.853,80.001 541,80.001 C549.148,80.001 550.169,79.965 553.369,79.82 C556.562,79.673 558.743,79.167 560.652,78.425 C562.623,77.658 564.297,76.634 565.965,74.965 C567.633,73.296 568.659,71.625 569.425,69.651 C570.167,67.743 570.674,65.562 570.82,62.369 C570.966,59.17 571,58.147 571,50 C571,41.851 570.966,40.831 570.82,37.631"></path></g></g></g></svg></div><div style="padding-top: 8px;"> <div style=" color:#3897f0; font-family:Arial,sans-serif; font-size:14px; font-style:normal; font-weight:550; line-height:18px;">View this post on Instagram</div></div><div style="padding: 12.5% 0;"></div> <div style="display: flex; flex-direction: row; margin-bottom: 14px; align-items: center;"><div> <div style="background-color: #F4F4F4; border-radius: 50%; height: 12.5px; width: 12.5px; transform: translateX(0px) translateY(7px);"></div> <div style="background-color: #F4F4F4; height: 12.5px; transform: rotate(-45deg) translateX(3px) translateY(1px); width: 12.5px; flex-grow: 0; margin-right: 14px; margin-left: 2px;"></div> <div style="background-color: #F4F4F4; border-radius: 50%; height: 12.5px; width: 12.5px; transform: translateX(9px) translateY(-18px);"></div></div><div style="margin-left: 8px;"> <div style=" background-color: #F4F4F4; border-radius: 50%; flex-grow: 0; height: 20px; width: 20px;"></div> <div style=" width: 0; height: 0; border-top: 2px solid transparent; border-left: 6px solid #f4f4f4; border-bottom: 2px solid transparent; transform: translateX(16px) translateY(-4px) rotate(30deg)"></div></div><div style="margin-left: auto;"> <div style=" width: 0px; border-top: 8px solid #F4F4F4; border-right: 8px solid transparent; transform: translateY(16px);"></div> <div style=" background-color: #F4F4F4; flex-grow: 0; height: 12px; width: 16px; transform: translateY(-4px);"></div> <div style=" width: 0; height: 0; border-top: 8px solid #F4F4F4; border-left: 8px solid transparent; transform: translateY(-4px) translateX(8px);"></div></div></div> <div style="display: flex; flex-direction: column; flex-grow: 1; justify-content: center; margin-bottom: 24px;"> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; margin-bottom: 6px; width: 224px;"></div> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; width: 144px;"></div></div></a><p style=" color:#c9c8cd; font-family:Arial,sans-serif; font-size:14px; line-height:17px; margin-bottom:0; margin-top:8px; overflow:hidden; padding:8px 0 7px; text-align:center; text-overflow:ellipsis; white-space:nowrap;"><a href="https://www.instagram.com/p/DYH6KMWDVVR/?utm_source=ig_embed&amp;utm_campaign=loading" style=" color:#c9c8cd; font-family:Arial,sans-serif; font-size:14px; font-style:normal; font-weight:normal; line-height:17px; text-decoration:none;" target="_blank">A post shared by Anne-Laure (@annelaurefre)</a></p></div></blockquote>""",
    """<blockquote class="instagram-media" data-instgrm-captioned data-instgrm-permalink="https://www.instagram.com/p/DXeZoRqlA89/?utm_source=ig_embed&amp;utm_campaign=loading" data-instgrm-version="14" style=" background:#FFF; border:0; border-radius:3px; box-shadow:0 0 1px 0 rgba(0,0,0,0.5),0 1px 10px 0 rgba(0,0,0,0.15); margin: 1px; max-width:540px; min-width:326px; padding:0; width:99.375%; width:-webkit-calc(100% - 2px); width:calc(100% - 2px);"><div style="padding:16px;"> <a href="https://www.instagram.com/p/DXeZoRqlA89/?utm_source=ig_embed&amp;utm_campaign=loading" style=" background:#FFFFFF; line-height:0; padding:0 0; text-align:center; text-decoration:none; width:100%;" target="_blank"> <div style=" display: flex; flex-direction: row; align-items: center;"> <div style="background-color: #F4F4F4; border-radius: 50%; flex-grow: 0; height: 40px; margin-right: 14px; width: 40px;"></div> <div style="display: flex; flex-direction: column; flex-grow: 1; justify-content: center;"> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; margin-bottom: 6px; width: 100px;"></div> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; width: 60px;"></div></div></div><div style="padding: 19% 0;"></div> <div style="display:block; height:50px; margin:0 auto 12px; width:50px;"><svg width="50px" height="50px" viewBox="0 0 60 60" version="1.1" xmlns="https://www.w3.org/2000/svg" xmlns:xlink="https://www.w3.org/1999/xlink"><g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"><g transform="translate(-511.000000, -20.000000)" fill="#000000"><g><path d="M556.869,30.41 C554.814,30.41 553.148,32.076 553.148,34.131 C553.148,36.186 554.814,37.852 556.869,37.852 C558.924,37.852 560.59,36.186 560.59,34.131 C560.59,32.076 558.924,30.41 556.869,30.41 M541,60.657 C535.114,60.657 530.342,55.887 530.342,50 C530.342,44.114 535.114,39.342 541,39.342 C546.887,39.342 551.658,44.114 551.658,50 C551.658,55.887 546.887,60.657 541,60.657 M541,33.886 C532.1,33.886 524.886,41.1 524.886,50 C524.886,58.899 532.1,66.113 541,66.113 C549.9,66.113 557.115,58.899 557.115,50 C557.115,41.1 549.9,33.886 541,33.886 M565.378,62.101 C565.244,65.022 564.756,66.606 564.346,67.663 C563.803,69.06 563.154,70.057 562.106,71.106 C561.058,72.155 560.06,72.803 558.662,73.347 C557.607,73.757 556.021,74.244 553.102,74.378 C549.944,74.521 548.997,74.552 541,74.552 C533.003,74.552 532.056,74.521 528.898,74.378 C525.979,74.244 524.393,73.757 523.338,73.347 C521.94,72.803 520.942,72.155 519.894,71.106 C518.846,70.057 518.197,69.06 517.654,67.663 C517.244,66.606 516.755,65.022 516.623,62.101 C516.479,58.943 516.448,57.996 516.448,50 C516.448,42.003 516.479,41.056 516.623,37.899 C516.755,34.978 517.244,33.391 517.654,32.338 C518.197,30.938 518.846,29.942 519.894,28.894 C520.942,27.846 521.94,27.196 523.338,26.654 C524.393,26.244 525.979,25.756 528.898,25.623 C532.057,25.479 533.004,25.448 541,25.448 C548.997,25.448 549.943,25.479 553.102,25.623 C556.021,25.756 557.607,26.244 558.662,26.654 C560.06,27.196 561.058,27.846 562.106,28.894 C563.154,29.942 563.803,30.938 564.346,32.338 C564.756,33.391 565.244,34.978 565.378,37.899 C565.522,41.056 565.552,42.003 565.552,50 C565.552,57.996 565.522,58.943 565.378,62.101 M570.82,37.631 C570.674,34.438 570.167,32.258 569.425,30.349 C568.659,28.377 567.633,26.702 565.965,25.035 C564.297,23.368 562.623,22.342 560.652,21.575 C558.743,20.834 556.562,20.326 553.369,20.18 C550.169,20.033 549.148,20 541,20 C532.853,20 531.831,20.033 528.631,20.18 C525.438,20.326 523.257,20.834 521.349,21.575 C519.376,22.342 517.703,23.368 516.035,25.035 C514.368,26.702 513.342,28.377 512.574,30.349 C511.834,32.258 511.326,34.438 511.181,37.631 C511.035,40.831 511,41.851 511,50 C511,58.147 511.035,59.17 511.181,62.369 C511.326,65.562 511.834,67.743 512.574,69.651 C513.342,71.625 514.368,73.296 516.035,74.965 C517.703,76.634 519.376,77.658 521.349,78.425 C523.257,79.167 525.438,79.673 528.631,79.82 C531.831,79.965 532.853,80.001 541,80.001 C549.148,80.001 550.169,79.965 553.369,79.82 C556.562,79.673 558.743,79.167 560.652,78.425 C562.623,77.658 564.297,76.634 565.965,74.965 C567.633,73.296 568.659,71.625 569.425,69.651 C570.167,67.743 570.674,65.562 570.82,62.369 C570.966,59.17 571,58.147 571,50 C571,41.851 570.966,40.831 570.82,37.631"></path></g></g></g></svg></div><div style="padding-top: 8px;"> <div style=" color:#3897f0; font-family:Arial,sans-serif; font-size:14px; font-style:normal; font-weight:550; line-height:18px;">View this post on Instagram</div></div><div style="padding: 12.5% 0;"></div> <div style="display: flex; flex-direction: row; margin-bottom: 14px; align-items: center;"><div> <div style="background-color: #F4F4F4; border-radius: 50%; height: 12.5px; width: 12.5px; transform: translateX(0px) translateY(7px);"></div> <div style="background-color: #F4F4F4; height: 12.5px; transform: rotate(-45deg) translateX(3px) translateY(1px); width: 12.5px; flex-grow: 0; margin-right: 14px; margin-left: 2px;"></div> <div style="background-color: #F4F4F4; border-radius: 50%; height: 12.5px; width: 12.5px; transform: translateX(9px) translateY(-18px);"></div></div><div style="margin-left: 8px;"> <div style=" background-color: #F4F4F4; border-radius: 50%; flex-grow: 0; height: 20px; width: 20px;"></div> <div style=" width: 0; height: 0; border-top: 2px solid transparent; border-left: 6px solid #f4f4f4; border-bottom: 2px solid transparent; transform: translateX(16px) translateY(-4px) rotate(30deg)"></div></div><div style="margin-left: auto;"> <div style=" width: 0px; border-top: 8px solid #F4F4F4; border-right: 8px solid transparent; transform: translateY(16px);"></div> <div style=" background-color: #F4F4F4; flex-grow: 0; height: 12px; width: 16px; transform: translateY(-4px);"></div> <div style=" width: 0; height: 0; border-top: 8px solid #F4F4F4; border-left: 8px solid transparent; transform: translateY(-4px) translateX(8px);"></div></div></div> <div style="display: flex; flex-direction: column; flex-grow: 1; justify-content: center; margin-bottom: 24px;"> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; margin-bottom: 6px; width: 224px;"></div> <div style=" background-color: #F4F4F4; border-radius: 4px; flex-grow: 0; height: 14px; width: 144px;"></div></div></a><p style=" color:#c9c8cd; font-family:Arial,sans-serif; font-size:14px; line-height:17px; margin-bottom:0; margin-top:8px; overflow:hidden; padding:8px 0 7px; text-align:center; text-overflow:ellipsis; white-space:nowrap;"><a href="https://www.instagram.com/p/DXeZoRqlA89/?utm_source=ig_embed&amp;utm_campaign=loading" style=" color:#c9c8cd; font-family:Arial,sans-serif; font-size:14px; font-style:normal; font-weight:normal; line-height:17px; text-decoration:none;" target="_blank">A post shared by Anne-Laure (@annelaurefre)</a></p></div></blockquote>""",
]

def build_instagram() -> str:
    year = datetime.now().year
    nav = NAV_INDEX

    if INSTAGRAM_POSTS:
        grid_items = "\n".join(
            f'      <div class="border-b border-r border-gray-900 p-6 flex items-start justify-center">{post}</div>'
            for post in INSTAGRAM_POSTS
        )
        grid = f'<div class="px-4"><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 border-t border-l border-gray-900">\n{grid_items}\n    </div></div>'
        embed_script = '<script async src="//www.instagram.com/embed.js"></script>'
    else:
        grid = """\
    <div class="max-w-2xl mx-auto px-6 mt-16 border border-dashed border-gray-400 p-8 text-sm text-gray-900 leading-relaxed font-sans">
      <p class="font-semibold">No posts added yet.</p>
      <p class="mt-2">To embed an Instagram post:</p>
      <ol class="list-decimal pl-5 mt-2 space-y-1">
        <li>Open the post on instagram.com</li>
        <li>Click the <strong>···</strong> menu → <strong>Embed</strong></li>
        <li>Copy the <code>&lt;blockquote&gt;…&lt;/blockquote&gt;</code> snippet</li>
        <li>Paste it into <code>INSTAGRAM_POSTS</code> in <code>build.py</code></li>
        <li>Run <code>python3 build.py</code></li>
      </ol>
    </div>"""
        embed_script = ""

    return HTML_HEAD.format(title="Instagram", font_path="") + f"""\
{nav}
  <section class="max-w-6xl mx-auto px-6 pt-16 pb-10">
    <h1 class="font-display text-7xl font-bold tracking-tight text-gray-900">Instagram</h1>
    <p class="mt-3 text-gray-900 text-base max-w-xl">A selection of posts documenting each chapter.</p>
    <a href="https://www.instagram.com/annelaurefre/" target="_blank" rel="noopener"
      class="mt-6 inline-block bg-gray-900 text-white text-sm font-semibold uppercase tracking-widest px-6 py-2.5 hover:bg-white hover:text-gray-900 border border-gray-900 transition-colors">Follow @annelaurefre</a>
  </section>
  {grid}
  {embed_script}
{build_footer(year)}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Blog page
# ---------------------------------------------------------------------------

def load_blog_entries() -> list[dict]:
    entries = []
    for path in BLOG_DIR.glob("*.md"):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        meta.setdefault("slug", path.stem)
        meta["body"] = body
        raw_date = meta.get("date")
        if isinstance(raw_date, (date, datetime)):
            meta["date_obj"] = raw_date if isinstance(raw_date, date) else raw_date.date()
        else:
            meta["date_obj"] = None
        tags_raw = meta.get("tags", meta.get("category", ""))
        if isinstance(tags_raw, list):
            meta["tags"] = [str(t).strip() for t in tags_raw if t]
        elif tags_raw:
            meta["tags"] = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
        else:
            meta["tags"] = []
        meta.setdefault("image", "")
        entries.append(meta)
    entries.sort(key=lambda e: e["date_obj"] or date.min, reverse=True)
    return entries


def build_note_post(entry: dict) -> str:
    MD.reset()
    title = entry.get("title", "Untitled")
    tags = entry.get("tags", [])
    description = entry.get("description", "")
    body_html = MD.convert(entry["body"])
    date_str = fmt_date(entry.get("date_obj") or entry.get("date"))
    year = datetime.now().year
    image = entry.get("image", "")

    tags_html = "".join(
        f'<span class="inline-block border border-gray-900 text-xs font-semibold uppercase tracking-widest px-3 py-1 mr-2 mb-2">{t}</span>'
        for t in tags
    )

    dithered_image = f"images/dithered/{Path(image).stem}.png" if image else ""
    image_copyright = entry.get("image_copyright", "")
    copyright_html = f'<p class="mt-2 mb-4 text-xs text-gray-400 italic">{image_copyright}</p>' if image_copyright else ""
    image_html = (
        f'<img src="../{dithered_image}" alt="{title}" class="w-full mt-0">{copyright_html}'
    ) if dithered_image else ""

    sources = parse_sources(entry.get("sources"))
    if sources:
        _arrow = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" class="inline-block w-3 h-3 mb-0.5" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1.5 8.5L8.5 1.5M4 1.5h4.5V6"/></svg>'
        _links = "\n".join(
            f'        <li><a href="{url}" target="_blank" rel="noopener noreferrer" class="hover:underline">{label} {_arrow}</a></li>'
            for label, url in sources
        )
        sources_html = f"""    <div class="mt-12 font-sans max-w-3xl mx-auto">
      <p class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Further reading</p>
      <ul class="space-y-2 text-sm text-gray-900">
{_links}
      </ul>
    </div>"""
    else:
        sources_html = ""

    print_css = """  <style>
    @media print {
      header, footer, .no-print { display: none !important; }
      body { background: white; }
      .prose { max-width: 100%; }
      img { max-width: 100%; }
    }
  </style>"""

    return HTML_HEAD.format(title=title, font_path="../") + f"""\
{print_css}
{NAV}
  <main class="max-w-6xl mx-auto px-6 pt-16 pb-24 flex-1 w-full">
    <div class="flex items-center justify-between no-print">
      <a href="../notes.html" class="text-sm text-gray-900 hover:underline transition-colors">&larr; Research Notes</a>
      <button onclick="window.print()" class="text-sm text-gray-900 border border-gray-900 px-4 py-1.5 hover:bg-gray-900 hover:text-white transition-colors uppercase tracking-widest font-semibold">Export to PDF</button>
    </div>
    <div class="w-full border border-gray-900 mt-8 flex flex-col md:flex-row">
      <div class="p-6 md:w-1/4 border-b md:border-b-0 md:border-r border-gray-900">
        <div class="flex flex-wrap gap-2">
          {tags_html}
        </div>
        {f'<p class="mt-4 text-xs text-gray-500">{date_str}</p>' if date_str else ''}
      </div>
      <div class="p-6 md:w-3/4">
        <span class="font-display text-4xl md:text-6xl font-bold leading-none text-gray-900">{title}</span>
        {f'<p class="mt-4 text-base text-gray-900 leading-relaxed">{description}</p>' if description else ''}
      </div>
    </div>
    {image_html}
    <div class="mt-10 prose text-gray-900 text-base max-w-3xl mx-auto">
      {body_html}
    </div>
{sources_html}
  </main>
{build_footer(year, prefix="../")}
</body>
</html>
"""


def build_blog_post(entry: dict) -> str:
    return build_note_post(entry)


def build_notes_index(entries: list[dict]) -> str:
    year = datetime.now().year

    rows = []
    for post in entries:
        slug = post["slug"]
        date_str = fmt_date(post.get("date_obj") or post.get("date"))
        tags = post.get("tags", [])
        tags_html = "".join(
            f'<span class="inline-block border border-gray-900 text-xs font-semibold uppercase tracking-widest px-3 py-1 mr-2 mb-1">{t}</span>'
            for t in tags
        )
        image = post.get("image", "")
        dithered = f"images/dithered/{Path(image).stem}.png" if image else ""
        img_col = (
            f'<div class="md:col-span-1 border-t md:border-t-0 md:border-l border-gray-900 overflow-hidden">'
            f'<img src="{dithered}" alt="" class="w-full h-full object-cover" style="min-height:140px;max-height:200px;"></div>'
        ) if dithered else '<div class="md:col-span-1"></div>'

        rows.append(f"""\
      <a href="notes/{slug}.html" class="block border-b border-gray-900 py-10 grid grid-cols-1 md:grid-cols-4 gap-0 group">
        <div class="md:col-span-1 pr-6">
          <div class="flex flex-wrap">{tags_html}</div>
          <p class="mt-3 text-xs text-gray-500 font-sans">{date_str}</p>
        </div>
        <div class="md:col-span-2 md:px-6 mt-4 md:mt-0">
          <h2 class="font-display text-4xl font-bold leading-none text-gray-900 group-hover:underline">{post.get('title', '')}</h2>
          <p class="mt-4 text-base text-gray-900 leading-relaxed">{post.get('description', '')}</p>
        </div>
        {img_col}
      </a>""")

    feed = "\n".join(rows)

    return HTML_HEAD.format(title="Research Notes", font_path="") + f"""\
{NAV_INDEX}
  <section class="max-w-6xl mx-auto px-6 pt-16 pb-10">
    <h1 class="font-display text-7xl font-bold tracking-tight text-gray-900">Research Notes</h1>
    <p class="mt-3 text-gray-900 text-base max-w-xl">Essays on data history, material culture, and the politics of classification.</p>
  </section>
  <main class="max-w-6xl mx-auto px-6 pb-24 flex-1 w-full border-t border-gray-900">
{feed}
  </main>
{build_footer(year)}
</body>
</html>
"""


def build_blog(entries: list[dict]) -> str:
    return build_notes_index(entries)


# ---------------------------------------------------------------------------
# Book page
# ---------------------------------------------------------------------------

def build_book() -> str:
    year = datetime.now().year
    return HTML_HEAD.format(title="Book", font_path="") + f"""\
{NAV_INDEX}
  <section class="max-w-6xl mx-auto px-6 pt-16 pb-10">
    <h1 class="font-display text-7xl font-bold tracking-tight text-gray-900">Book</h1>
    <p class="mt-3 text-gray-900 text-base max-w-xl">A series on data artefacts — the objects that carry, shape, and outlive the data they hold.</p>
  </section>
  <main class="max-w-6xl mx-auto px-6 pb-24 flex-1 w-full">
    <div class="border border-gray-900 grid grid-cols-1 md:grid-cols-3">
      <div class="border-b md:border-b-0 md:border-r border-gray-900 bg-gray-100 flex items-center justify-center min-h-80 p-12">
        <div class="w-full aspect-[2/3] bg-gray-200 border border-gray-300 flex items-center justify-center">
          <span class="text-xs text-gray-400 uppercase tracking-widest font-sans">Cover</span>
        </div>
      </div>
      <div class="md:col-span-2 p-10 flex flex-col justify-between">
        <div>
          <span class="inline-block bg-gray-900 text-white text-xs font-semibold uppercase tracking-widest px-3 py-1">Book 1</span>
          <h2 class="font-display text-5xl font-bold leading-none text-gray-900 mt-6">Datartefact</h2>
          <p class="mt-2 font-display text-xl text-gray-900 leading-tight">Encoding and Recording the World</p>
          <p class="mt-2 text-sm text-gray-500 font-sans uppercase tracking-widest">Anne-Laure Freant</p>
          <p class="mt-6 text-base text-gray-900 leading-relaxed max-w-prose">
            From cuneiform tablets to punch cards, every era leaves behind objects that encode how it measured, counted, and classified the world. This book is a guided index of those objects — what they recorded, what they concealed, and what they reveal about the systems that produced them.
          </p>
          <p class="mt-4 text-base text-gray-900 leading-relaxed max-w-prose">
            Seven chapters. Seven artefacts. Each one a different way of asking: what did it mean, then, to make data?
          </p>
        </div>
        <div class="mt-10 flex items-center gap-6 border-t border-gray-900 pt-8">
          <span class="font-display text-4xl font-bold text-gray-900">€28</span>
          <a href="#" class="inline-block bg-gray-900 text-white text-sm font-semibold uppercase tracking-widest px-8 py-3 hover:bg-white hover:text-gray-900 border border-gray-900 transition-colors">Buy — coming soon</a>
        </div>
      </div>
    </div>
  </main>
{build_footer(year)}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# About page
# ---------------------------------------------------------------------------

def build_about() -> str:
    year = datetime.now().year
    return HTML_HEAD.format(title="About", font_path="") + f"""\
{NAV_INDEX}
  <section class="max-w-6xl mx-auto px-6 pt-16 pb-10">
    <h1 class="font-display text-7xl font-bold tracking-tight text-gray-900">About</h1>
  </section>
  <main class="max-w-6xl mx-auto px-6 pb-24 flex-1 w-full flex flex-col gap-6">

    <div class="border border-gray-900 grid grid-cols-1 md:grid-cols-4">
      <div class="border-b md:border-b-0 md:border-r border-gray-900 p-10 flex items-start">
        <span class="inline-block bg-gray-900 text-white text-xs font-semibold uppercase tracking-widest px-3 py-1">The project</span>
      </div>
      <div class="md:col-span-3 p-10">
        <h2 class="font-display text-4xl font-bold leading-none text-gray-900">Datartefact</h2>
        <p class="mt-6 text-base text-gray-900 leading-relaxed max-w-prose">
          Datartefact is an index of objects that carry data — cuneiform tablets, punch cards, shipping manifests, census forms. Each one is a record of how a society chose to measure, classify, and remember the world around it.
        </p>
        <p class="mt-4 text-base text-gray-900 leading-relaxed max-w-prose">
          The project asks what it means to inherit these objects and the assumptions embedded in them. It takes the form of a book, an index, and an ongoing series of notes on where this conversation is happening today.
        </p>
      </div>
    </div>

    <div class="border border-gray-900 grid grid-cols-1 md:grid-cols-4">
      <div class="border-b md:border-b-0 md:border-r border-gray-900 flex items-stretch">
        <img src="images/anne-laure.png" alt="Anne-Laure Freant" class="w-full object-cover object-top" />
      </div>
      <div class="md:col-span-3 p-10">
        <h2 class="font-display text-4xl font-bold leading-none text-gray-900">Anne-Laure Freant</h2>
        <p class="mt-6 text-base text-gray-900 leading-relaxed max-w-prose">
          Anne-Laure is a researcher and writer working at the intersection of data history, material culture, and the politics of classification. She is the author of Datartefact, a guided index of objects that encode how past societies measured and counted the world.
        </p>
        <p class="mt-4 text-base text-gray-900 leading-relaxed max-w-prose">
          Her work draws on archival research across Europe and asks what it means to inherit a dataset — and the assumptions embedded in it.
        </p>
        <div class="mt-10 flex gap-6 border-t border-gray-900 pt-8 text-sm font-sans">
          <a href="#" class="hover:underline transition-colors">Instagram</a>
          <a href="#" class="hover:underline transition-colors">X / Twitter</a>
          <a href="mailto:annelaure.freant@gmail.com" class="hover:underline transition-colors">Email</a>
        </div>
      </div>
    </div>

  </main>
{build_footer(year)}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    POSTS_DIR.mkdir(exist_ok=True)
    process_images()

    entries = load_entries()
    if not entries:
        print("No .md files found in content/ — nothing to build.")
        return

    INDEX_FILE.write_text(build_index(entries), encoding="utf-8")
    print(f"Built collection.html ({len(entries)} entries)")

    for entry in entries:
        slug = entry["slug"]
        out = POSTS_DIR / f"{slug}.html"
        out.write_text(build_post(entry), encoding="utf-8")
        print(f"  Built posts/{slug}.html")

    # Research Notes section retired — no longer built. See build_notes_index()
    # / build_note_post() / load_blog_entries() if this ever needs reviving.

    print("Done.")


if __name__ == "__main__":
    main()
