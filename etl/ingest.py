"""
ingest.py
Reads raw CSV files from data/raw/ and loads them into the
SQLite analytics database as bronze-layer tables.
"""

import os
import sqlite3
import pandas as pd

RAW_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
DB_PATH  = os.path.join(os.path.dirname(__file__), "..", "data", "analytics.db")


TABLES = {
    "raw_users":       "users.csv",
    "raw_user_events": "user_events.csv",
    "raw_sales":       "sales.csv",
    "raw_marketing":   "marketing.csv",
}


def ingest_raw(verbose: bool = True) -> None:
    """Load all raw CSV files into SQLite bronze tables."""
    conn = sqlite3.connect(DB_PATH)
    for table, filename in TABLES.items():
        path = os.path.join(RAW_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Raw file not found: {path}\n"
                "Run `python etl/generate_data.py` first."
            )
        df = pd.read_csv(path, low_memory=False)
        df.to_sql(table, conn, if_exists="replace", index=False)
        if verbose:
            print(f"  ✓ Ingested {len(df):>8,} rows → {table}")
    conn.close()


if __name__ == "__main__":
    print("📥 Ingesting raw data into bronze layer …")
    ingest_raw()
    print("✅ Done.")
