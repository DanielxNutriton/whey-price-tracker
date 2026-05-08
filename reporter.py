"""
reporter.py — Generates a daily HTML report and plain-text change summary.

Run after scraper.py or call generate_report() directly.
"""

import json
import pathlib
from datetime import datetime, timezone

from database import get_latest_all_products, get_recent_changes
from config import SETTINGS, YOUR_PRODUCTS


def _your_pps() -> dict:
    """Return your brand's price-per-serving keyed by size for comparison."""
    rows = get_latest_all_products()
    your_brand = YOUR_PRODUCTS[0]["brand"]
    return {
        r["size"]: r["price_per_srv"]
        for r in rows
        if r["brand"] == your_brand and r["price_per_srv"]
    }


def _diff_label(pps: float, your_pps_map: dict, size: str) -> str:
    """Human-readable comparison vs nearest your product size."""
    # Find best matching your size
    ref = None
    if "900g" in size or "1kg" in size or "750g" in size or "1.2kg" in size:
        ref = your_pps_map.get("900g")
    elif "1.8kg" in size or "2kg" in size or "2.5kg" in size or "2.27kg" in size:
        ref = your_pps_map.get("1.8kg")

    if ref is None or pps is None:
        return "—"

    diff = pps - ref
    if abs(diff) < 0.005:
        return "≈ same"
    elif diff > 0:
        return f"+£{diff:.2f} dearer/srv"
    else:
        return f"£{abs(diff):.2f} cheaper/srv"


def generate_report() -> str:
    """Generate HTML report. Returns file path."""
    rows = get_latest_all_products()
    changes = get_recent_changes(days=7)
    your_pps = _your_pps()

    now = datetime.now(timezone.utc)
    ts = now.strftime("%d %b %Y %H:%M UTC")

    your_brand = YOUR_PRODUCTS[0]["brand"]
    rivals = [r for r in rows if r["brand"] != your_brand]
    yours = [r for r in rows if r["brand"] == your_brand]

    all_pps = [r["price_per_srv"] for r in rivals if r["price_per_srv"]]
    avg_pps = sum(all_pps) / len(all_pps) if all_pps else 0
    min_pps = min(all_pps) if all_pps else 0
    max_pps = max(all_pps) if all_pps else 0

    your_small_pps = your_pps.get("900g") or 0
    your_large_pps = your_pps.get("1.8kg") or 0

    def pps_cell(r):
        if not r["price_per_srv"]:
            return '<td class="na">N/A</td>'
        p = r["price_per_srv"]
        style = ""
        if p == min_pps and r["brand"] != your_brand:
            style = ' class="best"'
        elif p > max_pps * 0.9 and r["brand"] != your_brand:
            style = ' class="high"'
        return f'<td{style}>£{p:.3f}</td>'

    def sale_cell(r):
        if r.get("on_sale") and r.get("compare_at_price") and r.get("price"):
            saving = r.get("sale_saving_pct") or 0
            return f'<td class="sale">🏷 was £{r["compare_at_price"]:.2f} ({saving:.0f}% off)</td>'
        return '<td class="na">—</td>'

    def change_badge(change):
        ct = change["change_type"]
        if ct == "price":
            pct = change["pct_change"] or 0
            cls = "badge-rise" if pct > 0 else "badge-drop"
            sign = "▲" if pct > 0 else "▼"
            return f'<span class="{cls}">{sign} {abs(pct):.1f}%</span>'
        elif ct == "description":
            return '<span class="badge-desc">📝 description</span>'
        elif ct == "sale_started":
            pct = abs(change["pct_change"] or 0)
            return f'<span class="badge-drop">🏷 sale {pct:.0f}% off</span>'
        elif ct == "sale_ended":
            return '<span class="badge-rise">🏷 sale ended</span>'
        return '<span class="badge-warn">⚠ unavailable</span>'

    rows_html = "".join(f"""
    <tr class="{'own' if r['brand'] == your_brand else ''}">
      <td><strong>{r['brand']}</strong></td>
      <td>{r['product']}</td>
      <td>{r['size']}</td>
      <td>{'£' + f"{r['price']:.2f}" if r['price'] else 'N/A'}</td>
      <td>{r['servings']}</td>
      <td>{r['protein_per_srv']}g</td>
      {pps_cell(r)}
      <td>{'£' + f"{r['price_per_100g_protein']:.2f}" if r['price_per_100g_protein'] else 'N/A'}</td>
      {sale_cell(r)}
      <td class="diff">{_diff_label(r['price_per_srv'], your_pps, r['size'])}</td>
      <td class="ts">{r['scraped_at'][:10]}</td>
    </tr>""" for r in rows)

    changes_html = "".join(f"""
    <tr>
      <td>{c['detected_at'][:16].replace('T',' ')}</td>
      <td>{c['brand']}</td>
      <td>{c['size']}</td>
      <td>{change_badge(c)}</td>
      <td>{'£' + c['old_value'] if c['old_value'] and c['change_type'] == 'price' else (c['old_value'] or '')[:60]}</td>
      <td>{'£' + c['new_value'] if c['new_value'] and c['change_type'] == 'price' else (c['new_value'] or '')[:60]}</td>
    </tr>""" for c in changes) if changes else "<tr><td colspan='6' style='color:#888;text-align:center'>No changes detected in the last 7 days</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Big Whey Price Intelligence — {ts}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #f5f5f3; color: #1a1a1a; font-size: 14px; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px 16px; }}
  h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
  .sub {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }}
  .metric {{ background: #fff; border-radius: 10px; padding: 16px; border: 1px solid #e5e5e5; }}
  .metric .label {{ font-size: 12px; color: #888; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; }}
  .metric .value {{ font-size: 26px; font-weight: 600; }}
  .metric .hint {{ font-size: 12px; color: #666; margin-top: 4px; }}
  .hint.good {{ color: #2d7a0f; }}
  .hint.warn {{ color: #854F0B; }}
  h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden; border: 1px solid #e5e5e5; margin-bottom: 28px; }}
  th {{ background: #f8f8f6; padding: 10px 12px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: #666; border-bottom: 1px solid #e5e5e5; }}
  td {{ padding: 11px 12px; border-bottom: 1px solid #f0f0ee; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.own {{ background: #f0f5ff; }}
  tr.own strong {{ color: #185FA5; }}
  td.best {{ color: #2d7a0f; font-weight: 600; }}
  td.high {{ color: #a32d2d; }}
  td.na {{ color: #bbb; }}
  td.diff {{ font-size: 12px; color: #666; }}
  td.ts {{ font-size: 11px; color: #bbb; }}
  .badge-rise {{ background: #ffeded; color: #a32d2d; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .badge-drop {{ background: #edf7ed; color: #2d7a0f; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .badge-desc {{ background: #fff8e1; color: #854F0B; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .badge-warn {{ background: #fff3cd; color: #664d03; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .footer {{ font-size: 12px; color: #aaa; text-align: center; margin-top: 24px; }}
  @media (max-width: 700px) {{
    .metrics {{ grid-template-columns: 1fr 1fr; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Big Whey — Competitor Price Intelligence</h1>
  <p class="sub">Generated {ts} · Prices scraped from brand websites · 30g serving baseline</p>

  <div class="metrics">
    <div class="metric">
      <div class="label">Your 900g £/serving</div>
      <div class="value">{'£' + f'{your_small_pps:.2f}' if your_small_pps else 'N/A'}</div>
      <div class="hint">{'£' + f'{your_pps.get("900g", 0) * (list(filter(lambda r: r["brand"] == your_brand and r["size"] == "900g", rows)) or [{}])[0].get("servings", 30):.2f}' if your_small_pps else ''}</div>
    </div>
    <div class="metric">
      <div class="label">Your 1.8kg £/serving</div>
      <div class="value">{'£' + f'{your_large_pps:.2f}' if your_large_pps else 'N/A'}</div>
    </div>
    <div class="metric">
      <div class="label">Rival avg £/serving</div>
      <div class="value">£{avg_pps:.2f}</div>
      <div class="hint {'good' if your_small_pps < avg_pps else 'warn'}">
        {'✓ Your 900g is cheaper' if your_small_pps and your_small_pps < avg_pps else '↑ Your 900g is above avg'}
      </div>
    </div>
    <div class="metric">
      <div class="label">Changes (7 days)</div>
      <div class="value">{len(changes)}</div>
      <div class="hint {'warn' if changes else ''}">{len([c for c in changes if c['change_type'] == 'price'])} price · {len([c for c in changes if c['change_type'] == 'description'])} description</div>
    </div>
  </div>

  <h2>Recent alerts (last 7 days)</h2>
  <table>
    <thead>
      <tr>
        <th>Detected</th><th>Brand</th><th>Size</th><th>Type</th><th>Previous</th><th>New</th>
      </tr>
    </thead>
    <tbody>{changes_html}</tbody>
  </table>

  <h2>Live price comparison</h2>
  <table>
    <thead>
      <tr>
        <th>Brand</th><th>Product</th><th>Size</th><th>Price</th>
        <th>Servings</th><th>Protein/srv</th><th>£/serving</th>
        <th>£/100g protein</th><th>On sale?</th><th>vs you</th><th>Last scraped</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>

  <p class="footer">
    Whey Tracker · nutritionx.co.uk · Prices are as scraped and may differ from current live prices.
    Servings marked with * are estimated from bag weight ÷ serving size.
  </p>
</div>
</body>
</html>"""

    # Write file
    pathlib.Path(SETTINGS["report_dir"]).mkdir(parents=True, exist_ok=True)
    fname = now.strftime("report_%Y-%m-%d.html")
    fpath = pathlib.Path(SETTINGS["report_dir"]) / fname
    fpath.write_text(html, encoding="utf-8")
    # Also write latest.html for easy bookmarking
    (pathlib.Path(SETTINGS["report_dir"]) / "latest.html").write_text(html, encoding="utf-8")

    print(f"Report written: {fpath}")
    return str(fpath)


def print_summary():
    """Print a quick change summary to stdout — useful for cron email."""
    changes = get_recent_changes(days=1)
    if not changes:
        print("No changes detected in the last 24 hours.")
        return

    print(f"\n{'='*55}")
    print(f"  BIG WHEY TRACKER — {len(changes)} change(s) detected today")
    print(f"{'='*55}")
    for c in changes:
        ts = c["detected_at"][:16].replace("T", " ")
        if c["change_type"] == "price":
            pct = c["pct_change"] or 0
            arrow = "▲ RISE" if pct > 0 else "▼ DROP"
            print(f"  {arrow} {c['brand']} {c['size']}: £{c['old_value']} → £{c['new_value']} ({pct:+.1f}%)  [{ts}]")
        elif c["change_type"] == "description":
            print(f"  📝 DESC  {c['brand']} {c['size']}: description changed  [{ts}]")
        else:
            print(f"  ⚠ MISS   {c['brand']} {c['size']}: price no longer found  [{ts}]")
    print()


if __name__ == "__main__":
    generate_report()
    print_summary()
