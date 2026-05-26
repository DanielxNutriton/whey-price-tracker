"""
scrapers/parsers.py — Rewritten from live diagnostic output, May 2026.
"""

import re
import json
from bs4 import BeautifulSoup


def _clean_price(text: str) -> float | None:
    if not text:
        return None
    text = text.replace("Â", "").replace("\u200e", "").replace(",", "").strip()
    match = re.search(r"£?\s*([\d]+\.[\d]{2})", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _meta_price(soup: BeautifulSoup, prefer: str = "product") -> float | None:
    order = (["product:price:amount", "og:price:amount"] if prefer == "product"
             else ["og:price:amount", "product:price:amount"])
    for prop in order:
        tag = soup.find("meta", {"property": prop}) or soup.find("meta", {"name": prop})
        if tag and tag.get("content"):
            try:
                return float(tag["content"])
            except ValueError:
                pass
    return None


def _json_ld_price(soup: BeautifulSoup) -> float | None:
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                offers = item.get("offers")
                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("lowPrice")
                    if price:
                        return float(price)
                if isinstance(offers, list) and offers:
                    price = offers[0].get("price")
                    if price:
                        return float(price)
        except Exception:
            pass
    return None


def _json_ld_all_prices(soup: BeautifulSoup) -> list:
    prices = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                graph = item.get("@graph", [item])
                for node in graph:
                    offers = node.get("offers")
                    if isinstance(offers, dict):
                        p = offers.get("price") or offers.get("lowPrice")
                        if p:
                            try: prices.append(float(p))
                            except: pass
                    if isinstance(offers, list):
                        for o in offers:
                            p = o.get("price")
                            if p:
                                try: prices.append(float(p))
                                except: pass
        except Exception:
            pass
    return prices


def _extract_variation_id_from_url(url: str):
    match = re.search(r"[?&]variation=(\d+)", url)
    return match.group(1) if match else None


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_nutritionx(soup, product):
    """meta[product:price:amount] works. [data-price-type=finalPrice] backup."""
    price = _meta_price(soup, prefer="product")
    if not price:
        for sel in ["[data-price-type='finalPrice']", ".product-info-price .price", ".special-price .price"]:
            el = soup.select_one(sel)
            if el:
                price = _clean_price(el.get_text())
                if price: break
    # Nutrition X Magento: .old-price or special-price vs regular-price
    compare_at = None
    old_el = soup.select_one(".old-price .price") or soup.select_one(".regular-price .price")
    if old_el:
        compare_at = _clean_price(old_el.get_text())
        if compare_at and price and compare_at <= price:
            compare_at = None
    desc_el = soup.select_one(".product.attribute.description") or soup.select_one(".product-info-main .description")
    return {"price": price, "compare_at_price": compare_at, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_myprotein(soup, product):
    """
    JS-rendered. Playwright renders the page but .price always shows the default
    size (900g = £27.99) regardless of the ?variation= URL param — Myprotein's JS
    ignores the param on initial load.

    Strategy: find the variation ID in the script data and extract its price.
    Diagnostic showed £77.49 IS in page source near '2.7kg' and variation ID.
    Script[8] has all variant prices: ['126.49','109.45','66.49','27.99',...].
    We find the price closest to our verified config price for this size.
    """
    variation_id = _extract_variation_id_from_url(product.get("url", ""))
    target_price = product.get("price", 0)
    price = None

    # Primary: find this variation's price in script data
    for script in soup.find_all("script"):
        txt = script.string or ""
        if not txt or len(txt) < 50:
            continue

        # Look for variation ID near a price
        if variation_id and variation_id in txt:
            m = re.search(
                rf'{variation_id}.{{0,400}}"price"\s*:\s*"?([\d.]+)"?',
                txt, re.DOTALL
            )
            if m:
                try:
                    p = float(m.group(1))
                    if 5 < p < 500:
                        price = p
                        break
                except ValueError:
                    pass

        # Fallback: find all prices in script and pick closest to target
        if not price and target_price and len(txt) > 500:
            all_prices = re.findall(r'"price"\s*:\s*"?([\d]{2,3}\.[\d]{2})"?', txt)
            candidates = []
            for p_str in all_prices:
                try:
                    p = float(p_str)
                    if 5 < p < 500:
                        candidates.append(p)
                except ValueError:
                    pass
            if candidates:
                closest = min(candidates, key=lambda p: abs(p - target_price))
                if abs(closest - target_price) < 10:
                    price = closest
                    break

    # Last resort: .price selector (will be wrong size but better than nothing)
    if not price:
        for sel in [".price", ".productPrice_price"]:
            el = soup.select_one(sel)
            if el:
                price = _clean_price(el.get_text())
                if price and 5 < price < 500:
                    break

    desc_el = soup.select_one(".productDescription_synopsis") or soup.select_one(".product-description")
    return {"price": price, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_bulk(soup, product):
    """
    JS-rendered. Diagnostic: JSON-LD has all variant prices.
    Match closest to the verified config price for this size.
    """
    target_price = product.get("price")
    all_prices = _json_ld_all_prices(soup)
    price = None
    if all_prices and target_price:
        closest = min(all_prices, key=lambda p: abs(p - target_price))
        if abs(closest - target_price) < 15:
            price = closest
    if not price and all_prices:
        price = min(all_prices)  # fallback: cheapest = smallest size
    if not price:
        for sel in [".price--current", "[data-price]", ".pdp-price"]:
            el = soup.select_one(sel)
            if el:
                price = _clean_price(el.get("data-price") or el.get_text())
                if price: break
    desc_el = soup.select_one(".product-description")
    return {"price": price, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_applied_nutrition(soup, product):
    """
    Shopify. Diagnostic2 revealed:
      JSON-LD price=59.95 ❌ (always returns 2kg regardless of variant URL)
      meta og:price:amount=8.95 ❌ (trial size default)
      Shopify variants script[64]:
        id=55037133029751  price=£59.95  (2kg)
        id=55702274310519  price=£29.95  (825g) ✅
        id=56469861040503  price=£8.95   (trial)
    Strategy: extract variant ID from URL, match against Shopify variants JSON.
    """
    url = product.get("url", "")
    variant_id = re.search(r"[?&]variant=(\d+)", url)
    variant_id = variant_id.group(1) if variant_id else None

    price = None

    # Primary: Shopify variants JSON — most accurate for specific variant
    if variant_id:
        for script in soup.find_all("script"):
            txt = script.string or ""
            if '"variants"' not in txt or len(txt) > 500000:
                continue
            # Find this specific variant ID and its price (in pence)
            pattern = rf'"id"\s*:\s*{variant_id}\s*[,{{].*?"price"\s*:\s*(\d+)'
            m = re.search(pattern, txt, re.DOTALL)
            if m:
                try:
                    price = float(m.group(1)) / 100
                    break
                except ValueError:
                    pass
            # Also try price before id
            pattern2 = rf'"price"\s*:\s*(\d+).*?"id"\s*:\s*{variant_id}'
            m2 = re.search(pattern2, txt, re.DOTALL)
            if m2:
                try:
                    price = float(m2.group(1)) / 100
                    break
                except ValueError:
                    pass

    # Fallback: JSON-LD (will give wrong variant but better than nothing)
    if not price:
        price = _json_ld_price(soup)

    if not price:
        for sel in [".price-item--regular", ".price-item--sale", ".price__current"]:
            el = soup.select_one(sel)
            if el:
                price = _clean_price(el.get_text())
                if price:
                    break

    desc_el = soup.select_one(".product__description") or soup.select_one(".product-description")
    return {"price": price, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_optimum_nutrition(soup, product):
    """
    Shopify. Diagnostic: meta[product:price:amount]=40.00 ✅  JSON-LD also correct.
    """
    price = _meta_price(soup, prefer="product") or _json_ld_price(soup)
    if not price:
        for sel in [".price__current", ".price-item--regular"]:
            el = soup.select_one(sel)
            if el:
                price = _clean_price(el.get_text())
                if price: break
    variant_id = re.search(r"[?&]variant=(\d+)", product.get("url", ""))
    compare_at = _shopify_compare_at_price(soup, variant_id.group(1) if variant_id else None)
    desc_el = soup.select_one(".product__description") or soup.select_one(".product-description")
    return {"price": price, "compare_at_price": compare_at, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_kinetica(soup, product):
    """
    Shopify. Diagnostic: og:price:amount=44.99 ✅  JSON-LD=44.99 ✅
    Each size has its own URL — no variant matching needed.
    """
    price = _meta_price(soup, prefer="og") or _json_ld_price(soup)
    if not price:
        for sel in [".price-item--regular", ".price-item--sale", ".price__current"]:
            el = soup.select_one(sel)
            if el:
                price = _clean_price(el.get_text())
                if price: break
    compare_at = _shopify_compare_at_price(soup, None)
    desc_el = soup.select_one(".product__description") or soup.select_one(".product-description")
    return {"price": price, "compare_at_price": compare_at, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_usn(soup, product):
    """
    Shopify. Diagnostic: meta[product:price:amount]=36.00 ✅  JSON-LD=£18.00 ❌ (lowest variant).
    Use meta (variant-aware) then .price-item--sale.
    """
    price = _meta_price(soup, prefer="product")
    if not price:
        el = soup.select_one(".price-item--sale") or soup.select_one(".price-item--regular")
        if el:
            price = _clean_price(el.get_text())
    variant_id = re.search(r"[?&]variant=(\d+)", product.get("url", ""))
    compare_at = _shopify_compare_at_price(soup, variant_id.group(1) if variant_id else None)
    desc_el = soup.select_one(".product__description")
    return {"price": price, "compare_at_price": compare_at, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_protein_works(soup, product):
    """
    Magento-based. Diagnostic2 revealed:
      - Only one size button rendered at a time (button[class*='size'] = '500g')
      - itemprop=price always shows the currently active size (500g=£19.19)
      - Size buttons have base64-encoded Magento attribute values
      - All sizes share one URL — Playwright must click the size button

    Since clicking requires Playwright interaction (not just HTML parsing),
    and the scraper.py fetch_with_playwright only fetches without clicking,
    we read whichever size is currently displayed and store it.

    TODO: For accurate per-size pricing, Playwright needs to click each
    size button before reading. For now, store the displayed price and
    flag it with the actual size shown on page.

    For daily monitoring, the key signal is WHEN the price changes —
    the absolute value per size can be manually verified.
    """
    price = None

    # itemprop=price gives the currently displayed size price
    el = soup.select_one("[itemprop='price']")
    if el:
        val = el.get("content") or el.get_text(strip=True)
        try:
            p = float(val.replace(",", "").strip())
            if 5 < p < 300:
                price = p
        except (ValueError, TypeError):
            pass

    if not price:
        price = _json_ld_price(soup) or _meta_price(soup)

    desc_el = soup.select_one(".product-description") or soup.select_one(".tab-content")
    return {"price": price, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_sis(soup, product):
    """
    scienceinsport.com — Magento configurable product.

    Page structure (from live diagnostic):
      jsonConfig.attributes.173 = pack_size attribute
        option 18263 = '450g'  → product IDs ['8081','8084','8087'] → finalPrice £25
        option 18257 = '1.35kg'→ product IDs ['8072','8075','8078'] → finalPrice £60
      jsonConfig.optionPrices = {product_id: {finalPrice: {amount: X}}}

    Strategy:
      1. Parse the Magento jsonConfig from the page script
      2. Find the pack_size option whose label matches our size (e.g. '1.35kg')
      3. Get the product IDs for that option
      4. Look up finalPrice for those product IDs in optionPrices
      5. Return that price

    This is the only reliable method — meta always returns the page default
    (450g = £25) regardless of which SKU is in the URL.
    """
    size = product.get("size", "")
    price = None

    for script in soup.find_all("script"):
        txt = script.string or ""
        if "jsonConfig" not in txt or "optionPrices" not in txt:
            continue

        try:
            # Extract optionPrices: {product_id: {finalPrice: {amount: X}}}
            # Extract optionPrices block
            op_match = re.search(r'"optionPrices"\s*:\s*(\{["\d].*?"msrpPrice":\{"amount":\d+\}\})\}', txt, re.DOTALL)
            if not op_match:
                op_match = re.search(r'optionPrices["\s:]+(\{[^;]{50,8000}\})\s*[,}]', txt, re.DOTALL)
            if not op_match:
                continue

            # Build product_id → finalPrice map using two-step approach
            op_txt = op_match.group(1)
            option_prices = {}
            for pid_match in re.finditer(r'"(\d{4,5})"\s*:\s*\{', op_txt):
                pid = pid_match.group(1)
                rest = op_txt[pid_match.end():]
                fp = re.search(r'"finalPrice"\s*:\s*\{"amount"\s*:\s*([\d.]+)\}', rest[:400])
                if fp:
                    option_prices[pid] = float(fp.group(1))

            if not option_prices:
                continue

            # Find pack_size options using the actual format seen in diagnostic
            pack_size_match = re.search(
                r'"code"\s*:\s*"pack_size".*?"options"\s*:\s*(\[.*?\])\s*,\s*"position"',
                txt, re.DOTALL
            )
            if not pack_size_match:
                pack_size_match = re.search(
                    r'"label"\s*:\s*"Pack Size".*?"options"\s*:\s*(\[.*?\])\s*,\s*"position"',
                    txt, re.DOTALL
                )
            if not pack_size_match:
                continue

            options_txt = pack_size_match.group(1)

            # Find the option whose label matches our size
            # e.g. size='1.35kg' should match label='1.35kg'
            size_clean = size.replace(" ", "").lower()

            for opt_match in re.finditer(
                r'"label"\s*:\s*"([^"]+)"\s*,\s*"products"\s*:\s*\[([^\]]+)\]',
                options_txt
            ):
                label = opt_match.group(1).replace(" ", "").lower()
                product_ids = re.findall(r'"(\d+)"', opt_match.group(2))

                if label == size_clean or size_clean in label or label in size_clean:
                    # Find price for these product IDs
                    for pid in product_ids:
                        if pid in option_prices:
                            price = option_prices[pid]
                            break
                    if price:
                        break

        except Exception:
            pass

        if price:
            break

    # Fallback: meta for small sizes, expected price as last resort
    if not price:
        expected = product.get("price", 0)
        if expected and expected < 40:
            price = _meta_price(soup, prefer="product")

    if not price:
        all_prices = _json_ld_all_prices(soup)
        expected = product.get("price", 0)
        if all_prices and expected:
            closest = min(all_prices, key=lambda p: abs(p - expected))
            if abs(closest - expected) < 20:
                price = closest

    compare_at = _magento_old_price(soup, product.get("size", ""))
    desc_el = (soup.select_one(".product.attribute.description") or
               soup.select_one(".product-description"))
    return {"price": price, "compare_at_price": compare_at, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_healthspan(soup, product):
    """WooCommerce. Diagnostic: JSON-LD=33.990000 ✅"""
    price = _json_ld_price(soup)
    if not price:
        for sel in [".woocommerce-Price-amount", ".price"]:
            el = soup.select_one(sel)
            if el:
                price = _clean_price(el.get_text())
                if price: break
    desc_el = soup.select_one(".product-description") or soup.select_one(".woocommerce-product-details__short-description")
    return {"price": price, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


def parse_soccer_supplement(soup, product):
    """
    Shopify. Diagnostic: JSON-LD=41.95 ✅  .product__price='£41.95' ✅
    Avoid span.money — showed £0.00.
    CSS selectors first: JSON-LD can include related/other products and return
    the wrong price when the page is served from a different edge location.
    """
    price = None
    for sel in [".product__price", "[data-product-price]"]:
        el = soup.select_one(sel)
        if el:
            price = _clean_price(el.get_text())
            if price:
                break
    if not price:
        price = _meta_price(soup, prefer="product") or _meta_price(soup, prefer="og")
    if not price:
        price = _json_ld_price(soup)
    desc_el = soup.select_one(".product__description")
    return {"price": price, "description": desc_el.get_text(separator=" ", strip=True)[:500] if desc_el else None}


# ── Dispatcher ────────────────────────────────────────────────────────────────

PARSER_MAP = {
    "Nutrition X":        parse_nutritionx,
    "Myprotein":          parse_myprotein,
    "Bulk":               parse_bulk,
    "Applied Nutrition":  parse_applied_nutrition,
    "Optimum Nutrition":  parse_optimum_nutrition,
    "Kinetica":           parse_kinetica,
    "USN":                parse_usn,
    "The Protein Works":  parse_protein_works,
    "SIS":                parse_sis,
    "Healthspan":         parse_healthspan,
    "Soccer Supplement":  parse_soccer_supplement,
}

PLAYWRIGHT_BRANDS = {"Myprotein", "Bulk", "The Protein Works"}


def dispatch_parser(soup: BeautifulSoup, product: dict) -> dict:
    brand = product["brand"]
    parser = PARSER_MAP.get(brand)
    if parser:
        return parser(soup, product)
    price = _json_ld_price(soup) or _meta_price(soup)
    return {"price": price, "description": None}


# ── Sale detection helpers ─────────────────────────────────────────────────────

def _shopify_compare_at_price(soup: BeautifulSoup, variant_id: str | None) -> float | None:
    """
    Read compare_at_price from Shopify variants JSON.
    If compare_at_price > price, the item is genuinely on sale.
    Returns None if not on sale or not found.
    """
    for script in soup.find_all("script"):
        txt = script.string or ""
        if '"variants"' not in txt or len(txt) > 500000:
            continue

        # Find all variants and their compare_at_price
        if variant_id:
            # Find this variant block and extract compare_at_price
            pattern = rf'"id"\s*:\s*{variant_id}[\s\S]{{0,600}}"compare_at_price"\s*:\s*(\d+|null)'
            m = re.search(pattern, txt)
            if m and m.group(1) != "null":
                try:
                    val = float(m.group(1)) / 100
                    return val if val > 0 else None
                except ValueError:
                    pass

            # Also try compare_at_price before id
            pattern2 = rf'"compare_at_price"\s*:\s*(\d+)[\s\S]{{0,300}}"id"\s*:\s*{variant_id}'
            m2 = re.search(pattern2, txt)
            if m2:
                try:
                    val = float(m2.group(1)) / 100
                    return val if val > 0 else None
                except ValueError:
                    pass

        # No variant ID — just find first non-zero compare_at_price
        m = re.search(r'"compare_at_price"\s*:\s*(\d+)', txt)
        if m:
            try:
                val = float(m.group(1)) / 100
                return val if val > 0 else None
            except ValueError:
                pass
    return None


def _magento_old_price(soup: BeautifulSoup, size: str) -> float | None:
    """
    Read oldPrice from Magento optionPrices config.
    If oldPrice > finalPrice, the item is on sale.
    """
    for script in soup.find_all("script"):
        txt = script.string or ""
        if "optionPrices" not in txt or "pack_size" not in txt:
            continue
        try:
            # Find pack_size option matching our size
            pack_match = re.search(
                r'"code"\s*:\s*"pack_size".*?"options"\s*:\s*(\[.*?\])\s*,\s*"position"',
                txt, re.DOTALL
            )
            if not pack_match:
                continue
            size_clean = size.replace(" ", "").lower()
            product_ids = []
            for opt in re.finditer(r'"label"\s*:\s*"([^"]+)"\s*,\s*"products"\s*:\s*\[([^\]]+)\]',
                                   pack_match.group(1)):
                label = opt.group(1).replace(" ", "").lower()
                if label == size_clean or size_clean in label or label in size_clean:
                    product_ids = re.findall(r'"(\d+)"', opt.group(2))
                    break

            # Find oldPrice for these product IDs
            for pid in product_ids:
                pid_match = re.search(rf'"{pid}"\s*:\s*\{{', txt)
                if pid_match:
                    rest = txt[pid_match.end():]
                    op = re.search(r'"oldPrice"\s*:\s*\{"amount"\s*:\s*([\d.]+)\}', rest[:400])
                    fp = re.search(r'"finalPrice"\s*:\s*\{"amount"\s*:\s*([\d.]+)\}', rest[:400])
                    if op and fp:
                        old = float(op.group(1))
                        final = float(fp.group(1))
                        if old > final:
                            return old
        except Exception:
            pass
    return None
