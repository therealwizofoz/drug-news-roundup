#!/usr/bin/env python3
"""
Year-to-date seizure tally, shared by build.py and make_email.py.

Every story may carry a "seizures" list of structured, summable records:

    "seizures": [
      {"drug": "cocaine", "kg": 1011.52, "place": "Ecuador"},
      {"drug": "fentanyl", "kg": 4, "place": "New York"}
    ]

Rules:
  - Weights are always kilograms. Convert before writing the JSON.
  - "place" is a US state name for US seizures, otherwise a country name.
  - Record only drugs actually intercepted. Sentencings, indictments and
    court outcomes describe past seizures and must NOT be counted again.
  - Omit "seizures" entirely when no weight is reported (dose or pill
    counts alone are not convertible and are deliberately not tallied).

The tally for a given edition covers that edition's calendar year, up to
and including its own date — so it resets to zero on 1 January.
"""

from collections import defaultdict

# Conversions, for reference when writing JSON by hand:
#   1 lb = 0.45359237 kg    1 tonne = 1000 kg    1 g = 0.001 kg
LB_TO_KG = 0.45359237

US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
    "District of Columbia", "Puerto Rico", "Guam", "U.S. Virgin Islands",
}


def year_of(iso):
    return iso.split("-")[0]


def edition_number(days, date_iso):
    """
    Sequential edition number, oldest edition = 1, counting up one per
    published day. Continuous across years — it is an issue number, not a
    year-to-date counter, so it never resets.
    """
    return 1 + sum(
        1 for d in days if d.get("date") and d["date"] < date_iso
    )


def fmt_edition(n):
    """
    O'001, O'002 … O'999, then O'1000 onward without padding.

    The O' prefix is a quiet nod to O'Connor — the masthead stays plain
    "Drug News Roundup", and this is the only place the name shows up.
    """
    return f"O'{n:03d}"


def collect(days, upto_date, restrict_year=True):
    """
    Sum every seizure from editions dated on or before `upto_date`.

    With restrict_year=True (the default) only editions in the same
    calendar year as `upto_date` count — that is the year-to-date tally,
    which resets on 1 January. With restrict_year=False every edition up
    to that date counts, giving the all-time total.

    Returns (us, intl, drugs, n_editions) where us/intl map
    place -> {drug: kg} and `drugs` is the sorted set of drug names seen.
    """
    year = year_of(upto_date) if restrict_year else None
    us = defaultdict(lambda: defaultdict(float))
    intl = defaultdict(lambda: defaultdict(float))
    drugs = set()
    n = 0

    for day in days:
        d = day.get("date", "")
        if not d or d > upto_date:
            continue
        if year is not None and year_of(d) != year:
            continue
        n += 1
        for section in day.get("sections", []):
            for story in section.get("stories") or []:
                for s in story.get("seizures") or []:
                    place = (s.get("place") or "").strip()
                    drug = (s.get("drug") or "").strip().lower()
                    try:
                        kg = float(s.get("kg") or 0)
                    except (TypeError, ValueError):
                        continue
                    if not place or not drug or kg <= 0:
                        continue
                    bucket = us if place in US_STATES else intl
                    bucket[place][drug] += kg
                    drugs.add(drug)

    return (
        {p: dict(v) for p, v in us.items()},
        {p: dict(v) for p, v in intl.items()},
        sorted(drugs),
        n,
    )


def closed_years(days, upto_date):
    """
    Calendar years strictly before `upto_date`'s year that have at least
    one edition, newest first. These are the finished years whose totals
    are kept on the page after the running tally rolls over.
    """
    current = year_of(upto_date)
    years = {
        year_of(day.get("date", ""))
        for day in days
        if day.get("date") and year_of(day["date"]) < current
    }
    return sorted(years, reverse=True)


def year_summary(days, year):
    """(us, intl, drugs, n_editions, total_kg) for one complete year."""
    us, intl, drugs, n = collect(days, f"{year}-12-31")
    return us, intl, drugs, n, grand_total(us, intl)


def fmt_kg(kg):
    """Human-scaled weight: tonnes above 1000 kg, grams below 1 kg."""
    if kg >= 1000:
        t = kg / 1000
        return f"{t:,.1f} t" if t < 100 else f"{t:,.0f} t"
    if kg >= 1:
        return f"{kg:,.0f} kg" if kg >= 10 else f"{kg:,.1f} kg".replace(".0 kg", " kg")
    return f"{kg * 1000:,.0f} g"


def rows(bucket):
    """[(place, {drug: kg}, total_kg)] sorted by total descending."""
    out = [(place, drugs, sum(drugs.values())) for place, drugs in bucket.items()]
    out.sort(key=lambda r: (-r[2], r[0]))
    return out


def grand_total(us, intl):
    return sum(sum(d.values()) for d in us.values()) + sum(
        sum(d.values()) for d in intl.values()
    )


def has_data(us, intl):
    return bool(us or intl)
