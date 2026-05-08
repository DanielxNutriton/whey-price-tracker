"""
scraper.py — Core scraping engine.

Uses requests for standard sites, Playwright for JS-rendered brands
(Myprotein, Bulk, The Protein Works).
"""

import hashlib
import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from config import ALL_PRODUCTS, SETTINGS
from database import save_snapshot, save_change, get_last_snapshot, init_db
from scrapers.parsers import dispatch_parser, PLAYWRIGHT_BRANDS

# ── Logging ───────────────────────────────────────────────────────────────────
import pathlib
pathlib.Path(SETTINGS["log_path"]).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(SETTINGS["log_path"]),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── requests session ──────────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.6367.207 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
})

# ── Playwright fetch (lazy import — only loaded if needed) ────────────────────

_playwright_browser = None
_playwright_instance = None


def _get_playwright_page():
    """Return a Playwright page, launching browser on first call."""
    global _playwright_browser, _playwright_instance
    try:
        from playwright.sync_api import sync_playwright
        if _playwright_instance is None:
            _playwright_instance = sync_playwright().start()
            _playwright_browser = _playwright_instance.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            log.info("Playwright browser launched")
        ctx = _playwright_browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.6367.207 Safari/537.36"
            ),
            locale="en-GB",
            timezone_id="Europe/London",
            viewport={"width": 1280, "height": 800},
        )
        return ctx.new_page()
    except Exception as e:
        log.error(f"Playwright failed to launch: {e}")
        return None


def _close_playwright():
    global _playwright_browser, _playwright_instance
    try:
        if _playwright_browser:
            _playwright_browser.close()
        if _playwright_instance:
            _playwright_instance.stop()
    except Exception:
        pass
    _playwright_browser = None
    _playwright_instance = None


# ── Fetch functions ───────────────────────────────────────────────────────────

def fetch_with_requests(url: str) -> BeautifulSoup | None:
    """Standard requests fetch with retries. Fresh session per call to avoid
    Cloudflare cookie contamination across different domains."""
    for attempt in range(1, SETTINGS["max_retries"] + 1):
        try:
            sess = requests.Session()
            sess.headers.update(SESSION.headers)
            resp = sess.get(url, timeout=SETTINGS["request_timeout_seconds"],
                            allow_redirects=True)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as exc:
            log.warning(f"  requests attempt {attempt}/{SETTINGS['max_retries']}: {exc}")
            if attempt < SETTINGS["max_retries"]:
                time.sleep(SETTINGS["request_delay_seconds"] * attempt)
    return None


def fetch_with_playwright(url: str) -> BeautifulSoup | None:
    """Playwright fetch — waits for JS to render prices."""
    for attempt in range(1, SETTINGS["max_retries"] + 1):
        try:
            page = _get_playwright_page()
            if not page:
                return None
            resp = page.goto(url, wait_until="networkidle", timeout=30000)
            if not resp or resp.status >= 400:
                log.warning(f"  Playwright attempt {attempt}: HTTP {resp.status if resp else 'N/A'}")
                page.context.close()
                if attempt < SETTINGS["max_retries"]:
                    time.sleep(SETTINGS["request_delay_seconds"] * attempt)
                continue
            # Small extra wait for price JS to settle
            page.wait_for_timeout(2000)
            html = page.content()
            page.context.close()
            return BeautifulSoup(html, "html.parser")
        except Exception as exc:
            log.warning(f"  Playwright attempt {attempt}/{SETTINGS['max_retries']}: {exc}")
            if attempt < SETTINGS["max_retries"]:
                time.sleep(SETTINGS["request_delay_seconds"] * attempt)
    return None


def fetch_page(product: dict) -> BeautifulSoup | None:
    """Route to the right fetcher based on brand."""
    brand = product["brand"]
    url = product["url"]
    if brand in PLAYWRIGHT_BRANDS:
        log.info(f"  Using Playwright for {brand}")
        soup = fetch_with_playwright(url)
        # If Playwright fails, try requests as fallback
        if soup is None:
            log.warning(f"  Playwright failed, falling back to requests for {brand}")
            soup = fetch_with_requests(url)
    else:
        soup = fetch_with_requests(url)
    return soup


# ── Change detection ──────────────────────────────────────────────────────────

def _desc_hash(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.md5(text.strip().encode()).hexdigest()


def detect_changes(product: dict, new_price: float | None, new_desc: str | None,
                   new_compare_at: float | None = None):
    last = get_last_snapshot(product["brand"], product["product"], product["size"])
    if not last:
        return

    now = datetime.now(timezone.utc).isoformat()

    # Price change
    if new_price is not None and last["price"] is not None:
        pct = (new_price - last["price"]) / last["price"] * 100
        if abs(pct) >= SETTINGS["price_change_alert_pct"]:
            direction = "RISE" if pct > 0 else "DROP"
            log.warning(
                f"⚠ PRICE {direction}: {product['brand']} {product['size']} "
                f"£{last['price']:.2f} → £{new_price:.2f} ({pct:+.1f}%)"
            )
            save_change({
                "detected_at": now,
                "brand": product["brand"],
                "product": product["product"],
                "size": product["size"],
                "change_type": "price",
                "old_value": str(last["price"]),
                "new_value": str(new_price),
                "pct_change": round(pct, 2),
            })

    # Sale started — was not on sale, now is
    was_on_sale = bool(last.get("on_sale"))
    now_on_sale = bool(new_compare_at and new_price and new_compare_at > new_price)
    if now_on_sale and not was_on_sale:
        saving_pct = round((new_compare_at - new_price) / new_compare_at * 100, 1)
        log.warning(
            f"🏷 SALE STARTED: {product['brand']} {product['size']} "
            f"£{new_compare_at:.2f} → £{new_price:.2f} ({saving_pct}% off)"
        )
        save_change({
            "detected_at": now,
            "brand": product["brand"],
            "product": product["product"],
            "size": product["size"],
            "change_type": "sale_started",
            "old_value": str(new_compare_at),
            "new_value": str(new_price),
            "pct_change": -saving_pct,
        })

    # Sale ended — was on sale, now is not
    elif was_on_sale and not now_on_sale and new_price is not None:
        log.warning(
            f"🏷 SALE ENDED: {product['brand']} {product['size']} "
            f"back to £{new_price:.2f}"
        )
        save_change({
            "detected_at": now,
            "brand": product["brand"],
            "product": product["product"],
            "size": product["size"],
            "change_type": "sale_ended",
            "old_value": str(last.get("compare_at_price")),
            "new_value": str(new_price),
            "pct_change": None,
        })

    # Description change
    if SETTINGS["desc_change_alert"] and new_desc:
        old_hash = last.get("description_hash")
        new_hash = _desc_hash(new_desc)
        if old_hash and new_hash and old_hash != new_hash:
            log.warning(f"⚠ DESCRIPTION CHANGED: {product['brand']} {product['size']}")
            save_change({
                "detected_at": now,
                "brand": product["brand"],
                "product": product["product"],
                "size": product["size"],
                "change_type": "description",
                "old_value": last.get("description_raw", "")[:200],
                "new_value": (new_desc or "")[:200],
                "pct_change": None,
            })

    # Price disappeared
    if new_price is None and last["price"] is not None:
        log.warning(
            f"⚠ PRICE MISSING: {product['brand']} {product['size']} "
            f"(was £{last['price']:.2f})"
        )
        save_change({
            "detected_at": now,
            "brand": product["brand"],
            "product": product["product"],
            "size": product["size"],
            "change_type": "unavailable",
            "old_value": str(last["price"]),
            "new_value": None,
            "pct_change": None,
        })


# ── Per-product scrape ────────────────────────────────────────────────────────

def scrape_product(product: dict) -> dict:
    label = f"{product['brand']} {product['size']}"
    log.info(f"Scraping: {label}")

    scraped_at = datetime.now(timezone.utc).isoformat()
    soup = fetch_page(product)

    if soup is None:
        log.error(f"FAILED: {label}")
        row = {
            "scraped_at": scraped_at,
            "brand": product["brand"],
            "product": product["product"],
            "size": product["size"],
            "url": product["url"],
            "price": None,
            "currency": "GBP",
            "servings": product["servings"],
            "protein_per_srv": product["protein_per_serving_g"],
            "serving_size_g": product["serving_size_g"],
            "price_per_srv": None,
            "price_per_100g_protein": None,
            "compare_at_price": None,
            "on_sale": 0,
            "sale_saving_pct": None,
            "description_hash": None,
            "description_raw": None,
            "scrape_ok": 0,
            "error_msg": "fetch failed after retries",
        }
        save_snapshot(row)
        return row

    parsed = dispatch_parser(soup, product)
    price = parsed.get("price")
    description = parsed.get("description")
    compare_at = parsed.get("compare_at_price")

    servings = product["servings"]
    pps = round(price / servings, 4) if price else None
    protein_g_total = servings * product["protein_per_serving_g"]
    p100 = round(price / (protein_g_total / 100), 2) if price and protein_g_total else None

    on_sale = bool(compare_at and price and compare_at > price)
    sale_saving_pct = None
    if on_sale:
        sale_saving_pct = round((compare_at - price) / compare_at * 100, 1)
        log.info(f"  {label}: £{price:.2f} (was £{compare_at:.2f}, {sale_saving_pct}% off) → £{pps:.3f}/srv")
    elif price:
        log.info(f"  {label}: £{price:.2f} → £{pps:.3f}/srv")
    else:
        log.info(f"  {label}: price not found")

    row = {
        "scraped_at": scraped_at,
        "brand": product["brand"],
        "product": product["product"],
        "size": product["size"],
        "url": product["url"],
        "price": price,
        "currency": "GBP",
        "servings": servings,
        "protein_per_srv": product["protein_per_serving_g"],
        "serving_size_g": product["serving_size_g"],
        "price_per_srv": pps,
        "price_per_100g_protein": p100,
        "compare_at_price": compare_at,
        "on_sale": 1 if on_sale else 0,
        "sale_saving_pct": sale_saving_pct,
        "description_hash": _desc_hash(description),
        "description_raw": description,
        "scrape_ok": 1,
        "error_msg": None,
    }

    detect_changes(product, price, description, compare_at)
    save_snapshot(row)
    time.sleep(SETTINGS["request_delay_seconds"])
    return row


# ── Full run ──────────────────────────────────────────────────────────────────

def run_scrape(products: list[dict] | None = None) -> list[dict]:
    init_db()
    targets = products or ALL_PRODUCTS
    log.info(f"=== Scrape run started — {len(targets)} products ===")

    playwright_count = sum(1 for p in targets if p["brand"] in PLAYWRIGHT_BRANDS)
    if playwright_count:
        log.info(f"  {playwright_count} products will use Playwright (JS-rendered sites)")

    results = []
    for product in targets:
        try:
            row = scrape_product(product)
            results.append(row)
        except Exception as exc:
            log.exception(f"Unexpected error scraping {product['brand']}: {exc}")

    _close_playwright()

    ok = sum(1 for r in results if r.get("scrape_ok"))
    with_price = sum(1 for r in results if r.get("price"))
    log.info(
        f"=== Scrape complete — {ok}/{len(results)} fetched, "
        f"{with_price}/{len(results)} prices found ==="
    )
    return results


if __name__ == "__main__":
    run_scrape()
