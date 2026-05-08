# Big Whey — Competitor Price Tracker

Daily scraper for Nutrition X Big Whey vs 10 UK competitors.
Tracks price-per-serving, flags price changes, description changes,
and generates a self-contained HTML report.

---

## Project structure

```
whey_tracker/
├── main.py               ← Entry point & CLI
├── config.py             ← All URLs, serving counts, settings
├── scraper.py            ← Fetch + parse + change detection
├── database.py           ← SQLite read/write
├── reporter.py           ← HTML report & terminal summary
├── alerts.py             ← Email alerts
├── scrapers/
│   └── parsers.py        ← Per-brand HTML parsers
├── data/
│   └── prices.db         ← SQLite database (auto-created)
├── reports/
│   ├── latest.html       ← Most recent report (overwritten daily)
│   └── report_YYYY-MM-DD.html
├── logs/
│   └── scraper.log
├── requirements.txt
└── .github/
    └── workflows/
        └── daily_scrape.yml   ← GitHub Actions schedule
```

---

## Quick start (local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run once now (scrapes all products + generates report)
python main.py

# 3. Open the report
open reports/latest.html

# 4. Start the daily scheduler (blocks — use screen/tmux or systemd)
python main.py --schedule
```

---

## Automated daily runs (GitHub Actions — free)

1. Push this folder to a **private** GitHub repository.
2. The workflow in `.github/workflows/daily_scrape.yml` runs at 08:00 UTC daily.
3. Reports are saved as downloadable **Artifacts** in the Actions tab.
4. The database persists between runs via GitHub Actions Cache.

### Optional: email alerts
1. Add your SMTP password as a GitHub Secret named `SMTP_PASSWORD`.
2. Set `email_enabled: True` in `config.py` and fill in your email details.

---

## CLI commands

```bash
# Scrape all products + generate report (default)
python main.py

# Run on a schedule (blocks — for VPS/server use)
python main.py --schedule

# Generate report from existing DB without scraping
python main.py --report-only

# Scrape only one brand
python main.py --brand Bulk
python main.py --brand "Optimum Nutrition"

# Print 7-day price history summary
python main.py --history
```

---

## Updating serving counts

Open `config.py` and update the `servings` field for each product,
then set `"confirmed": True`. These are used to calculate price-per-serving.

**Your products** — check the label on your 900g and 1.8kg tubs.
**Competitors** — check label or product page.

Current estimates (marked `confirmed: False`):
- Bulk 2.5kg: calculated as 2500 ÷ 30g
- SIS 1kg: price not confirmed in GBP — verify at scienceinsport.com
- Soccer Supplement: new formula (30g scoop / 22g protein) — confirm servings

---

## Adding a new competitor

1. Add an entry to `COMPETITOR_PRODUCTS` in `config.py`.
2. Add a parser function in `scrapers/parsers.py`.
3. Register it in `PARSER_MAP` at the bottom of `parsers.py`.
4. Run `python main.py --brand "New Brand"` to test.

---

## Price change sensitivity

Default: alert if price changes by ≥ 2%.
Adjust `price_change_alert_pct` in `config.py`.

---

## Notes on anti-bot measures

Some sites (Myprotein, Bulk) use JavaScript rendering or CAPTCHAs on
repeated visits. If a brand consistently returns `price not found`:

1. Add a `Referer` header to the session in `scraper.py`.
2. Increase `request_delay_seconds` in `config.py`.
3. For heavy JS sites, swap `requests` for `playwright` (pip install playwright).
   A Playwright-based fetch function is provided as a comment in `scraper.py`.

---

## Data stays local

All data is stored in `data/prices.db` (SQLite).
No data is sent anywhere unless you configure email alerts.
