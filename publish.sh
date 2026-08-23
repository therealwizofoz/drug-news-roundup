#!/bin/bash
# Rebuild the site from data/*.json and push it to GitHub.
# Called by the daily 6 AM roundup task, and safe to run by hand.
#
#   ./publish.sh              commit message defaults to today's date
#   ./publish.sh "message"    custom commit message

set -euo pipefail
cd "$(dirname "$0")"

MSG="${1:-Roundup $(date +%Y-%m-%d)}"

python3 build.py

# Nothing to do if the build produced no changes.
if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
  echo "No changes to publish."
  exit 0
fi

git add -A
git commit -m "$MSG"
git push origin main

echo "Published: $MSG"
