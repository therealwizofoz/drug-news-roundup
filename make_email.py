#!/usr/bin/env python3
"""
Render one edition's JSON into an HTML email body.

Usage:  python3 make_email.py 2026-08-22 [> email.html]
        python3 make_email.py 2026-08-22 --out email.html

Reads data/<date>.json and writes email-safe HTML: every style is inline,
the layout is a single centred column, and nothing depends on external
CSS, JavaScript, or remote images. Apple Mail on macOS and iOS both
render it as-is.

If SITE_URL below is set, a "Read this edition on the web" link is added
under the masthead.
"""

import json
import html
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

# Fill this in once GitLab Pages is live, e.g.
# SITE_URL = "https://drug-news-roundup-a1b2c3.gitlab.io"
SITE_URL = ""

SECTION_ORDER = [
    ("federal", "National / Federal (US)"),
    ("local", "Local US Arrests"),
    ("south-america", "South America"),
    ("world", "Rest of World"),
    ("ongoing", "Ongoing Stories with New Developments"),
]

# Light-only palette, matching the website's light theme. Email clients
# handle a fixed light design far more predictably than a themed one.
BG = "#fbfaf8"
SURFACE = "#ffffff"
BORDER = "#e4e0d9"
BORDER_SF = "#d6d1c8"
INK = "#1c1a17"
INK2 = "#46423b"
INK3 = "#78726a"
ACCENT = "#9a3412"
ACCENT_SF = "#f5ede8"
CHIP_BG = "#f3f0eb"

FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif")


def e(s):
    return html.escape(str(s), quote=True)


def pretty_date(iso):
    y, m, d = (int(p) for p in iso.split("-"))
    return date(y, m, d).strftime("%A, %B %-d, %Y")


def chip(text, emphasis=False):
    if emphasis:
        style = (
            f"display:inline-block;font-size:12px;line-height:18px;"
            f"color:{ACCENT};background:{ACCENT_SF};border:1px solid {ACCENT};"
            f"border-radius:999px;padding:1px 9px;margin:0 4px 4px 0;font-weight:600;"
        )
    else:
        style = (
            f"display:inline-block;font-size:12px;line-height:18px;"
            f"color:{INK2};background:{CHIP_BG};border:1px solid {BORDER_SF};"
            f"border-radius:999px;padding:1px 9px;margin:0 4px 4px 0;"
        )
    return f'<span style="{style}">{e(text)}</span>'


def story_block(story):
    chips = ""
    if story.get("quantity"):
        chips += chip(story["quantity"], emphasis=True)
    if story.get("location"):
        chips += chip(story["location"])
    if story.get("arrests"):
        chips += chip(story["arrests"])
    chips_row = f'<div style="margin:0 0 10px;">{chips}</div>' if chips else ""

    url = story.get("url", "")
    src = story.get("source") or "Source"
    link = (
        f'<div style="font-size:13px;line-height:20px;color:{INK3};">Source &nbsp;'
        f'<a href="{e(url)}" style="color:{ACCENT};text-decoration:underline;">{e(src)}</a>'
        f"</div>"
        if url
        else ""
    )

    return (
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:10px;'
        f'padding:16px 18px;margin:0 0 10px;">'
        f'<div style="font-size:17px;line-height:24px;font-weight:650;color:{INK};'
        f'margin:0 0 8px;">{e(story.get("headline", "Untitled"))}</div>'
        f"{chips_row}"
        f'<div style="font-size:15px;line-height:23px;color:{INK2};margin:0 0 12px;">'
        f'{e(story.get("body", ""))}</div>'
        f"{link}"
        "</div>"
    )


def build(day):
    by_id = {s.get("id"): s for s in day.get("sections", [])}
    blocks = []
    total = 0

    for i, (sid, default_name) in enumerate(SECTION_ORDER, start=1):
        sec = by_id.get(sid, {})
        name = sec.get("name") or default_name
        stories = sec.get("stories") or []
        total += len(stories)

        inner = (
            "".join(story_block(s) for s in stories)
            if stories
            else f'<div style="font-size:15px;line-height:23px;color:{INK3};'
            f'font-style:italic;margin:0 0 10px;">Nothing significant in the past 24 hours.</div>'
        )

        blocks.append(
            f'<div style="margin:0 0 34px;">'
            f'<div style="border-bottom:2px solid {ACCENT};padding:0 0 8px;margin:0 0 16px;">'
            f'<span style="display:inline-block;font-size:12px;color:{ACCENT};'
            f'background:{ACCENT_SF};border-radius:4px;padding:2px 7px;font-weight:650;'
            f'margin-right:9px;">{i}</span>'
            f'<span style="font-size:17px;font-weight:700;color:{INK};">{e(name)}</span>'
            f"</div>{inner}</div>"
        )

    site_link = (
        f'<div style="margin:14px 0 0;font-size:14px;">'
        f'<a href="{e(SITE_URL)}" style="color:{ACCENT};text-decoration:underline;">'
        f"Read this edition on the web &rarr;</a></div>"
        if SITE_URL
        else ""
    )

    window = (
        f'<div style="font-size:14px;line-height:21px;color:{INK3};margin:6px 0 0;">'
        f'{e(day["window"])}</div>'
        if day.get("window")
        else ""
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
</head>
<body style="margin:0;padding:0;background:{BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:{BG};margin:0;padding:0;">
<tr><td align="center" style="padding:28px 14px 48px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0"
       style="width:100%;max-width:640px;text-align:left;font-family:{FONT};">
<tr><td>

<div style="border-bottom:1px solid {BORDER};padding:0 0 20px;margin:0 0 30px;">
<div style="font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
            color:{ACCENT};font-weight:650;margin:0 0 8px;">Daily Edition</div>
<div style="font-size:30px;line-height:34px;font-weight:700;color:{INK};
            letter-spacing:-0.5px;margin:0 0 10px;">Drug News Roundup</div>
<div style="font-size:15px;line-height:22px;color:{INK2};">
{e(pretty_date(day["date"]))} &middot; {total} {"story" if total == 1 else "stories"}</div>
{window}
{site_link}
</div>

{"".join(blocks)}

<div style="border-top:1px solid {BORDER};padding:16px 0 0;font-size:13px;
            line-height:20px;color:{INK3};">
<div style="margin:0 0 5px;">Compiled automatically each morning at 6:00 AM Central.
Every story is checked against a running log, so nothing repeats between editions.</div>
<div>Links go to the original reporting; quantities and arrest counts are as stated by the source.</div>
</div>

</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        raise SystemExit("Usage: make_email.py YYYY-MM-DD [--out FILE]")

    day_iso = args[0]
    out = None
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])

    path = DATA / f"{day_iso}.json"
    if not path.exists():
        raise SystemExit(f"No edition at {path}")

    with path.open(encoding="utf-8") as fh:
        day = json.load(fh)
    day.setdefault("date", day_iso)

    rendered = build(day)

    if out:
        out.write_text(rendered, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        sys.stdout.write(rendered)


if __name__ == "__main__":
    main()
