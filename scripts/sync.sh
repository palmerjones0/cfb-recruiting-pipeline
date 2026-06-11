#!/bin/bash
# sync.sh — orchestrates daily/weekly data update
# Daily (4:15am ET): fetch CFBD + build
# Weekly (Sunday 3am ET): also scrape 247Sports offers
# Usage: ./scripts/sync.sh [--weekly]

set -e
cd "$(dirname "$0")/.."

MODE="daily"
if [[ "$1" == "--weekly" ]]; then
  MODE="weekly"
fi

echo "[$(date)] Starting CFB pipeline sync ($MODE)"

# Always: fetch latest CFBD recruit data
python3 scripts/fetch_recruits.py

# Weekly: scrape 247Sports offer pages
if [[ "$MODE" == "weekly" ]]; then
  echo "[$(date)] Running 247Sports offer scrape..."
  python3 scripts/scrape_offers.py
fi

# Always: rebuild public/ output files
python3 scripts/build_json.py

# Commit and push if anything changed
if git diff --quiet public/; then
  echo "[$(date)] No changes in public/ — skipping commit"
else
  git add public/
  git commit -m "data: auto-update $(date '+%Y-%m-%d %H:%M') ET"
  git push
  echo "[$(date)] Pushed updated data"
fi

echo "[$(date)] Sync complete"
