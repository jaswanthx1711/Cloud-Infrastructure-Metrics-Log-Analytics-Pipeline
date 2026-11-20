"""
export_for_bi.py — Export gold-layer tables for Tableau / Power BI

Exports:
  data/bi_exports/
    ├── agg_channel_kpis.csv
    ├── fct_orders.csv
    ├── fct_events.csv
    ├── dim_users.csv
    ├── analytics_export.xlsx   (all sheets in one workbook)
    └── cloud_metrics.tds       (Tableau Data Source XML)

Usage:
    python etl/export_for_bi.py
"""

import os
import sqlite3
import pandas as pd
import textwrap
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────
REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH    = os.path.join(REPO_ROOT, "data", "analytics.db")
BI_DIR     = os.path.join(REPO_ROOT, "data", "bi_exports")
os.makedirs(BI_DIR, exist_ok=True)

# ── Tables to export ─────────────────────────────────────────────────────
EXPORTS = {
    "agg_channel_kpis": "SELECT * FROM agg_channel_kpis",
    "fct_orders":       "SELECT * FROM fct_orders",
    "fct_events":       "SELECT * FROM fct_events LIMIT 200000",
    "dim_users":        "SELECT * FROM dim_users",
    "funnel_summary": """
        SELECT stage, stage_order,
               COUNT(DISTINCT user_id) AS users,
               ROUND(100.0*COUNT(DISTINCT user_id)/MAX(COUNT(DISTINCT user_id)) OVER(),1) AS pct_of_top
        FROM fct_events GROUP BY stage,stage_order ORDER BY stage_order
    """,
    "monthly_revenue": """
        SELECT month, channel,
               SUM(net_revenue)         AS revenue,
               COUNT(DISTINCT order_id) AS orders,
               COUNT(DISTINCT user_id)  AS buyers
        FROM fct_orders WHERE status='completed'
        GROUP BY month,channel ORDER BY month
    """,
    "rfm_segments": """
        WITH rfm_raw AS (
            SELECT user_id,
                   JULIANDAY('2026-01-01')-JULIANDAY(MAX(order_date)) AS recency,
                   COUNT(DISTINCT order_id)  AS frequency,
                   SUM(net_revenue)          AS monetary
            FROM fct_orders WHERE status='completed' GROUP BY user_id),
        scored AS (
            SELECT *, NTILE(4) OVER(ORDER BY recency DESC) r,
                      NTILE(4) OVER(ORDER BY frequency)    f,
                      NTILE(4) OVER(ORDER BY monetary)     m FROM rfm_raw),
        segs AS (
            SELECT user_id, recency, frequency, monetary,
                   CASE
                       WHEN r>=3 AND f>=3 AND m>=3 THEN 'Champions'
                       WHEN r>=3 AND f>=2          THEN 'Loyal'
                       WHEN r>=3 AND f=1           THEN 'Recent'
                       WHEN r=2  AND f>=2          THEN 'At Risk'
                       WHEN r=1  AND f>=2          THEN 'Cant Lose'
                       ELSE 'Low Value' END AS segment FROM scored)
        SELECT * FROM segs
    """,
}


def export_csvs(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Export each query to a CSV file and return DataFrames."""
    frames = {}
    for name, sql in EXPORTS.items():
        df = pd.read_sql(sql, conn)
        path = os.path.join(BI_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        frames[name] = df
        print(f"  ✓  {name}.csv  ({len(df):,} rows)")
    return frames


def export_excel(frames: dict[str, pd.DataFrame]) -> None:
    """Write all DataFrames into a single Excel workbook (one sheet each)."""
    path = os.path.join(BI_DIR, "analytics_export.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in frames.items():
            # Excel sheet names max 31 chars
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    print(f"  ✓  analytics_export.xlsx  ({len(frames)} sheets)")


def write_tableau_datasource() -> None:
    """
    Generate a Tableau Data Source (.tds) XML file that points to the
    exported CSVs.  Open this file in Tableau Desktop to connect instantly.
    """
    csv_dir = BI_DIR.replace("\\", "/")
    tds_content = textwrap.dedent(f"""\
    <?xml version='1.0' encoding='utf-8' ?>
    <datasource name='Cloud Metrics Analytics'
                version='18.1'
                xmlns:user='http://www.tableausoftware.com/xml/user'>

      <!-- ── agg_channel_kpis ────────────────────────────── -->
      <connection class='textscan' directory='{csv_dir}'
                  filename='agg_channel_kpis.csv' port='' server=''>
        <relation name='agg_channel_kpis' table='agg_channel_kpis' type='text' />
      </connection>

      <!-- ── fct_orders ─────────────────────────────────── -->
      <connection class='textscan' directory='{csv_dir}'
                  filename='fct_orders.csv' port='' server=''>
        <relation name='fct_orders' table='fct_orders' type='text' />
      </connection>

      <!-- ── fct_events ─────────────────────────────────── -->
      <connection class='textscan' directory='{csv_dir}'
                  filename='fct_events.csv' port='' server=''>
        <relation name='fct_events' table='fct_events' type='text' />
      </connection>

      <!-- ── dim_users ──────────────────────────────────── -->
      <connection class='textscan' directory='{csv_dir}'
                  filename='dim_users.csv' port='' server=''>
        <relation name='dim_users' table='dim_users' type='text' />
      </connection>

      <!-- ── Calculated fields ──────────────────────────── -->
      <column caption='CVR (Calculated)' datatype='real' name='[CVR]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='[converters]/[visitors]' />
      </column>
      <column caption='ROAS (Calculated)' datatype='real' name='[ROAS]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='[total_revenue]/[total_spend]' />
      </column>

    </datasource>
    """)
    path = os.path.join(BI_DIR, "cloud_metrics.tds")
    with open(path, "w") as f:
        f.write(tds_content)
    print(f"  ✓  cloud_metrics.tds  (Tableau Data Source)")


def write_powerbi_instructions() -> None:
    """Write a Power BI connection guide."""
    guide = textwrap.dedent(f"""\
    # Power BI — Connection Guide
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

    ## Option 1: Connect via CSV Files (Recommended for local use)

    1. Open **Power BI Desktop**
    2. Click **Get Data → Text/CSV**
    3. Import each file from:
       `{BI_DIR}/`
       - agg_channel_kpis.csv
       - fct_orders.csv
       - fct_events.csv
       - dim_users.csv
       - monthly_revenue.csv
       - rfm_segments.csv
    4. In the **Model** view, create relationships:
       - `dim_users[user_id]` → `fct_orders[user_id]`
       - `dim_users[user_id]` → `fct_events[user_id]`

    ## Option 2: Connect via Excel Workbook

    1. Open **Power BI Desktop**
    2. Click **Get Data → Excel Workbook**
    3. Select: `{BI_DIR}/analytics_export.xlsx`
    4. Import all sheets

    ## Recommended DAX Measures

    ```dax
    CVR = DIVIDE([Total Converters], [Total Visitors])

    ROAS = DIVIDE([Total Revenue], [Total Spend])

    CAC = DIVIDE([Total Spend], [Total Buyers])

    LTV = [Avg Order Value] * 3

    MoM Revenue Growth =
        VAR ThisMonth = [Total Revenue]
        VAR LastMonth = CALCULATE([Total Revenue], DATEADD('fct_orders'[order_date], -1, MONTH))
        RETURN DIVIDE(ThisMonth - LastMonth, LastMonth)
    ```

    ## Suggested Visuals

    | Visual | Fields |
    |--------|--------|
    | KPI Cards | Total Revenue, CVR, CAC, ROAS |
    | Line Chart | month × revenue (by channel) |
    | Funnel Chart | stage × users |
    | Bar Chart | segment × avg_ltv |
    | Scatter | avg_cac × avg_roas (by channel) |
    """)
    path = os.path.join(BI_DIR, "POWERBI_CONNECTION_GUIDE.md")
    with open(path, "w") as f:
        f.write(guide)
    print(f"  ✓  POWERBI_CONNECTION_GUIDE.md")


def run_export() -> None:
    print("\n" + "="*60)
    print("  📊  BI Export — Tableau / Power BI")
    print("="*60)

    if not os.path.exists(DB_PATH):
        print("❌  Database not found. Run `python etl/pipeline.py` first.")
        return

    conn = sqlite3.connect(DB_PATH)

    print("\n[1/4] Exporting CSVs …")
    frames = export_csvs(conn)

    print("\n[2/4] Building Excel workbook …")
    export_excel(frames)

    print("\n[3/4] Writing Tableau Data Source (.tds) …")
    write_tableau_datasource()

    print("\n[4/4] Writing Power BI connection guide …")
    write_powerbi_instructions()

    conn.close()
    print(f"\n{'='*60}")
    print(f"  ✅  Export complete!")
    print(f"  📂  Output: {BI_DIR}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_export()
