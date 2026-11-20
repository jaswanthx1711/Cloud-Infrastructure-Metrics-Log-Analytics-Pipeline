"""
pipeline.py
Master ETL orchestrator – runs the full pipeline end-to-end:
  1. Generate synthetic data (if raw CSVs not present)
  2. Ingest raw CSVs into bronze layer (SQLite)
  3. Transform into silver + gold layers
  4. Run analytics SQL queries and export result CSVs
"""

import logging
import os
import sys
import sqlite3
import time
import pandas as pd
import subprocess
import shutil

# ── ensure repo root is importable ──────────────────────────────────────
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from config import RAW_DIR, PROCESSED_DIR, DB_PATH, PIPELINE_CUTOFF_DATE
from etl.ingest    import ingest_raw
from etl.transform import run_all as run_transforms

logger = logging.getLogger(__name__)

os.makedirs(PROCESSED_DIR, exist_ok=True)


def _check_raw_data() -> bool:
    required = ["users.csv", "user_events.csv", "sales.csv", "marketing.csv"]
    return all(os.path.exists(os.path.join(RAW_DIR, f)) for f in required)


def _run_analytics(conn: sqlite3.Connection) -> None:
    """Execute key analytics queries and export CSVs for BI tools."""

    analyses = {
        # ── Funnel analysis ────────────────────────────────────────────
        "funnel_conversion": """
            SELECT
                stage,
                stage_order,
                COUNT(DISTINCT user_id) AS users,
                100.0 * COUNT(DISTINCT user_id) /
                    NULLIF(MAX(COUNT(DISTINCT user_id)) OVER (), 0) AS pct_of_top
            FROM fct_events
            GROUP BY stage, stage_order
            ORDER BY stage_order
        """,

        # ── Cohort retention (weekly) ──────────────────────────────────
        "cohort_retention": """
            WITH cohort AS (
                SELECT user_id,
                       MIN(week) AS cohort_week
                FROM fct_events
                WHERE stage = 'visit'
                GROUP BY user_id
            ),
            activity AS (
                SELECT DISTINCT e.user_id, e.week AS activity_week, c.cohort_week
                FROM fct_events e
                JOIN cohort c USING (user_id)
            )
            SELECT
                cohort_week,
                activity_week,
                COUNT(DISTINCT user_id) AS active_users
            FROM activity
            GROUP BY cohort_week, activity_week
            ORDER BY cohort_week, activity_week
        """,

        # ── Monthly revenue summary ────────────────────────────────────
        "monthly_revenue": """
            SELECT
                month,
                channel,
                COUNT(DISTINCT user_id)   AS unique_buyers,
                COUNT(DISTINCT order_id)  AS orders,
                SUM(net_revenue)          AS revenue,
                AVG(net_revenue)          AS avg_order_value
            FROM fct_orders
            WHERE status = 'completed'
            GROUP BY month, channel
            ORDER BY month, channel
        """,

        # ── Channel KPI summary ────────────────────────────────────────
        "channel_kpis": """
            SELECT * FROM agg_channel_kpis
            ORDER BY total_revenue DESC
        """,

        # ── Product performance ────────────────────────────────────────
        "product_performance": """
            SELECT
                o.product_id,
                p.category,
                COUNT(DISTINCT o.order_id) AS orders,
                SUM(o.quantity)            AS units_sold,
                SUM(o.net_revenue)         AS revenue
            FROM fct_orders o
            LEFT JOIN dim_products p USING (product_id)
            WHERE o.status = 'completed'
            GROUP BY o.product_id, p.category
            ORDER BY revenue DESC
            LIMIT 20
        """,

        # ── A/B test simulation (plan vs CVR) ─────────────────────────
        "ab_test_plan_cvr": """
            WITH visitors AS (
                SELECT plan, COUNT(DISTINCT user_id) AS total_users
                FROM fct_events
                WHERE stage = 'visit'
                GROUP BY plan
            ),
            buyers AS (
                SELECT plan, COUNT(DISTINCT user_id) AS converted_users
                FROM fct_orders
                WHERE status = 'completed'
                GROUP BY plan
            )
            SELECT
                v.plan,
                v.total_users,
                COALESCE(b.converted_users, 0) AS converted_users,
                ROUND(100.0 * COALESCE(b.converted_users, 0) / NULLIF(v.total_users, 0), 2) AS cvr_pct
            FROM visitors v
            LEFT JOIN buyers b USING (plan)
            ORDER BY cvr_pct DESC
        """,

        # ── RFM segmentation ──────────────────────────────────────────
        "rfm_segmentation": f"""
            WITH rfm_raw AS (
                SELECT
                    user_id,
                    JULIANDAY('{PIPELINE_CUTOFF_DATE}') - JULIANDAY(MAX(order_date)) AS recency_days,
                    COUNT(DISTINCT order_id)                              AS frequency,
                    SUM(net_revenue)                                      AS monetary
                FROM fct_orders
                WHERE status = 'completed'
                GROUP BY user_id
            ),
            rfm_scored AS (
                SELECT *,
                    NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
                    NTILE(4) OVER (ORDER BY frequency)         AS f_score,
                    NTILE(4) OVER (ORDER BY monetary)          AS m_score
                FROM rfm_raw
            )
            SELECT *,
                (f_score + m_score + r_score) AS rfm_composite,
                CASE
                    WHEN f_score = 4 AND m_score = 4 THEN 'Champions'
                    WHEN f_score >= 3               THEN 'Loyal'
                    WHEN r_score <= 2               THEN 'At Risk'
                    ELSE 'Potential'
                END AS segment
            FROM rfm_scored
            ORDER BY rfm_composite DESC
        """,
    }

    for name, sql in analyses.items():
        try:
            df = pd.read_sql(sql, conn)
            out_path = os.path.join(PROCESSED_DIR, f"{name}.csv")
            df.to_csv(out_path, index=False)
            logger.info("  ✓ Exported %-25s → %6d rows", name, len(df))
        except Exception as exc:
            logger.error("  ✖ Failed to export %s: %s", name, exc)


# ── Main ───────────────────────────────────────────────────────────────
def run_pipeline() -> None:
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("  🚀  E-Commerce Analytics ETL Pipeline")
    logger.info("=" * 60)

    # Step 1 – Generate data if needed
    if not _check_raw_data():
        logger.info("[1/4] Generating synthetic raw data …")
        from etl.generate_data import (
            generate_users, generate_events, generate_sales, generate_marketing
        )
        users     = generate_users()
        events    = generate_events(users)
        sales     = generate_sales(users)
        marketing = generate_marketing()
        users.to_csv(    os.path.join(RAW_DIR, "users.csv"),        index=False)
        events.to_csv(   os.path.join(RAW_DIR, "user_events.csv"),  index=False)
        sales.to_csv(    os.path.join(RAW_DIR, "sales.csv"),        index=False)
        marketing.to_csv(os.path.join(RAW_DIR, "marketing.csv"),    index=False)
    else:
        logger.info("[1/4] Raw data already present — skipping generation.")

    # Step 2 – Bronze layer
    logger.info("[2/4] Ingesting raw data (Bronze layer) …")
    ingest_raw()

    # Step 3 – Silver + Gold
    logger.info("[3/4] Running transformations (Silver → Gold) …")

    def run_dbt_or_fallback(project_dir: str = "dbt") -> None:
        if shutil.which("dbt") is None:
            logger.warning("  ⚠️  dbt not found on PATH — running Python transforms instead.")
            run_transforms()
            return
        try:
            logger.info("  ▶ Running: dbt run --project-dir %s", project_dir)
            res = subprocess.run(
                ["dbt", "run", "--project-dir", project_dir],
                check=False, timeout=300,
            )
            if res.returncode != 0:
                logger.warning("  ✖ dbt run failed — falling back to Python transforms.")
                run_transforms()
                return
            logger.info("  ✓ dbt run completed; running dbt tests …")
            subprocess.run(
                ["dbt", "test", "--project-dir", project_dir],
                check=False, timeout=300,
            )
        except Exception as exc:
            logger.error("  ✖ Error running dbt: %s — falling back to Python transforms.", exc)
            run_transforms()

    run_dbt_or_fallback()

    # Step 4 – Analytics exports
    logger.info("[4/4] Exporting analytics queries …")
    conn = sqlite3.connect(DB_PATH)
    try:
        _run_analytics(conn)
    finally:
        conn.close()

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info("  ✅  Pipeline complete in %.1fs", elapsed)
    logger.info("  📁  Analytics DB : %s", DB_PATH)
    logger.info("  📂  Processed CSVs: %s", PROCESSED_DIR)
    logger.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    run_pipeline()
