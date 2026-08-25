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

import tally

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

SITE_URL = "https://therealwizofoz.github.io/drug-news-roundup"

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


def tally_rows(bucket):
    out = ""
    for place, drugs, total in tally.rows(bucket):
        items = sorted(drugs.items(), key=lambda kv: -kv[1])
        brk = " &middot; ".join(f"{e(d)} {tally.fmt_kg(kg)}" for d, kg in items)
        out += (
            f'<tr>'
            f'<td style="padding:9px 10px 9px 0;border-bottom:1px solid {BORDER};'
            f'font-size:14px;font-weight:650;color:{INK};vertical-align:top;">{e(place)}'
            f'<div style="font-size:12px;font-weight:400;color:{INK3};'
            f'margin-top:2px;">{brk}</div></td>'
            f'<td style="padding:9px 0;border-bottom:1px solid {BORDER};'
            f'font-size:14px;font-weight:650;color:{ACCENT};text-align:right;'
            f'white-space:nowrap;vertical-align:top;">{tally.fmt_kg(total)}</td>'
            f"</tr>"
        )
    return out


def prior_years_block(days, upto_date):
    """
    Closed years as one compact row each, plus an all-time line.
    Email clients do not support <details>, so unlike the website this
    stays collapsed to totals — the site carries the full breakdown.
    """
    years = tally.closed_years(days, upto_date)
    if not years:
        return ""

    rows = ""
    for year in years:
        us, intl, _, n, total = tally.year_summary(days, year)
        if not tally.has_data(us, intl):
            continue
        places = len(us) + len(intl)
        rows += (
            f"<tr>"
            f'<td style="padding:9px 10px 9px 0;border-bottom:1px solid {BORDER};'
            f'font-size:14px;font-weight:650;color:{INK};">{e(year)}'
            f'<div style="font-size:12px;font-weight:400;color:{INK3};margin-top:2px;">'
            f'{n} {"edition" if n == 1 else "editions"} &middot; '
            f'{places} {"place" if places == 1 else "places"}</div></td>'
            f'<td style="padding:9px 0;border-bottom:1px solid {BORDER};'
            f'font-size:14px;font-weight:650;color:{ACCENT};text-align:right;'
            f'white-space:nowrap;">{tally.fmt_kg(total)}</td>'
            f"</tr>"
        )

    if not rows:
        return ""

    all_us, all_intl, _, _ = tally.collect(days, upto_date, restrict_year=False)
    all_time = tally.fmt_kg(tally.grand_total(all_us, all_intl))

    return (
        f'<div style="font-size:11px;letter-spacing:1.3px;text-transform:uppercase;'
        f'color:{INK3};font-weight:650;margin:24px 0 6px;">Previous years</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        f' border="0" style="width:100%;border-collapse:collapse;">{rows}</table>'
        f'<div style="margin:12px 0 0;padding-top:10px;border-top:2px solid {BORDER};'
        f'font-size:14px;color:{INK};">'
        f'<span style="font-weight:650;">All time</span>'
        f'<span style="float:right;font-weight:650;color:{ACCENT};">{all_time}</span>'
        f'</div>'
    )


def tally_block(days, upto_date):
    us, intl, drugs, n = tally.collect(days, upto_date)
    if not tally.has_data(us, intl):
        return ""

    total = tally.grand_total(us, intl)
    places = len(us) + len(intl)
    year = tally.year_of(upto_date)

    groups = ""
    for label, bucket in (("United States", us), ("International", intl)):
        if not bucket:
            continue
        groups += (
            f'<div style="font-size:11px;letter-spacing:1.3px;text-transform:uppercase;'
            f'color:{INK3};font-weight:650;margin:20px 0 6px;">{label}</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
            f' border="0" style="width:100%;border-collapse:collapse;">'
            f"{tally_rows(bucket)}</table>"
        )

    groups += prior_years_block(days, upto_date)

    return f"""<div style="margin:0 0 34px;">
<div style="border-bottom:2px solid {INK3};padding:0 0 8px;margin:0 0 14px;">
<span style="font-size:17px;font-weight:700;color:{INK};">{e(year)} Running Tally</span>
</div>
<div style="font-size:13px;line-height:20px;color:{INK3};margin:0 0 14px;">
Total weight intercepted across every story covered so far this year, through
{e(pretty_date(upto_date))}. Counts seizures only — sentencings and indictments
are not double-counted — and resets to zero each 1 January. Earlier years are
kept below.</div>
<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:10px;
            padding:14px 18px;">
<span style="font-size:28px;font-weight:700;color:{ACCENT};">{tally.fmt_kg(total)}</span>
<span style="font-size:13px;color:{INK3};margin-left:10px;">{n} {"edition" if n == 1 else "editions"}
&middot; {places} {"place" if places == 1 else "places"}
&middot; {len(drugs)} {"substance" if len(drugs) == 1 else "substances"}</span>
</div>
{groups}
</div>"""


def build(day, all_days=()):
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
            color:{ACCENT};font-weight:650;margin:0 0 8px;">Edition {tally.fmt_edition(tally.edition_number(all_days, day["date"]))}</div>
<div style="font-size:30px;line-height:34px;font-weight:700;color:{INK};
            letter-spacing:-0.5px;margin:0 0 10px;">Drug News Roundup</div>
<div style="font-size:15px;line-height:22px;color:{INK2};">
{e(pretty_date(day["date"]))} &middot; {total} {"story" if total == 1 else "stories"}</div>
{window}
{site_link}
</div>

{"".join(blocks)}

{tally_block(all_days, day["date"])}

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

    # Every edition, so the tally can sum the year to date.
    all_days = []
    for f in sorted(DATA.glob("*.json")):
        with f.open(encoding="utf-8") as fh:
            d = json.load(fh)
        d.setdefault("date", f.stem)
        all_days.append(d)

    rendered = build(day, all_days)

    if out:
        out.write_text(rendered, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        sys.stdout.write(rendered)


if __name__ == "__main__":
    main()
