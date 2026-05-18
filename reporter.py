"""
reporter.py — Generates a daily HTML report with:
  - Colour-coded £/serving (red = cheaper than our cheapest, green = more expensive)
  - Weekly average price-per-serving chart by brand with toggle
"""

import json
import pathlib
from datetime import datetime, timezone, timedelta

from database import get_latest_all_products, get_recent_changes, get_price_history
from config import SETTINGS, YOUR_PRODUCTS


def _your_pps() -> dict:
    rows = get_latest_all_products()
    your_brand = YOUR_PRODUCTS[0]["brand"]
    return {
        r["size"]: r["price_per_srv"]
        for r in rows
        if r["brand"] == your_brand and r["price_per_srv"]
    }


def _diff_label(pps: float, your_pps_map: dict, size: str) -> str:
    ref = None
    if any(s in size for s in ["900g", "1kg", "750g", "825g", "476g", "450g", "300g", "500g"]):
        ref = your_pps_map.get("900g")
    elif any(s in size for s in ["1.8kg", "2kg", "2.5kg", "2.27kg", "2.28kg", "4kg", "4.5kg", "5kg", "1.35kg"]):
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


def _build_weekly_chart_data(rows: list) -> str:
    """
    Build price-per-serving chart data per brand.
    Uses daily data for the last 14 days when history is short,
    falling back to the latest known price when no history exists.
    """
    brands = sorted(set(r["brand"] for r in rows))
    now = datetime.now(timezone.utc)

    # Build daily labels for last 14 days
    days = []
    for i in range(13, -1, -1):
        d = now - timedelta(days=i)
        days.append({"label": d.strftime("%-d %b"), "date": d})

    brand_data = {}
    for brand in brands:
        brand_rows = [r for r in rows if r["brand"] == brand]

        # Get latest pps as fallback
        latest_pps_vals = [r["price_per_srv"] for r in brand_rows if r["price_per_srv"]]
        fallback_pps = round(sum(latest_pps_vals) / len(latest_pps_vals), 3) if latest_pps_vals else None

        daily_avgs = []
        for day_info in days:
            day_start = day_info["date"].replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_prices = []

            for r in brand_rows:
                hist = get_price_history(r["brand"], r["product"], r["size"], days=20)
                for h in hist:
                    try:
                        scraped = datetime.fromisoformat(h["scraped_at"].replace("Z", "+00:00"))
                        if scraped.tzinfo is None:
                            scraped = scraped.replace(tzinfo=timezone.utc)
                    except Exception:
                        continue
                    if day_start <= scraped < day_end and h["price_per_srv"]:
                        day_prices.append(h["price_per_srv"])

            if day_prices:
                daily_avgs.append(round(sum(day_prices) / len(day_prices), 3))
            else:
                daily_avgs.append(fallback_pps)

        brand_data[brand] = daily_avgs

    return json.dumps({
        "labels": [d["label"] for d in days],
        "brands": brands,
        "data": brand_data,
    })


def generate_report() -> str:
    rows = get_latest_all_products()
    changes = get_recent_changes(days=7)
    your_pps = _your_pps()

    now = datetime.now(timezone.utc)
    ts = now.strftime("%d %b %Y %H:%M UTC")

    your_brand = YOUR_PRODUCTS[0]["brand"]
    rivals = [r for r in rows if r["brand"] != your_brand]

    all_pps = [r["price_per_srv"] for r in rivals if r["price_per_srv"]]
    avg_pps = sum(all_pps) / len(all_pps) if all_pps else 0
    min_rival_pps = min(all_pps) if all_pps else 0

    your_small_pps = your_pps.get("900g") or 0
    your_large_pps = your_pps.get("1.8kg") or 0

    # Our cheapest pps across all sizes
    our_min_pps = min(v for v in your_pps.values() if v) if your_pps else 0

    chart_data = _build_weekly_chart_data(rows)

    BRAND_COLOURS = {
        "Nutrition X": "#185FA5",
        "Myprotein": "#D85A30",
        "Bulk": "#1D9E75",
        "Applied Nutrition": "#BA7517",
        "Optimum Nutrition": "#7F77DD",
        "Kinetica": "#0F6E56",
        "USN": "#A32D2D",
        "The Protein Works": "#639922",
        "SIS": "#533AB7",
        "Healthspan": "#854F0B",
        "Soccer Supplement": "#5F5E5A",
    }

    def pps_cell(r):
        if not r["price_per_srv"]:
            return '<td class="na">N/A</td>'
        p = r["price_per_srv"]
        if r["brand"] == your_brand:
            return f'<td class="pps-you">£{p:.3f}</td>'
        if p < our_min_pps:
            return f'<td class="pps-cheaper">£{p:.3f}</td>'
        else:
            return f'<td class="pps-dearer">£{p:.3f}</td>'

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
      <td>{'£' + c['old_value'] if c['old_value'] and c['change_type'] in ('price','sale_started','sale_ended') else (c['old_value'] or '')[:60]}</td>
      <td>{'£' + c['new_value'] if c['new_value'] and c['change_type'] in ('price','sale_started','sale_ended') else (c['new_value'] or '')[:60]}</td>
    </tr>""" for c in changes) if changes else "<tr><td colspan='6' style='color:#888;text-align:center'>No changes detected in the last 7 days</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Big Whey Price Intelligence — {ts}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #f5f5f3; color: #1a1a1a; font-size: 14px; }}
  .wrap {{ max-width: 1300px; margin: 0 auto; padding: 24px 16px; }}
  h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
  .sub {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }}
  .metric {{ background: #fff; border-radius: 10px; padding: 16px; border: 1px solid #e5e5e5; }}
  .metric .label {{ font-size: 12px; color: #888; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; }}
  .metric .value {{ font-size: 26px; font-weight: 600; }}
  .metric .hint {{ font-size: 12px; color: #666; margin-top: 4px; }}
  .hint.good {{ color: #2d7a0f; }} .hint.warn {{ color: #854F0B; }}
  h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; margin-top: 8px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden; border: 1px solid #e5e5e5; margin-bottom: 28px; }}
  th {{ background: #f8f8f6; padding: 10px 12px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: #666; border-bottom: 1px solid #e5e5e5; white-space: nowrap; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0ee; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.own {{ background: #f0f5ff; }}
  tr.own strong {{ color: #185FA5; }}
  /* Price per serving colour coding */
  td.pps-you   {{ font-weight: 700; color: #185FA5; }}
  td.pps-cheaper {{ font-weight: 600; color: #a32d2d; background: #ffeded; }}
  td.pps-dearer  {{ font-weight: 600; color: #2d7a0f; background: #edf7ed; }}
  td.na {{ color: #bbb; }}
  td.diff {{ font-size: 12px; color: #666; }}
  td.ts {{ font-size: 11px; color: #bbb; }}
  td.sale {{ color: #2d7a0f; font-size: 12px; font-weight: 500; }}
  .legend-note {{ font-size: 12px; margin-bottom: 12px; display: flex; gap: 16px; flex-wrap: wrap; }}
  .legend-note span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .swatch {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}
  .badge-rise {{ background: #ffeded; color: #a32d2d; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .badge-drop {{ background: #edf7ed; color: #2d7a0f; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .badge-desc {{ background: #fff8e1; color: #854F0B; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .badge-warn {{ background: #fff3cd; color: #664d03; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .chart-card {{ background: #fff; border-radius: 10px; border: 1px solid #e5e5e5; padding: 20px; margin-bottom: 28px; }}
  .chart-controls {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }}
  .brand-btn {{ font-size: 12px; padding: 4px 12px; border-radius: 99px; border: 2px solid transparent; cursor: pointer; font-weight: 500; opacity: 0.45; transition: opacity .15s; }}
  .brand-btn.active {{ opacity: 1; }}
  .chart-wrap {{ position: relative; height: 320px; }}
  .footer {{ font-size: 12px; color: #aaa; text-align: center; margin-top: 24px; }}
  @media (max-width: 700px) {{ .metrics {{ grid-template-columns: 1fr 1fr; }} }}
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
      <div class="hint">£{our_min_pps:.2f} cheapest across your sizes</div>
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
    <thead><tr><th>Detected</th><th>Brand</th><th>Size</th><th>Type</th><th>Previous</th><th>New</th></tr></thead>
    <tbody>{changes_html}</tbody>
  </table>

  <h2>Weekly average £/serving by brand</h2>
  <div class="chart-card">
    <div class="chart-controls" id="brand-btns"></div>
    <div class="chart-wrap"><canvas id="weeklyChart"></canvas></div>
  </div>

  <h2>Live price comparison</h2>
  <div class="legend-note">
    <span><span class="swatch" style="background:#185FA5"></span> Your products (blue)</span>
    <span><span class="swatch" style="background:#edf7ed;border:1px solid #2d7a0f"></span> <b style="color:#2d7a0f">Green</b> = cheaper than your lowest £/serving (good — rivals undercut you)</span>
    <span><span class="swatch" style="background:#ffeded;border:1px solid #a32d2d"></span> <b style="color:#a32d2d">Red</b> = more expensive than your lowest (good — you're the better value)</span>
  </div>
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

  <p class="footer">Whey Tracker · nutritionx.co.uk · Prices scraped from brand websites.</p>
</div>

<script>
const CHART_DATA = {chart_data};
const COLOURS = {json.dumps(BRAND_COLOURS)};

// Build datasets
const datasets = CHART_DATA.brands.map(brand => ({{
  label: brand,
  data: CHART_DATA.data[brand].map(v => v === null || v === undefined ? NaN : v),
  borderColor: COLOURS[brand] || '#888',
  backgroundColor: (COLOURS[brand] || '#888') + '22',
  borderWidth: brand === 'Nutrition X' ? 3 : 1.5,
  pointRadius: 3,
  tension: 0.3,
  hidden: false,
  spanGaps: true,
}}));

const chart = new Chart(document.getElementById('weeklyChart'), {{
  type: 'line',
  data: {{ labels: CHART_DATA.labels, datasets }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: c => ` ${{c.dataset.label}}: £${{c.parsed.y?.toFixed(3) || 'N/A'}}` }} }}
    }},
    scales: {{
      x: {{ ticks: {{ color: '#888', font: {{ size: 11 }} }}, grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
      y: {{ ticks: {{ callback: v => '£' + v.toFixed(2), color: '#888', font: {{ size: 11 }} }}, grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
    }}
  }}
}});

// Brand toggle buttons
const btnContainer = document.getElementById('brand-btns');
CHART_DATA.brands.forEach((brand, i) => {{
  const btn = document.createElement('button');
  btn.className = 'brand-btn active';
  btn.textContent = brand;
  btn.style.borderColor = COLOURS[brand] || '#888';
  btn.style.color = COLOURS[brand] || '#888';
  btn.style.background = (COLOURS[brand] || '#888') + '15';
  btn.onclick = () => {{
    const ds = chart.data.datasets[i];
    ds.hidden = !ds.hidden;
    btn.classList.toggle('active', !ds.hidden);
    chart.update();
  }};
  btnContainer.appendChild(btn);
}});
</script>
</body>
</html>"""

    pathlib.Path(SETTINGS["report_dir"]).mkdir(parents=True, exist_ok=True)
    fname = now.strftime("report_%Y-%m-%d.html")
    fpath = pathlib.Path(SETTINGS["report_dir"]) / fname
    fpath.write_text(html, encoding="utf-8")
    (pathlib.Path(SETTINGS["report_dir"]) / "latest.html").write_text(html, encoding="utf-8")
    print(f"Report written: {fpath}")
    return str(fpath)


def print_summary():
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
        elif c["change_type"] == "sale_started":
            print(f"  🏷 SALE  {c['brand']} {c['size']}: sale started  [{ts}]")
        elif c["change_type"] == "sale_ended":
            print(f"  🏷 SALE  {c['brand']} {c['size']}: sale ended  [{ts}]")
        elif c["change_type"] == "description":
            print(f"  📝 DESC  {c['brand']} {c['size']}: description changed  [{ts}]")
        else:
            print(f"  ⚠ MISS   {c['brand']} {c['size']}: price no longer found  [{ts}]")
    print()


if __name__ == "__main__":
    generate_report()
    print_summary()