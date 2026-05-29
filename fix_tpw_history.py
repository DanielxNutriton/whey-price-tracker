"""
fix_tpw_history.py — One-shot script to correct bad Protein Works snapshots.

On 2026-05-26 the size-button click wasn't working, so all 4 sizes were
scraped as £14.29 (the default page price). The correct prices at that time
are taken from the verified May 27 targeted test run.

Run once locally after pulling the latest DB from GitHub, then push the result.
"""

import sqlite3
from config import SETTINGS

# Rows where size click failed on GitHub Actions (Linux) — default page price
# £13.29 returned for all sizes instead of per-size price.
# IDs confirmed from DB inspection on 2026-05-29.
BAD_SNAPSHOT_IDS = {
    # May 27 12:59 scheduled run (Linux Playwright — size click failed)
    1242: {"size": "1kg",  "price": 25.29, "servings": 33,  "protein_per_serving_g": 22},
    1243: {"size": "2kg",  "price": 41.79, "servings": 66,  "protein_per_serving_g": 22},
    1244: {"size": "4kg",  "price": 71.99, "servings": 160, "protein_per_serving_g": 22},
    # May 28 11:39 scheduled run (same bug)
    1273: {"size": "1kg",  "price": 25.29, "servings": 33,  "protein_per_serving_g": 22},
    1274: {"size": "2kg",  "price": 41.79, "servings": 66,  "protein_per_serving_g": 22},
    1275: {"size": "4kg",  "price": 71.99, "servings": 160, "protein_per_serving_g": 22},
}

# False price-drop alerts logged when the bad snapshots compared against correct prior prices
FALSE_CHANGE_IDS = [78, 79, 80]


def fix():
    conn = sqlite3.connect(SETTINGS["db_path"])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f"Correcting {len(BAD_SNAPSHOT_IDS)} bad snapshot(s):\n")

    for row_id, c in BAD_SNAPSHOT_IDS.items():
        price = c["price"]
        pps = round(price / c["servings"], 4)
        p100 = round(price / (c["servings"] * c["protein_per_serving_g"] / 100), 2)

        cur.execute("""
            UPDATE snapshots
            SET price                  = ?,
                price_per_srv          = ?,
                price_per_100g_protein = ?,
                scrape_ok              = 1,
                error_msg              = NULL
            WHERE id = ?
        """, (price, pps, p100, row_id))

        if cur.rowcount:
            print(f"  Fixed id={row_id}  {c['size']}  → £{price}")
        else:
            print(f"  SKIP id={row_id} — row not found (already fixed?)")

    # Remove false price-drop alerts
    placeholders = ",".join("?" * len(FALSE_CHANGE_IDS))
    cur.execute(f"DELETE FROM changes WHERE id IN ({placeholders})", FALSE_CHANGE_IDS)
    print(f"\n  Removed {cur.rowcount} false price-change alert(s) from changes table.")

    conn.commit()
    conn.close()
    print("\nDone. Commit and push data/prices.db to update the production database.")


if __name__ == "__main__":
    fix()
