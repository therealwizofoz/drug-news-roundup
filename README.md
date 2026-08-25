# O'Drug News Roundup — archive site

A static site that mirrors the daily O'Drug News Roundup email. One JSON file per
day is the source of truth; `build.py` turns those files into HTML. No frameworks,
no build dependencies beyond Python 3.

```
data/2026-08-22.json     one file per edition  ← the only thing you ever edit
build.py                 regenerates all HTML from data/
make_email.py            renders one edition as the HTML email
tally.py                 year-to-date seizure totals, shared by both
publish.sh               build + git commit + push
assets/style.css         the whole stylesheet
index.html               generated — latest edition
archive/index.html       generated — list of all editions
archive/2026-08-22.html  generated — one page per edition
```

Everything outside `data/` and `assets/` is generated. Delete all the HTML and
run `python3 build.py` and you get it back byte for byte.

---

## The daily email

The 6 AM email is generated from the same JSON as the website, so the two can
never disagree:

```bash
python3 make_email.py 2026-08-22 --out email.html
```

That writes an email-safe HTML file — every style inline, one centred column,
no external CSS, JavaScript or remote images — which the scheduled task hands to
Mail via AppleScript's `html content` property. Apple Mail on macOS and iOS both
render it as-is. `email.html` is regenerated every morning and is not tracked in
git.

The design is deliberately light-only. Email clients handle a fixed light
palette far more predictably than a themed one, so unlike the website the email
does not follow your system dark mode.

**Once GitHub Pages is live**, open `make_email.py` and set:

```python
SITE_URL = "https://<your-username>.github.io/drug-news-roundup"
```

Each email then carries a "Read this edition on the web →" link under the
masthead. Leave it empty and the link is simply omitted.

---

## Hosting: GitHub Pages

The site is plain committed HTML — `publish.sh` runs `build.py` before every
commit, so what lands in the repo is what gets served. GitHub Pages needs no
build step and no Actions workflow: it deploys the branch as-is.

### Public or private?

**GitHub Pages will not publish from a private repository on the free plan.**
It needs GitHub Pro ($4/month). Nothing on this site is sensitive — every story
links to already-published reporting — so the steps below use `--public`. If you
have Pro and want the repo private, swap `--public` for `--private`; everything
else is identical, though the *site* stays publicly reachable either way. Pages
has no viewer restriction at any tier.

### 1. Install the GitHub CLI

```bash
brew install gh
gh auth login
```

Choose **GitHub.com → HTTPS → Login with a web browser**, paste the one-time
code, and answer **yes** to "authenticate Git operations with your GitHub
credentials". That stores a credential in the macOS keychain, which is what lets
the 6 AM task push unattended.

### 2. Create the repo and push

```bash
cd ~/Documents/DrugNewsRoundup/site
gh repo create drug-news-roundup --public --source=. --remote=origin --push
```

This creates the repository, wires up `origin`, and pushes `main` in one step.

### 3. Turn on Pages

```bash
gh api -X POST repos/:owner/drug-news-roundup/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```

Or in the browser: **Settings → Pages → Build and deployment → Source:
Deploy from a branch → Branch: `main` → Folder: `/ (root)` → Save**.

### 4. Get your URL

```bash
gh api repos/:owner/drug-news-roundup/pages --jq .html_url
```

Typically `https://<your-username>.github.io/drug-news-roundup/`. The first
deploy takes a minute or two; later ones are usually under 30 seconds.

### 5. Put the URL in the email

Open `make_email.py` and set:

```python
SITE_URL = "https://<your-username>.github.io/drug-news-roundup"
```

Each morning's email then carries a "Read this edition on the web →" link under
the masthead.

### 6. Confirm the unattended push works

```bash
./publish.sh "test push"
```

If it completes without prompting for a password, tomorrow's 6 AM task will
publish on its own. If it does prompt, run `gh auth setup-git` and retry.

---

## The daily update

Once the repo exists, the 6 AM roundup task does this on its own after the email
goes out:

1. Writes `data/YYYY-MM-DD.json` for the new edition.
2. Runs `./publish.sh`, which rebuilds every page and pushes to `main`.
3. GitHub Pages redeploys the branch, usually within 30 seconds.

For the push to work unattended, the credential has to be stored in the macOS
keychain — that is what `gh auth login` did. To confirm it works without a
prompt:

```bash
cd ~/Documents/DrugNewsRoundup/site && ./publish.sh "test push"
```

If that succeeds silently, the scheduled task will too. If it asks for a
username and password every time, run `gh auth setup-git` and push once by hand.

### Adding or fixing an edition by hand

Edit or add a file in `data/`, then:

```bash
./publish.sh "Fix Aug 22 seizure figure"
```

The JSON shape:

```json
{
  "date": "2026-08-22",
  "window": "Covering the past 24 hours (Aug 21–22).",
  "sections": [
    {
      "id": "federal",
      "name": "National / Federal (US)",
      "stories": [
        {
          "headline": "Short headline",
          "body": "One to three sentences.",
          "quantity": "4.5 t cocaine",
          "location": "Putumayo, Colombia",
          "arrests": "12 arrested",
          "source": "DEA",
          "url": "https://example.org/story",
          "seizures": [
            {"drug": "cocaine", "kg": 4500, "place": "Colombia"}
          ]
        }
      ]
    }
  ]
}
```

`headline`, `body` and `url` are required. `quantity`, `location`, `arrests` and
`source` are optional and render as small chips under the headline — omit any
that the reporting does not give.

`seizures` is the structured, summable version of `quantity`, and feeds the
running tally. See below.

Section `id` must be one of `federal`, `local`, `south-america`, `world`,
`ongoing`. They always render in that order regardless of how the file lists
them, and a section with no stories shows "Nothing significant in the past 24
hours" rather than disappearing.

---

## The running tally

Every edition page and every email ends with a year-to-date tally of weight
intercepted, broken out by US state and by country. `tally.py` computes it;
`build.py` and `make_email.py` both render it.

It is driven entirely by the `seizures` field on each story:

```json
"seizures": [
  {"drug": "cocaine", "kg": 1011.52, "place": "Ecuador"},
  {"drug": "fentanyl", "kg": 4, "place": "New York"}
]
```

Four rules keep the numbers honest:

1. **Always kilograms.** Convert before writing the JSON — 1 lb = 0.45359237 kg,
   1 tonne = 1000 kg. The display rescales to tonnes or grams on its own.
2. **`place` is a US state name or a country name.** `tally.py` holds the list
   of US states and routes each row into the right table. A place it does not
   recognise as a state is treated as a country, so spelling matters —
   "New York", not "NY"; "Colombia", not "Putumayo".
3. **Seizures only.** Sentencings, indictments and court outcomes describe
   drugs seized in the past, often years earlier and already counted. They get
   no `seizures` entry.
4. **Omit it when no weight is given.** Dose and pill counts are not reliably
   convertible to weight, so a story reporting "8.5 million doses" contributes
   nothing to the tally. Better a slightly low number than a fabricated one.

An edition's tally covers its own calendar year, up to and including its own
date. So each archived page shows the total as it stood that morning, the front
page shows the current total, and everything resets to zero on 1 January
automatically — there is nothing to clear by hand.

### Previous years

Nothing is lost at the rollover. Once an edition falls in a later year than
some of the data, a **Previous years** block appears under the current tally:
one collapsible row per finished year showing its final total, editions and
place count, expanding to that year's full state-and-country breakdown. An
**All time** figure closes the section.

This is derived, not stored — the tally is recomputed from `data/*.json` on
every build, so a correction to an old edition's JSON updates that year's
historical total the next time the site is built. Archived pages stay honest
too: a page dated in 2027 lists 2026 as a previous year, while the 2026 pages
show only what was known then.

The email carries the same block collapsed to one total per year, since email
clients do not support `<details>`. The full breakdown lives on the site.

---

## Notes

- `.nojekyll` is generated on every build. It stops GitHub Pages from running
  Jekyll over the output, which would otherwise ignore any file or folder whose
  name begins with an underscore.
- The site is built on your Mac by `publish.sh`, not in CI, so the committed
  HTML is always what gets served. Never hand-edit an HTML file — the next
  build overwrites it. Edit the JSON in `data/` instead.
- The stylesheet follows the reader's system light/dark setting. There is no
  theme toggle and no JavaScript anywhere on the site.
- Story text and URLs are HTML-escaped at build time, so quotes, ampersands and
  accented characters in Spanish and Portuguese headlines are safe.
