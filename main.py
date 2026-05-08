"""
main.py — Entry point for the Big Whey price tracker.

Usage:
    python main.py                  # Run scrape now, generate report
    python main.py --schedule       # Start daily scheduler (runs forever)
    python main.py --report-only    # Generate report from existing DB data
    python main.py --brand Bulk     # Scrape a single brand only
    python main.py --history        # Print 7-day price history summary
"""

import argparse
import logging
import sys
import time
from datetime import datetime

import schedule

from config import ALL_PRODUCTS, SETTINGS
from database import init_db, get_recent_changes, get_price_history
from scraper import run_scrape
from reporter import generate_report, print_summary
from alerts import send_daily_alerts

log = logging.getLogger(__name__)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Big Whey competitor price tracker"
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Run daily at the time set in config.py (blocks forever)"
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="Generate report from existing DB without scraping"
    )
    parser.add_argument(
        "--brand", type=str, default=None,
        help="Scrape only this brand (e.g. 'Bulk')"
    )
    parser.add_argument(
        "--history", action="store_true",
        help="Print recent price history for all products"
    )
    return parser.parse_args()


# ─── Daily job ────────────────────────────────────────────────────────────────

def daily_job():
    log.info("=== Daily job starting ===")
    run_scrape()
    generate_report()
    print_summary()
    send_daily_alerts()
    log.info("=== Daily job complete ===")


# ─── History printer ──────────────────────────────────────────────────────────

def print_history():
    from database import get_latest_all_products
    products = get_latest_all_products()
    if not products:
        print("No data yet. Run a scrape first.")
        return
    print(f"\n{'─'*70}")
    print(f"  PRICE HISTORY SUMMARY (7 days)")
    print(f"{'─'*70}")
    seen = set()
    for p in products:
        key = (p["brand"], p["product"], p["size"])
        if key in seen:
            continue
        seen.add(key)
        hist = get_price_history(p["brand"], p["product"], p["size"], days=7)
        if len(hist) < 2:
            continue
        first_price = hist[0]["price_per_srv"]
        last_price = hist[-1]["price_per_srv"]
        if first_price and last_price:
            change = (last_price - first_price) / first_price * 100
            arrow = "▲" if change > 0.5 else ("▼" if change < -0.5 else "→")
            print(
                f"  {p['brand']:22s} {p['size']:8s}  "
                f"£{first_price:.3f} → £{last_price:.3f}  {arrow} {change:+.1f}%"
            )
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    init_db()
    args = parse_args()

    if args.history:
        print_history()
        return

    if args.report_only:
        generate_report()
        print_summary()
        return

    if args.brand:
        targets = [p for p in ALL_PRODUCTS if p["brand"].lower() == args.brand.lower()]
        if not targets:
            print(f"Brand '{args.brand}' not found. Available: {[p['brand'] for p in ALL_PRODUCTS]}")
            sys.exit(1)
        run_scrape(products=targets)
        generate_report()
        print_summary()
        return

    if args.schedule:
        run_time = SETTINGS["run_time"]
        print(f"Scheduler started — running daily at {run_time} ({SETTINGS['timezone']})")
        print("Press Ctrl+C to stop.\n")

        # Run immediately on start so you get a baseline
        daily_job()

        schedule.every().day.at(run_time).do(daily_job)
        while True:
            schedule.run_pending()
            time.sleep(60)

    else:
        # Default: run once now
        run_scrape()
        generate_report()
        print_summary()


if __name__ == "__main__":
    main()
