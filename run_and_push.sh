#!/bin/bash
cd ~/Downloads/whey_tracker

# Run the scraper
python3 main.py

# Copy report to docs for GitHub Pages
cp reports/latest.html docs/index.html

# Commit and push
git add data/prices.db reports/latest.html docs/index.html logs/scraper.log
git diff --cached --quiet || git commit -m "chore: daily price snapshot $(date +'%Y-%m-%d')"
git pull --rebase origin main
git push
