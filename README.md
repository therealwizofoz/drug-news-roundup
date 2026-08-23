# Drug News Roundup — archive site

A static site that mirrors the daily Drug News Roundup email. One JSON file per
day is the source of truth; `build.py` turns those files into HTML. No frameworks,
no build dependencies beyond Python 3.

```
data/2026-08-22.json     one file per edition  ← the only thing you ever edit
build.py                 regenerates all HTML from data/
publish.sh               build + git commit + push
.gitlab-ci.yml           GitLab Pages deployment
assets/style.css         the whole stylesheet
index.html               generated — latest edition
archive/index.html       generated — list of all editions
archive/2026-08-22.html  generated — one page per edition
```

Everything outside `data/` and `assets/` is generated. Delete all the HTML and
run `python3 build.py` and you get it back byte for byte.

---

## Hosting: GitLab Pages

The site is deployed by GitLab CI. `.gitlab-ci.yml` runs `build.py` on every push
to `main`, assembles the output into a `public/` directory (the only directory
GitLab Pages will serve), and publishes it.

Because CI rebuilds from `data/`, the JSON files stay the single source of truth
— hand-edited HTML can never drift out of sync.

### One-time gotcha: identity verification

GitLab.com requires identity verification — a credit card or phone number —
before a free account can use shared CI runners. The card is not charged; a
small authorization is placed and reversed. Without this, the pipeline will sit
queued forever and the site will never build. Verify at
**Settings → Account** if GitLab prompts you.

Free accounts get 400 compute minutes per month. This site builds in well under
a minute, so a daily push uses roughly 30 of them.

### 1. Create the project and push

```bash
# Set the remote (replace <username> with your GitLab username)
cd ~/Documents/DrugNewsRoundup/site
git remote add origin https://gitlab.com/<username>/drug-news-roundup.git
git push -u origin main
```

Create the project first at <https://gitlab.com/projects/new#blank_project> —
name it `drug-news-roundup`, set **Visibility Level** to **Private**, and
uncheck **Initialize repository with a README** so the push is not rejected.

GitLab will prompt for a username and password on first push. Use a **personal
access token** as the password, not your account password: **Settings → Access
tokens → Add new token**, scope `write_repository`, then let the macOS keychain
store it so the 6 AM task can push unattended.

### 2. Watch the first pipeline

**Build → Pipelines** in the project. The `pages` job should go green in under
a minute. If it stays *pending*, that is the identity verification issue above.

### 3. Find your URL

**Deploy → Pages**. New projects get a unique domain, so the URL looks like
`https://drug-news-roundup-a1b2c3.gitlab.io` rather than a predictable path.

### 4. Make the site private (optional)

By default the site is public even though the repo is private. To restrict it:

**Settings → General → Visibility, project features, permissions**, find
**Pages**, and set access to **Only project members**. Viewers then have to be
signed in to a GitLab account you have added to the project. Changes take about
a minute to propagate through the cache.

This is available on the free tier, and unlike GitHub Pages it needs no external
auth service.

## The daily update

Once the repo exists, the 6 AM roundup task does this on its own after the email
goes out:

1. Writes `data/YYYY-MM-DD.json` for the new edition.
2. Runs `./publish.sh`, which rebuilds every page and pushes to `main`.
3. GitLab CI runs the `pages` job and the site updates within a minute or two.

For the push to work unattended, the personal access token has to be stored in
the macOS keychain. To confirm it works without a prompt:

```bash
cd ~/Documents/DrugNewsRoundup/site && ./publish.sh "test push"
```

If that succeeds silently, the scheduled task will too. If it asks for a
username and password every time, tell git to use the keychain:

```bash
git config --global credential.helper osxkeychain
```

then push once by hand, entering your GitLab username and the personal access
token as the password.

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
          "url": "https://example.org/story"
        }
      ]
    }
  ]
}
```

`headline`, `body` and `url` are required. `quantity`, `location`, `arrests` and
`source` are optional and render as small chips under the headline — omit any
that the reporting does not give.

Section `id` must be one of `federal`, `local`, `south-america`, `world`,
`ongoing`. They always render in that order regardless of how the file lists
them, and a section with no stories shows "Nothing significant in the past 24
hours" rather than disappearing.

---

## Notes

- `.nojekyll` is generated on every build. GitLab Pages ignores it — it only
  matters on GitHub Pages — but it is harmless and keeps the option open.
- CI builds on `python:3.12-alpine`; your Mac builds on the system Python 3.9.
  `build.py` uses nothing version-specific, so both produce identical output.
- The stylesheet follows the reader's system light/dark setting. There is no
  theme toggle and no JavaScript anywhere on the site.
- Story text and URLs are HTML-escaped at build time, so quotes, ampersands and
  accented characters in Spanish and Portuguese headlines are safe.
