"""
diagnose.py — Run this locally to show exactly what each site returns.
Dumps price selectors, meta tags, JSON-LD, and a snippet of script tags
so we can write the correct parser for each brand.

Usage:  python3 diagnose.py
Output: diagnose_output.txt  (paste this back to Claude)
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.6367.207 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://www.google.com/",
}

# One URL per problematic brand
TARGETS = [
    ("Nutrition X 900g",    "https://www.nutritionx.co.uk/big-whey-protein-powder-900g"),
    ("Kinetica 1kg",        "https://uk.kineticasports.com/products/whey-protein-powder-vanilla-1kg"),
    ("ON 900g",             "https://www.optimumnutrition.com/en-gb/products/gold-standard-100-whey-protein-powder-eu?variant=52105832300811"),
    ("Applied 2kg",         "https://appliednutrition.uk/products/critical-whey?variant=55037133029751"),
    ("USN 908g",            "https://uk.usn.global/products/blue-lab-whey-protein?variant=32385253408827"),
    ("Soccer Supp 1kg",     "https://www.soccersupplement.com/products/new-whey-vanilla1kg"),
    ("Healthspan 750g",     "https://www.healthspanelite.co.uk/elite-all-blacks-ultimate-whey-protein-blend/"),
    ("SIS 1.35kg",          "https://www.scienceinsport.com/shop-by-need/recovery/rego-whey-powder?sku=131925"),
    ("Myprotein 900g",      "https://www.myprotein.com/p/sports-nutrition/impact-whey-protein-powder/10530943/?variation=17712277"),
    ("Bulk 1kg",            "https://www.bulk.com/uk/products/pure-whey-protein/bpb-wpc8-0000"),
    ("TPW 1kg",             "https://www.theproteinworks.com/whey-protein-80-concentrate"),
]

PRICE_SELECTORS = [
    ".price__current", ".price-item--regular", ".price-item--sale",
    ".product__price", ".productPrice_price", "[data-product-price]",
    "[data-price]", ".price--current", ".product-price", ".special-price .price",
    "[itemprop='price']", ".athenaProductPage_priceBlock .productPrice_price",
    ".woocommerce-Price-amount", "span.money", ".price",
    ".product-info-price .price", "[data-price-type='finalPrice']",
]

lines = []

def log(s=""):
    print(s)
    lines.append(s)

def find_prices_in_scripts(soup):
    """Find any price-like values in script tags."""
    results = []
    for i, script in enumerate(soup.find_all("script")):
        txt = script.string or ""
        if not txt or len(txt) < 20:
            continue
        # Look for currency-style prices
        matches = re.findall(r'(?:price|Price|PRICE)["\s:]+["\']?([\d]{2,6}\.?\d{0,2})["\']?', txt)
        if matches:
            vals = []
            for m in matches[:5]:
                try:
                    v = float(m)
                    if v > 500:  # likely pence
                        vals.append(f"£{v/100:.2f}(pence)")
                    elif 5 < v < 500:
                        vals.append(f"£{v:.2f}")
                except ValueError:
                    pass
            if vals:
                script_type = script.get("type", "")
                script_id = script.get("id", "")
                results.append(f"  script[{i}] type={script_type!r} id={script_id!r}: {vals[:4]}")
    return results

log("=" * 70)
log("BIG WHEY TRACKER — DIAGNOSTIC OUTPUT")
log("Paste this entire file back to Claude")
log("=" * 70)

sess = requests.Session()
sess.headers.update(HEADERS)

for brand, url in TARGETS:
    log(f"\n{'─'*60}")
    log(f"BRAND: {brand}")
    log(f"URL:   {url}")

    try:
        resp = sess.get(url, timeout=20, allow_redirects=True)
        log(f"HTTP:  {resp.status_code}  ({len(resp.text):,} bytes)")

        if resp.status_code != 200:
            log(f"  ❌ Blocked — cannot inspect")
            time.sleep(2)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        log(f"Title: {soup.title.string.strip()[:70] if soup.title else 'N/A'}")

        # 1. Meta price tags
        for prop in ["product:price:amount", "og:price:amount"]:
            tag = soup.find("meta", {"property": prop}) or soup.find("meta", {"name": prop})
            if tag:
                log(f"  META [{prop}]: {tag.get('content')}")

        # 2. JSON-LD
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    offers = item.get("offers")
                    if offers:
                        price = (offers.get("price") if isinstance(offers, dict)
                                 else offers[0].get("price") if offers else None)
                        log(f"  JSON-LD offers.price: {price}")
            except Exception:
                pass

        # 3. CSS selectors
        found_any = False
        for sel in PRICE_SELECTORS:
            els = soup.select(sel)
            for el in els[:2]:
                txt = el.get_text(strip=True)
                content = el.get("content", "")
                val = content or txt
                if val and any(c.isdigit() for c in val) and len(val) < 40:
                    log(f"  SELECTOR [{sel}]: {val!r}")
                    found_any = True
                    break
        if not found_any:
            log("  SELECTORS: none matched")

        # 4. Script tag price hunting
        script_prices = find_prices_in_scripts(soup)
        if script_prices:
            log("  SCRIPT PRICES:")
            for sp in script_prices[:6]:
                log(sp)
        else:
            log("  SCRIPT PRICES: none found")

        # 5. Show a small snippet of the largest script (usually product data)
        scripts = sorted(
            [s for s in soup.find_all("script") if s.string and len(s.string) > 200],
            key=lambda s: len(s.string), reverse=True
        )
        if scripts:
            biggest = scripts[0].string
            log(f"  LARGEST SCRIPT ({len(biggest):,} chars), first 400 chars:")
            log("  " + biggest[:400].replace("\n", " ").replace("  ", " "))

    except Exception as e:
        log(f"  ERROR: {e}")

    time.sleep(3)

log("\n" + "=" * 70)
log("END OF DIAGNOSTIC")
log("=" * 70)

output = "\n".join(lines)
Path("diagnose_output.txt").write_text(output)
print(f"\nSaved to diagnose_output.txt — paste that file back to Claude")
