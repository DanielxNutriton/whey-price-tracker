#!/bin/bash
cd ~/Downloads/whey_tracker

# Install any missing dependencies
pip3 install -q requests beautifulsoup4 lxml schedule playwright

# Run the scraper
python3 main.py

# Copy report to docs for GitHub Pages
cp reports/latest.html docs/index.html

# Always force a change with timestamp
echo "$(date -u +'%Y-%m-%d %H:%M UTC')" > last_run.txt

# Stage everything
git add -A

# Commit
git commit -m "chore: daily price snapshot $(date +'%Y-%m-%d')" || true

# Push — force sync if needed
git push || (git fetch origin && git reset --soft origin/main && git push)
