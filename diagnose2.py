"""
diagnose2.py — Targeted diagnostic for remaining 4 issues.
Run: python3 diagnose2.py
Paste the output back to Claude.
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
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://www.google.com/",
}

lines = []

def log(s=""):
    print(s)
    lines.append(s)

def fresh_get(url):
    sess = requests.Session()
    sess.headers.update(HEADERS)
    return sess.get(url, timeout=20, allow_redirects=True)


# ── 1. Myprotein 2.7kg ────────────────────────────────────────────────────────
log("=" * 60)
log("1. MYPROTEIN 2.7kg")
log("   Goal: find £77.49 — currently returning £27.99 (900g price)")
log("=" * 60)

url = "https://www.myprotein.com/p/sports-nutrition/impact-whey-protein-powder/10530943/?variation=17712192"
r = fresh_get(url)
soup = BeautifulSoup(r.text, "html.parser")
log(f"HTTP: {r.status_code}")
log(f"Title: {soup.title.string.strip()[:70] if soup.title else 'N/A'}")

# Check .price selector text
for sel in [".price", ".productPrice_price",
            ".athenaProductPage_priceBlock .productPrice_price"]:
    el = soup.select_one(sel)
    if el:
        log(f"Selector [{sel}]: {el.get_text(strip=True)[:50]!r}")

# Look for all prices in scripts
log("Prices found in scripts:")
for i, script in enumerate(soup.find_all("script")):
    txt = script.string or ""
    # Find £XX.XX or price: XX.XX patterns
    matches = re.findall(r'(?:£|"price"\s*:\s*"?)([\d]{2,3}\.[\d]{2})', txt)
    if matches:
        unique = list(dict.fromkeys(matches))[:6]
        log(f"  script[{i}]: {unique}")

# Look for variation/2.7kg specifically
log("Searching for 2.7kg / 77.49 in page source:")
if "2.7" in r.text or "77.49" in r.text:
    log("  Found 2.7 or 77.49 in page source ✅")
    # Find context around it
    for pattern in ["2\.7.{0,100}", "77\.49.{0,100}"]:
        m = re.search(pattern, r.text)
        if m:
            log(f"  Context: {m.group(0)[:100]!r}")
else:
    log("  NOT found in page source ❌")

log()
time.sleep(3)

# ── 2. Applied Nutrition 825g ─────────────────────────────────────────────────
log("=" * 60)
log("2. APPLIED NUTRITION 825g")
log("   Goal: find £29.95 — currently returning £59.95 (2kg price)")
log("=" * 60)

url = "https://appliednutrition.uk/products/critical-whey?variant=55702274310519"
r = fresh_get(url)
soup = BeautifulSoup(r.text, "html.parser")
log(f"HTTP: {r.status_code}")

# JSON-LD
for script in soup.find_all("script", {"type": "application/ld+json"}):
    try:
        data = json.loads(script.string or "")
        items = data if isinstance(data, list) else [data]
        for item in items:
            offers = item.get("offers")
            if offers:
                log(f"JSON-LD offers: {json.dumps(offers)[:200]}")
    except Exception:
        pass

# Meta
for prop in ["product:price:amount", "og:price:amount"]:
    tag = soup.find("meta", {"property": prop})
    if tag:
        log(f"Meta [{prop}]: {tag.get('content')}")

# Look for 29.95 or 825 in scripts
log("Searching for 29.95 / 825g in page:")
if "29.95" in r.text:
    log("  Found 29.95 ✅")
    m = re.search(r'.{0,50}29\.95.{0,50}', r.text)
    if m:
        log(f"  Context: {m.group(0)!r}")
else:
    log("  29.95 NOT in page ❌")

# Shopify variants JSON
log("Shopify variants in scripts:")
for i, script in enumerate(soup.find_all("script")):
    txt = script.string or ""
    if '"variants"' in txt and len(txt) < 200000:
        # Extract variant prices
        variant_prices = re.findall(
            r'"id"\s*:\s*(\d+).{0,100}"price"\s*:\s*(\d+)', txt
        )
        if variant_prices:
            log(f"  script[{i}] variants (id, price_pence):")
            for vid, price in variant_prices[:6]:
                log(f"    id={vid}  price=£{int(price)/100:.2f}")
        break

log()
time.sleep(3)

# ── 3. SIS 450g ───────────────────────────────────────────────────────────────
log("=" * 60)
log("3. SIS 450g")
log("   Goal: find £25.00 — currently returning £60.00 (1.35kg price)")
log("=" * 60)

url = "https://www.scienceinsport.com/shop-by-need/recovery/rego-whey-powder?sku=131924"
r = fresh_get(url)
soup = BeautifulSoup(r.text, "html.parser")
log(f"HTTP: {r.status_code}")

# JSON-LD
for script in soup.find_all("script", {"type": "application/ld+json"}):
    try:
        data = json.loads(script.string or "")
        items = data if isinstance(data, list) else [data]
        for item in items:
            offers = item.get("offers")
            if offers:
                log(f"JSON-LD offers: {json.dumps(offers)[:300]}")
    except Exception:
        pass

# Meta
for prop in ["product:price:amount", "og:price:amount"]:
    tag = soup.find("meta", {"property": prop})
    if tag:
        log(f"Meta [{prop}]: {tag.get('content')}")

# Magento price config
log("Magento price config in scripts:")
for i, script in enumerate(soup.find_all("script")):
    txt = script.string or ""
    if "jsonConfig" in txt or "spConfig" in txt or ("finalPrice" in txt and "amount" in txt):
        log(f"  Found price config in script[{i}] ({len(txt)} chars)")
        # Look for both SKU prices
        for sku in ["131924", "131925"]:
            m = re.search(
                rf'{sku}.{{0,300}}"amount"\s*:\s*"?([\d.]+)"?',
                txt, re.DOTALL
            )
            if m:
                log(f"  SKU {sku} price: £{m.group(1)}")
        # Show snippet
        log(f"  First 300 chars: {txt[:300]!r}")
        break

log("Searching for 25.00 in page:")
if "25.00" in r.text or "25,00" in r.text:
    log("  Found 25.00 ✅")
else:
    log("  NOT found ❌")

log()
time.sleep(3)

# ── 4. TPW all sizes ──────────────────────────────────────────────────────────
log("=" * 60)
log("4. THE PROTEIN WORKS — size selection")
log("   Goal: get correct price per size, currently all return £19.19")
log("=" * 60)

url = "https://www.theproteinworks.com/whey-protein-80-concentrate"
r = fresh_get(url)
soup = BeautifulSoup(r.text, "html.parser")
log(f"HTTP: {r.status_code}")
log(f"Title: {soup.title.string.strip()[:70] if soup.title else 'N/A'}")

# itemprop price
el = soup.select_one("[itemprop='price']")
log(f"itemprop=price: {el}")

# Look for size buttons / options
for sel in ["[data-weight]", "[data-size]", "[data-variant]",
            "button[class*='size']", "label[class*='size']",
            "[class*='weight']", "[class*='pack-size']",
            "select option", "[class*='variant']"]:
    els = soup.select(sel)
    if els:
        log(f"Selector [{sel}]: {len(els)} found")
        for el in els[:5]:
            log(f"  text={el.get_text(strip=True)[:30]!r} attrs={dict(list(el.attrs.items())[:3])}")

# Look for price data in scripts
log("Size-price data in scripts:")
for i, script in enumerate(soup.find_all("script")):
    txt = script.string or ""
    if len(txt) < 100:
        continue
    # Find all prices
    prices = re.findall(r'"price"\s*[:\s]+["\']?([\d]{2,3}\.[\d]{2})["\']?', txt)
    sizes_found = [s for s in ["500g", "1kg", "2kg", "4kg"] if s in txt]
    if prices and sizes_found:
        log(f"  script[{i}] ({len(txt)} chars): prices={prices[:6]} sizes={sizes_found}")
        # Show relevant snippet
        for size in ["1kg", "2kg"]:
            m = re.search(rf'.{{0,30}}{size}.{{0,100}}', txt)
            if m:
                log(f"    {size} context: {m.group(0)[:120]!r}")
        break
    elif prices and len(txt) > 1000:
        log(f"  script[{i}]: prices={prices[:4]} (no size labels found)")

# Check for Next.js or similar data
for pattern in [r'__NEXT_DATA__\s*=\s*({.*?})\s*;', r'window\.__data__\s*=\s*({.*?})\s*;']:
    m = re.search(pattern, r.text, re.DOTALL)
    if m:
        log(f"Found global data object ({len(m.group(1))} chars)")
        data_str = m.group(1)
        for size in ["500g", "1kg", "2kg", "4kg"]:
            sm = re.search(rf'{size}.{{0,200}}([\d]{{2,3}}\.[\d]{{2}})', data_str)
            if sm:
                log(f"  {size}: £{sm.group(1)}")

log()
log("=" * 60)
log("END — paste this output back to Claude")
log("=" * 60)

Path("diagnose2_output.txt").write_text("\n".join(lines))
print("\nSaved to diagnose2_output.txt")
