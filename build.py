#!/usr/bin/env python3
"""
Build the Drug News Roundup archive site from data/*.json.

Usage:  python3 build.py

Reads every data/YYYY-MM-DD.json file and writes:
  index.html                  latest roundup + link to the archive
  archive/index.html          list of every day
  archive/YYYY-MM-DD.html     one page per day

Nothing else is touched. Safe to re-run at any time; output is
regenerated from scratch, so the JSON files are the only source of truth.
"""

import json
import html
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ARCHIVE = ROOT / "archive"

SITE_TITLE = "Drug News Roundup"
SITE_BLURB = "A daily digest of significant drug-related enforcement news — large seizures, trafficking takedowns, cartel developments and notable sentencings."

# Canonical section order. A day's JSON may list sections in any order or
# omit them entirely; output always follows this sequence.
SECTION_ORDER = [
    ("federal", "National / Federal (US)"),
    ("local", "Local US Arrests"),
    ("south-america", "South America"),
    ("world", "Rest of World"),
    ("ongoing", "Ongoing Stories with New Developments"),
]


def e(s):
    """Escape a value for HTML text content."""
    return html.escape(str(s), quote=True)


def pretty_date(iso):
    y, m, d = (int(p) for p in iso.split("-"))
    return date(y, m, d).strftime("%A, %B %-d, %Y")


def short_date(iso):
    y, m, d = (int(p) for p in iso.split("-"))
    return date(y, m, d).strftime("%b %-d, %Y")


def load_days():
    days = []
    for path in sorted(DATA.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            day = json.load(fh)
        day.setdefault("date", path.stem)
        day.setdefault("window", "")
        day.setdefault("sections", [])
        days.append(day)
    days.sort(key=lambda d: d["date"], reverse=True)
    return days


def ordered_sections(day):
    """Return [(id, name, [stories])] in canonical order."""
    by_id = {s.get("id"): s for s in day.get("sections", [])}
    out = []
    for sid, default_name in SECTION_ORDER:
        sec = by_id.get(sid, {})
        out.append((sid, sec.get("name") or default_name, sec.get("stories") or []))
    return out


def story_html(story):
    chips = []
    if story.get("quantity"):
        chips.append(f'<span class="chip qty">{e(story["quantity"])}</span>')
    if story.get("location"):
        chips.append(f'<span class="chip">{e(story["location"])}</span>')
    if story.get("arrests"):
        chips.append(f'<span class="chip">{e(story["arrests"])}</span>')
    chip_block = f'<div class="chips">{"".join(chips)}</div>' if chips else ""

    url = story.get("url", "")
    src = story.get("source") or "Source"
    link = (
        f'<div class="source"><span class="label">Source</span>'
        f'<a href="{e(url)}" rel="noopener noreferrer nofollow" target="_blank">{e(src)}</a></div>'
        if url
        else ""
    )

    return (
        '<article class="story">'
        f'<h3>{e(story.get("headline", "Untitled"))}</h3>'
        f"{chip_block}"
        f'<p>{e(story.get("body", ""))}</p>'
        f"{link}"
        "</article>"
    )


def page(title, body, css_prefix=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{e(title)}</title>
<meta name="description" content="{e(SITE_BLURB)}">
<link rel="stylesheet" href="{css_prefix}assets/style.css">
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>
"""


def render_day(day, css_prefix="", is_home=False, day_count=0):
    sections = ordered_sections(day)
    total = sum(len(s[2]) for s in sections)

    nav = (
        '<nav class="top">'
        + (
            f'<a href="{css_prefix}index.html" aria-current="page">Latest</a>'
            if is_home
            else f'<a href="{css_prefix}index.html">Latest</a>'
        )
        + f'<a href="{css_prefix}archive/index.html">Archive'
        + (f" ({day_count} {'day' if day_count == 1 else 'days'})" if day_count else "")
        + "</a>"
        + "</nav>"
    )

    toc_items = "".join(
        f'<li><a href="#{sid}">{e(name)}</a>'
        f'<span class="count">{len(stories)}</span></li>'
        for sid, name, stories in sections
    )

    blocks = []
    for i, (sid, name, stories) in enumerate(sections, start=1):
        inner = (
            "".join(story_html(s) for s in stories)
            if stories
            else '<p class="empty">Nothing significant in the past 24 hours.</p>'
        )
        blocks.append(
            f'<section class="block" id="{sid}">'
            f'<h2><span class="num">{i}</span>{e(name)}</h2>'
            f"{inner}</section>"
        )

    window = f'<p class="window">{e(day["window"])}</p>' if day.get("window") else ""

    body = f"""<header class="masthead">
<p class="kicker">{"Latest edition" if is_home else "Archive edition"}</p>
<h1>{e(SITE_TITLE)}</h1>
<p class="dateline">{e(pretty_date(day["date"]))} · {total} {"story" if total == 1 else "stories"}</p>
{window}
{nav}
</header>

<div class="toc">
<h2>In this edition</h2>
<ol>{toc_items}</ol>
</div>

{"".join(blocks)}

<footer>
<p>Compiled automatically each morning at 6:00 AM Central. Every story is deduplicated against a running log, so nothing repeats between editions.</p>
<p>Links go to the original reporting; quantities and arrest counts are as stated by the source.</p>
</footer>"""

    return page(f"{SITE_TITLE} — {short_date(day['date'])}", body, css_prefix)


def render_archive(days):
    items = "".join(
        f'<li><a href="{e(d["date"])}.html">'
        f'<span class="d">{e(pretty_date(d["date"]))}</span>'
        f'<span class="n">{sum(len(s.get("stories") or []) for s in d.get("sections", []))} stories</span>'
        "</a></li>"
        for d in days
    )

    body = f"""<header class="masthead">
<p class="kicker">Archive</p>
<h1>{e(SITE_TITLE)}</h1>
<p class="dateline">{len(days)} {"edition" if len(days) == 1 else "editions"}</p>
<nav class="top">
<a href="../index.html">Latest</a>
<a href="index.html" aria-current="page">Archive</a>
</nav>
</header>

<ul class="archive">{items}</ul>

<footer>
<p>Every edition since the roundup began. Stories are never repeated across editions.</p>
</footer>"""

    return page(f"{SITE_TITLE} — Archive", body, css_prefix="../")


def main():
    days = load_days()
    if not days:
        raise SystemExit("No data files found in data/ — nothing to build.")

    if ARCHIVE.exists():
        shutil.rmtree(ARCHIVE)
    ARCHIVE.mkdir(parents=True)

    (ROOT / "index.html").write_text(
        render_day(days[0], css_prefix="", is_home=True, day_count=len(days)),
        encoding="utf-8",
    )

    for day in days:
        (ARCHIVE / f"{day['date']}.html").write_text(
            render_day(day, css_prefix="../", is_home=False, day_count=len(days)),
            encoding="utf-8",
        )

    (ARCHIVE / "index.html").write_text(render_archive(days), encoding="utf-8")

    (ROOT / ".nojekyll").touch()

    print(f"Built {len(days)} edition(s). Latest: {days[0]['date']}")


if __name__ == "__main__":
    main()
