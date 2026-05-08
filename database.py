"""
database.py — SQLite storage for price snapshots, change history, and alerts.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from config import SETTINGS


def get_conn():
    Path(SETTINGS["db_path"]).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SETTINGS["db_path"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Safe to run on existing DBs — migrates columns."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            scraped_at             TEXT NOT NULL,
            brand                  TEXT NOT NULL,
            product                TEXT NOT NULL,
            size                   TEXT NOT NULL,
            url                    TEXT NOT NULL,
            price                  REAL,
            currency               TEXT DEFAULT 'GBP',
            servings               INTEGER NOT NULL,
            protein_per_srv        REAL NOT NULL,
            serving_size_g         REAL NOT NULL,
            price_per_srv          REAL,
            price_per_100g_protein REAL,
            compare_at_price       REAL,
            on_sale                INTEGER DEFAULT 0,
            sale_saving_pct        REAL,
            description_hash       TEXT,
            description_raw        TEXT,
            scrape_ok              INTEGER DEFAULT 1,
            error_msg              TEXT
        );

        CREATE TABLE IF NOT EXISTS changes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            detected_at     TEXT NOT NULL,
            brand           TEXT NOT NULL,
            product         TEXT NOT NULL,
            size            TEXT NOT NULL,
            change_type     TEXT NOT NULL,
            old_value       TEXT,
            new_value       TEXT,
            pct_change      REAL,
            alerted         INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_brand ON snapshots(brand, product, size);
        CREATE INDEX IF NOT EXISTS idx_snapshots_date  ON snapshots(scraped_at);
        CREATE INDEX IF NOT EXISTS idx_changes_date    ON changes(detected_at);
        """)

        # Migrate existing DB — add new columns if they don't exist yet
        existing = [r[1] for r in conn.execute("PRAGMA table_info(snapshots)").fetchall()]
        for col, definition in [
            ("compare_at_price", "REAL"),
            ("on_sale",          "INTEGER DEFAULT 0"),
            ("sale_saving_pct",  "REAL"),
        ]:
            if col not in existing:
                conn.execute(f"ALTER TABLE snapshots ADD COLUMN {col} {definition}")

    print("Database initialised.")


def save_snapshot(row: dict):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO snapshots
          (scraped_at, brand, product, size, url, price, currency,
           servings, protein_per_srv, serving_size_g,
           price_per_srv, price_per_100g_protein,
           compare_at_price, on_sale, sale_saving_pct,
           description_hash, description_raw, scrape_ok, error_msg)
        VALUES
          (:scraped_at, :brand, :product, :size, :url, :price, :currency,
           :servings, :protein_per_srv, :serving_size_g,
           :price_per_srv, :price_per_100g_protein,
           :compare_at_price, :on_sale, :sale_saving_pct,
           :description_hash, :description_raw, :scrape_ok, :error_msg)
        """, row)


def save_change(row: dict):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO changes
          (detected_at, brand, product, size, change_type, old_value, new_value, pct_change)
        VALUES
          (:detected_at, :brand, :product, :size, :change_type, :old_value, :new_value, :pct_change)
        """, row)


def get_last_snapshot(brand: str, product: str, size: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("""
        SELECT * FROM snapshots
        WHERE brand=? AND product=? AND size=? AND scrape_ok=1
        ORDER BY scraped_at DESC LIMIT 1
        """, (brand, product, size)).fetchone()
        return dict(row) if row else None


def get_price_history(brand: str, product: str, size: str, days: int = 90) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT scraped_at, price, price_per_srv, on_sale, compare_at_price
        FROM snapshots
        WHERE brand=? AND product=? AND size=? AND scrape_ok=1
          AND scraped_at >= datetime('now', ?)
        ORDER BY scraped_at ASC
        """, (brand, product, size, f"-{days} days")).fetchall()
        return [dict(r) for r in rows]


def get_recent_changes(days: int = 7) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT * FROM changes
        WHERE detected_at >= datetime('now', ?)
        ORDER BY detected_at DESC
        """, (f"-{days} days",)).fetchall()
        return [dict(r) for r in rows]


def get_latest_all_products() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT s.*
        FROM snapshots s
        INNER JOIN (
            SELECT brand, product, size, MAX(scraped_at) AS max_at
            FROM snapshots WHERE scrape_ok=1
            GROUP BY brand, product, size
        ) latest ON s.brand=latest.brand
                        AND s.product=latest.product
                        AND s.size=latest.size
                        AND s.scraped_at=latest.max_at
        ORDER BY s.brand, s.size
        """).fetchall()
        return [dict(r) for r in rows]
