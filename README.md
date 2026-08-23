# Drug News Roundup — archive site

A static site that mirrors the daily Drug News Roundup email. One JSON file per
day is the source of truth; `build.py` turns those files into HTML. No frameworks,
no build dependencies beyond Python 3.

```
data/2026-08-22.json     one file per edition  ← the only thing you ever edit
build.py                 regenerates all HTML from data/
publish.sh               build + git commit + push
assets/style.css         the whole stylesheet
index.html               generated — latest edition
archive/index.html       generated — list of all editions
archive/2026-08-22.html  generated — one page per edition
```

Everything outside `data/` and `assets/` is generated. Delete all the HTML and
run `python3 build.py` and you get it back byte for byte.

---

## Before you start: private repos and GitHub Pages

**GitHub Pages will not publish from a private repository on the free plan.**
It needs GitHub Pro ($4/month) for personal accounts, or a Team/Enterprise plan
for organizations. On a free account the repo can be private, but the Pages
build will be rejected.

You have three ways forward:

| Option | Repo | Site | Cost |
| --- | --- | --- | --- |
| **A.** Upgrade to GitHub Pro | Private | Public URL | $4/mo |
| **B.** Public repo | Public | Public URL | Free |
| **C.** Private repo + Cloudflare Pages | Private | Public URL (protectable) | Free |

Nothing in this site is sensitive — every story links to already-published
reporting — so **B** is the least friction if you only made it private out of
habit. **C** is the one to pick if you want the repo private *and* the site
access-controlled: Cloudflare Pages builds from a private GitHub repo on the
free tier, and Cloudflare Access can put an email-code login in front of it.

Instructions for all three are below. Start with the common setup.

---

## Common setup: create the repo and push

Run these from the site folder on your Mac
(`~/Documents/DrugNewsRoundup/site`).

### 1. Install the GitHub CLI (once)

```bash
brew install gh
gh auth login
```

Choose **GitHub.com** → **HTTPS** → **Login with a web browser**, and paste the
one-time code it shows you. When it asks whether to authenticate Git operations
with your GitHub credentials, say **yes** — this stores a credential in the
macOS Keychain, which is what lets the 6 AM task push without a prompt.

If you would rather not use `gh`, create the repo manually at
<https://github.com/new> and skip to step 3.

### 2. Create the repository

```bash
cd ~/Documents/DrugNewsRoundup/site
git init -b main
gh repo create drug-news-roundup --private --source=. --remote=origin
```

Swap `--private` for `--public` if you are going with option B.

### 3. First commit and push

```bash
git add -A
git commit -m "Initial site"
git push -u origin main
```

If you created the repo by hand rather than with `gh`, add the remote first:

```bash
git remote add origin https://github.com/<your-username>/drug-news-roundup.git
git push -u origin main
```

### 4. Make the publish script executable

```bash
chmod +x publish.sh
```

---

## Option A — private repo on GitHub Pages (requires GitHub Pro)

1. Upgrade at <https://github.com/settings/billing> → **Plans and usage** →
   **Upgrade to Pro**.
2. In the repo, go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to *Deploy from a branch*,
   **Branch** to `main`, folder `/ (root)`. Save.
4. Wait a minute or two. Your site appears at
   `https://<your-username>.github.io/drug-news-roundup/`.

The site itself is public even though the repo is private — Pages has no way to
restrict viewers on Pro. If you need the *site* private too, use option C.

## Option B — public repo on GitHub Pages (free)

Identical to option A, minus the upgrade. If you already created the repo as
private, flip it:

```bash
gh repo edit --visibility public --accept-visibility-change-consequences
```

Then **Settings → Pages → Deploy from a branch → main → / (root)**.

## Option C — private repo, hosted on Cloudflare Pages (free)

1. Sign in at <https://dash.cloudflare.com> and go to
   **Workers & Pages → Create → Pages → Connect to Git**.
2. Authorize Cloudflare for GitHub and pick `drug-news-roundup`. Granting access
   to just this one repository is enough.
3. Build settings:
   - **Framework preset:** None
   - **Build command:** *(leave empty)*
   - **Build output directory:** `/`
4. Deploy. You get a `https://drug-news-roundup.pages.dev` URL, and every push
   to `main` redeploys automatically.
5. *(Optional, to keep the site itself private)* **Zero Trust → Access →
   Applications → Add an application → Self-hosted**, point it at your
   `.pages.dev` hostname, and add a policy allowing only
   `ryan.oconnor.kc@icloud.com`. Visitors then get a one-time email code before
   the site loads.

---

## The daily update

Once the repo exists, the 6 AM roundup task does this on its own after the email
goes out:

1. Writes `data/YYYY-MM-DD.json` for the new edition.
2. Runs `./publish.sh`, which rebuilds every page and pushes to `main`.
3. GitHub Pages or Cloudflare redeploys within a minute or two.

For the push to work unattended, the credential has to be stored — that is what
`gh auth login` did in step 1. To confirm it works without a prompt:

```bash
cd ~/Documents/DrugNewsRoundup/site && ./publish.sh "test push"
```

If that succeeds silently, the scheduled task will too. If it asks for a
username and password, run `gh auth setup-git` and try again.

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

- `.nojekyll` is generated on every build. It stops GitHub Pages from running
  Jekyll over the output, which would otherwise ignore any file or folder
  beginning with an underscore.
- The stylesheet follows the reader's system light/dark setting. There is no
  theme toggle and no JavaScript anywhere on the site.
- Story text and URLs are HTML-escaped at build time, so quotes, ampersands and
  accented characters in Spanish and Portuguese headlines are safe.
