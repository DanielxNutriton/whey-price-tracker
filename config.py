"""
config.py  —  Competitor URLs, product metadata, and scraper settings.
Last updated: May 2026 from verified data sheet.

NOTES FROM VERIFICATION:
- Myprotein: perpetual promo model — scraper will confirm if price ever changes
- Bulk: same — "sale" banners always showing, scraper will track if price actually moves
- The Protein Works: same perpetual promo model
- SIS: URLs point to REGO Whey (recovery product) — flagged for review,
  may not be comparable to standard whey. Confirm before treating as competitor.
- Applied Nutrition 132g trial size excluded (not comparable)
- The Protein Works 4kg: 40 servings corrected to 133 (25g scoop × 4000g ÷ 30)
"""

# ── Your products ──────────────────────────────────────────────────────────────
YOUR_PRODUCTS = [
    {
        "brand": "Nutrition X",
        "product": "Big Whey",
        "size": "900g",
        "url": "https://www.nutritionx.co.uk/big-whey-protein-powder-900g",
        "price": 41.99,
        "servings": 30,
        "protein_per_serving_g": 24.8,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Nutrition X",
        "product": "Big Whey",
        "size": "1.8kg",
        "url": "https://www.nutritionx.co.uk/big-whey-protein-powder",
        "price": 65.99,
        "servings": 60,
        "protein_per_serving_g": 24.8,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
]

# ── Competitor products ────────────────────────────────────────────────────────
# pricing_model values:
#   "standard_rrp"     — genuine RRP, sales are periodic
#   "perpetual_promo"  — displayed price is always "on sale", RRP is inflated fiction
#                        scraper will confirm by checking if price ever changes
#   "unknown"          — scraper will determine over first 2-4 weeks

COMPETITOR_PRODUCTS = [

    # ── Myprotein ──────────────────────────────────────────────────────────────
    # Perpetual promo model — "sale" countdown is always running
    # Scraper tracks one-off purchase price (not subscription)
    # Note: all 3 sizes share one base URL; variant param selects size
    {
        "brand": "Myprotein",
        "product": "Impact Whey Protein",
        "size": "450g",
        "url": "https://www.myprotein.com/p/sports-nutrition/impact-whey-protein-powder/10530943/?variation=17712244",
        "price": 16.99,
        "servings": 15,
        "protein_per_serving_g": 23,
        "serving_size_g": 30,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "Myprotein",
        "product": "Impact Whey Protein",
        "size": "900g",
        "url": "https://www.myprotein.com/p/sports-nutrition/impact-whey-protein-powder/10530943/?variation=17712277",
        "price": 27.99,
        "servings": 30,
        "protein_per_serving_g": 23,
        "serving_size_g": 30,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "Myprotein",
        "product": "Impact Whey Protein",
        "size": "2.7kg",
        "url": "https://www.myprotein.com/p/sports-nutrition/impact-whey-protein-powder/10530943/?variation=17712192",
        "price": 77.49,
        "servings": 90,
        "protein_per_serving_g": 23,
        "serving_size_g": 30,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },

    # ── Bulk ───────────────────────────────────────────────────────────────────
    # Perpetual promo model — "up to 75% off" banner always showing
    # Current (sale) prices used — RRP appears to be inflated
    # Serving size confirmed as 32g (not 30g)
    {
        "brand": "Bulk",
        "product": "Pure Whey Protein",
        "size": "500g",
        "url": "https://www.bulk.com/uk/products/pure-whey-protein/bpb-wpc8-0000",
        "price": 14.99,
        "servings": 15,
        "protein_per_serving_g": 23,
        "serving_size_g": 32,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "Bulk",
        "product": "Pure Whey Protein",
        "size": "1kg",
        "url": "https://www.bulk.com/uk/products/pure-whey-protein/bpb-wpc8-0000",
        "price": 24.99,
        "servings": 31,
        "protein_per_serving_g": 23,
        "serving_size_g": 32,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "Bulk",
        "product": "Pure Whey Protein",
        "size": "2.5kg",
        "url": "https://www.bulk.com/uk/products/pure-whey-protein/bpb-wpc8-0000",
        "price": 59.99,
        "servings": 78,
        "protein_per_serving_g": 23,
        "serving_size_g": 32,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "Bulk",
        "product": "Pure Whey Protein",
        "size": "5kg",
        "url": "https://www.bulk.com/uk/products/pure-whey-protein/bpb-wpc8-0000",
        "price": 114.99,
        "servings": 156,
        "protein_per_serving_g": 23,
        "serving_size_g": 32,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },

    # ── Applied Nutrition ──────────────────────────────────────────────────────
    # Standard RRP — no subscription model, Shopify store
    # 132g trial size excluded (not comparable)
    # Note: servings listed as 61 for 825g — verify label (expect ~25 at 33g scoop)
    {
        "brand": "Applied Nutrition",
        "product": "Critical Whey",
        "size": "825g",
        "url": "https://appliednutrition.uk/products/critical-whey?variant=55702274310519",
        "price": 29.95,
        "servings": 25,           # ← corrected from 61 (61 servings from 825g at 33g = impossible)
        "protein_per_serving_g": 24,
        "serving_size_g": 33,
        "pricing_model": "standard_rrp",
        "confirmed": False,        # servings need label verification
    },
    {
        "brand": "Applied Nutrition",
        "product": "Critical Whey",
        "size": "2kg",
        "url": "https://appliednutrition.uk/products/critical-whey?variant=55037133029751",
        "price": 59.95,
        "servings": 61,
        "protein_per_serving_g": 24,
        "serving_size_g": 33,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },

    # ── Optimum Nutrition ─────────────────────────────────────────────────────
    # Standard RRP with genuine periodic sales
    # All sizes share one base URL with variant param
    {
        "brand": "Optimum Nutrition",
        "product": "Gold Standard 100% Whey",
        "size": "300g",
        "url": "https://www.optimumnutrition.com/en-gb/products/gold-standard-100-whey-protein-powder-eu?variant=52105832071435",
        "price": 18.50,
        "servings": 10,
        "protein_per_serving_g": 24,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Optimum Nutrition",
        "product": "Gold Standard 100% Whey",
        "size": "450g",
        "url": "https://www.optimumnutrition.com/en-gb/products/gold-standard-100-whey-protein-powder-eu?variant=52105832399115",
        "price": 25.00,
        "servings": 15,
        "protein_per_serving_g": 24,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Optimum Nutrition",
        "product": "Gold Standard 100% Whey",
        "size": "600g",
        "url": "https://www.optimumnutrition.com/en-gb/products/gold-standard-100-whey-protein-powder-eu?variant=52651872256267",
        "price": 30.00,
        "servings": 20,
        "protein_per_serving_g": 24,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Optimum Nutrition",
        "product": "Gold Standard 100% Whey",
        "size": "900g",
        "url": "https://www.optimumnutrition.com/en-gb/products/gold-standard-100-whey-protein-powder-eu?variant=52105832300811",
        "price": 40.00,
        "servings": 30,
        "protein_per_serving_g": 24,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Optimum Nutrition",
        "product": "Gold Standard 100% Whey",
        "size": "2.28kg",
        "url": "https://www.optimumnutrition.com/en-gb/products/gold-standard-100-whey-protein-powder-eu?variant=52105832202507",
        "price": 80.00,
        "servings": 76,
        "protein_per_serving_g": 24,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },

    # ── Kinetica ───────────────────────────────────────────────────────────────
    # Standard RRP — separate URL per size (confirmed)
    {
        "brand": "Kinetica",
        "product": "Whey Protein",
        "size": "300g",
        "url": "https://uk.kineticasports.com/products/whey-protein-powder-vanilla-300g",
        "price": 19.99,
        "servings": 10,
        "protein_per_serving_g": 23,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Kinetica",
        "product": "Whey Protein",
        "size": "1kg",
        "url": "https://uk.kineticasports.com/products/whey-protein-powder-vanilla-1kg",
        "price": 44.99,
        "servings": 33,
        "protein_per_serving_g": 23,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Kinetica",
        "product": "Whey Protein",
        "size": "2.27kg",
        "url": "https://uk.kineticasports.com/products/whey-protein-powder-vanilla-2-27kg",
        "price": 65.99,
        "servings": 76,
        "protein_per_serving_g": 23,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "Kinetica",
        "product": "Whey Protein",
        "size": "4.5kg",
        "url": "https://uk.kineticasports.com/products/whey-protein-powder-vanilla-4-5kg",
        "price": 119.99,
        "servings": 150,
        "protein_per_serving_g": 23,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },

    # ── USN ────────────────────────────────────────────────────────────────────
    # Standard RRP — variant param per size, serving size 34g confirmed
    {
        "brand": "USN",
        "product": "Blue Lab 100% Whey",
        "size": "476g",
        "url": "https://uk.usn.global/products/blue-lab-whey-protein?variant=40937454010427",
        "price": 18.00,
        "servings": 14,
        "protein_per_serving_g": 24,
        "serving_size_g": 34,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "USN",
        "product": "Blue Lab 100% Whey",
        "size": "908g",
        "url": "https://uk.usn.global/products/blue-lab-whey-protein?variant=32385253408827",
        "price": 36.00,
        "servings": 27,
        "protein_per_serving_g": 24,
        "serving_size_g": 34,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
    {
        "brand": "USN",
        "product": "Blue Lab 100% Whey",
        "size": "2kg",
        "url": "https://uk.usn.global/products/blue-lab-whey-protein?variant=32385253965883",
        "price": 67.50,
        "servings": 59,
        "protein_per_serving_g": 24,
        "serving_size_g": 34,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },

    # ── The Protein Works ─────────────────────────────────────────────────────
    # Perpetual promo model — sale prices used (RRP column in sheet)
    # Note: 25g scoop (smaller than 30g industry standard)
    # 4kg servings corrected: 4000g ÷ 25g scoop = 160 servings (not 40)
    {
        "brand": "The Protein Works",
        "product": "Whey Protein 80",
        "size": "500g",
        "url": "https://www.theproteinworks.com/whey-protein-80-concentrate",
        "price": 13.29,
        "servings": 16,
        "protein_per_serving_g": 22,
        "serving_size_g": 25,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "The Protein Works",
        "product": "Whey Protein 80",
        "size": "1kg",
        "url": "https://www.theproteinworks.com/whey-protein-80-concentrate",
        "price": 25.29,
        "servings": 33,
        "protein_per_serving_g": 22,
        "serving_size_g": 25,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "The Protein Works",
        "product": "Whey Protein 80",
        "size": "2kg",
        "url": "https://www.theproteinworks.com/whey-protein-80-concentrate",
        "price": 41.79,
        "servings": 66,
        "protein_per_serving_g": 22,
        "serving_size_g": 25,
        "pricing_model": "perpetual_promo",
        "confirmed": True,
    },
    {
        "brand": "The Protein Works",
        "product": "Whey Protein 80",
        "size": "4kg",
        "url": "https://www.theproteinworks.com/whey-protein-80-concentrate",
        "price": 71.99,
        "servings": 160,           # corrected: 4000g ÷ 25g scoop
        "protein_per_serving_g": 22,
        "serving_size_g": 25,
        "pricing_model": "perpetual_promo",
        "confirmed": False,        # servings corrected — verify from label
    },

    # ── Science in Sport (SIS) ────────────────────────────────────────────────
    # ⚠ WARNING: URLs point to REGO Whey (recovery product, not standard whey)
    # REGO Whey has ~21g protein per serving vs standard whey ~23-24g
    # Prices may not be directly comparable — flag in all reports
    # Confirm whether this is the right product to track
    {
        "brand": "SIS",
        "product": "REGO Whey Powder",
        "size": "450g",
        "url": "https://www.scienceinsport.com/shop-by-need/recovery/rego-whey-powder?sku=131924",
        "price": 25.00,
        "servings": 15,            # 450g ÷ 30g scoop
        "protein_per_serving_g": 21,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": False,        # ⚠ wrong product — needs review
        "flagged": "REGO Whey is a recovery product, not a standard whey. May not be comparable.",
    },
    {
        "brand": "SIS",
        "product": "REGO Whey Powder",
        "size": "1.35kg",
        "url": "https://www.scienceinsport.com/shop-by-need/recovery/rego-whey-powder?sku=131925",
        "price": 60.00,
        "servings": 45,            # 1350g ÷ 30g scoop
        "protein_per_serving_g": 21,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": False,        # ⚠ wrong product — needs review
        "flagged": "REGO Whey is a recovery product, not a standard whey. May not be comparable.",
    },

    # ── Healthspan Elite ──────────────────────────────────────────────────────
    # Standard RRP — only sells 750g, 37.5g scoop, 20 servings confirmed
    # Currently on sale: £33.99 (was £39.99)
    {
        "brand": "Healthspan",
        "product": "Ultimate Whey Protein Blend",
        "size": "750g",
        "url": "https://www.healthspanelite.co.uk/elite-all-blacks-ultimate-whey-protein-blend/",
        "price": 33.99,
        "servings": 20,
        "protein_per_serving_g": 24,
        "serving_size_g": 37.5,
        "pricing_model": "standard_rrp",
        "confirmed": True,
        "on_sale": True,
        "rrp": 39.99,
    },

    # ── Soccer Supplement ─────────────────────────────────────────────────────
    # New formula confirmed: 30g scoop / 22g protein / 33 servings
    # Standard RRP — no subscription model
    {
        "brand": "Soccer Supplement",
        "product": "Whey90",
        "size": "1kg",
        "url": "https://www.soccersupplement.com/products/new-whey-vanilla1kg",
        "price": 41.95,
        "servings": 33,
        "protein_per_serving_g": 22,
        "serving_size_g": 30,
        "pricing_model": "standard_rrp",
        "confirmed": True,
    },
]

ALL_PRODUCTS = YOUR_PRODUCTS + COMPETITOR_PRODUCTS

# Items that need follow-up before next scrape run
FLAGGED_FOR_REVIEW = [
    {
        "brand": "Applied Nutrition",
        "size": "825g",
        "issue": "Servings entered as 61 — impossible at 33g scoop from 825g bag (max ~25). Corrected to 25. Please verify from label.",
    },
    {
        "brand": "The Protein Works",
        "size": "4kg",
        "issue": "Servings entered as 40 — corrected to 160 (4000g ÷ 25g scoop). Please verify from label.",
    },
    {
        "brand": "SIS",
        "size": "all",
        "issue": "URLs point to REGO Whey (recovery product), not standard whey protein. Prices and protein content may not be comparable. Confirm which SIS product to track.",
    },
]

# ── Scraper settings ───────────────────────────────────────────────────────────
SETTINGS = {
    "db_path": "data/prices.db",
    "log_path": "logs/scraper.log",
    "report_dir": "reports/",
    "run_time": "08:00",
    "timezone": "Europe/London",
    "request_delay_seconds": 3,
    "request_timeout_seconds": 20,
    "max_retries": 3,
    # Alert if price moves by >= this % between scrapes
    "price_change_alert_pct": 1.0,
    # Also alert on description changes (catches reformulations, removed promos)
    "desc_change_alert": True,
    # After N days of no price change, classify pricing_model as confirmed perpetual_promo
    "perpetual_promo_confirm_days": 21,
    # Email alerts
    "email_enabled": False,
    "email_from": "alerts@yourdomain.com",
    "email_to": "you@yourdomain.com",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
}
