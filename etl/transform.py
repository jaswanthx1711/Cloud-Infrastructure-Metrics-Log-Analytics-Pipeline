"""
transform.py
Silver + Gold layer transformations.
Reads bronze tables, applies cleaning / typing, and writes:
  Silver: stg_users, stg_events, stg_sales, stg_marketing
  Gold:   dim_users, dim_products, dim_campaigns, fct_orders, fct_events, agg_channel_kpis
"""

import logging
import os
import sys
import sqlite3
import pandas as pd

# ── ensure repo root is importable ──────────────────────────────────────
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from config import DB_PATH

logger = logging.getLogger(__name__)


def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


# ──────────────────────────────────────────────────────────────────────
# SILVER LAYER – cleaned / typed staging models
# ──────────────────────────────────────────────────────────────────────

def build_stg_users(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM raw_users", conn)
    df.drop_duplicates(subset="user_id", inplace=True)
    df["acquisition_date"] = pd.to_datetime(df["acquisition_date"])
    df["email"] = df["email"].str.lower().str.strip()
    df["plan_rank"] = df["plan"].map(
        {"free": 0, "starter": 1, "pro": 2, "enterprise": 3}
    ).fillna(0).astype(int)
    df.to_sql("stg_users", conn, if_exists="replace", index=False)
    return df


def build_stg_events(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM raw_user_events", conn)
    df.drop_duplicates(subset="event_id", inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"]      = df["timestamp"].dt.date.astype(str)
    df["week"]      = df["timestamp"].dt.to_period("W").astype(str)
    df["month"]     = df["timestamp"].dt.to_period("M").astype(str)
    stage_order = {"visit": 1, "product_view": 2, "add_to_cart": 3,
                   "checkout": 4, "purchase": 5}
    df["stage_order"] = df["stage"].map(stage_order)
    df.to_sql("stg_events", conn, if_exists="replace", index=False)
    return df


def build_stg_sales(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM raw_sales", conn)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["month"]   = df["order_date"].dt.to_period("M").astype(str)
    df["quarter"] = df["order_date"].dt.to_period("Q").astype(str)
    df["net_revenue"] = (
        df["unit_price"] * df["quantity"] * (1 - df["discount_pct"] / 100)
    ).round(2)
    df.to_sql("stg_sales", conn, if_exists="replace", index=False)
    return df


def build_stg_marketing(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM raw_marketing", conn)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"]   = pd.to_datetime(df["end_date"])
    df["ctr"]  = (df["clicks"] / df["impressions"]).round(4)
    df["cvr"]  = (df["conversions"] / df["clicks"]).where(df["clicks"] > 0).round(4)
    # Fix zero-division: use NaN where denominator is zero instead of masking with 1
    df["cac"]  = (df["spend"] / df["conversions"]).where(df["conversions"] > 0).round(2)
    df["roas"] = (df["revenue_attributed"] / df["spend"]).where(df["spend"] > 0).round(2)
    df.to_sql("stg_marketing", conn, if_exists="replace", index=False)
    return df


# ──────────────────────────────────────────────────────────────────────
# GOLD LAYER – business aggregations
# ──────────────────────────────────────────────────────────────────────

def build_dim_users(conn: sqlite3.Connection) -> None:
    df = pd.read_sql("SELECT * FROM stg_users", conn)
    # Enrich with derived columns
    df["is_active"] = True
    df["ltv_tier"]  = df["plan"].apply(
        lambda p: "High" if p in ("pro", "enterprise") else "Low"
    )
    df.to_sql("dim_users", conn, if_exists="replace", index=False)


def build_dim_products(conn: sqlite3.Connection) -> None:
    df = pd.read_sql("SELECT DISTINCT product_id FROM stg_sales", conn)
    df["category"] = df["product_id"].apply(
        lambda p: ["Electronics", "Apparel", "Home", "Books", "Sports"][
            int(p.split("-")[1]) % 5
        ]
    )
    df.to_sql("dim_products", conn, if_exists="replace", index=False)


def build_fct_orders(conn: sqlite3.Connection) -> None:
    """Fact table: one row per order line with revenue metrics."""
    df = pd.read_sql("""
        SELECT
            s.order_id,
            s.line_id,
            s.user_id,
            s.product_id,
            s.quantity,
            s.unit_price,
            s.discount_pct,
            s.net_revenue,
            s.order_date,
            s.month,
            s.quarter,
            s.status,
            s.channel,
            s.country,
            u.plan,
            u.age_group,
            u.acquisition_date
        FROM stg_sales s
        LEFT JOIN stg_users u USING (user_id)
    """, conn)
    df.to_sql("fct_orders", conn, if_exists="replace", index=False)


def build_fct_events(conn: sqlite3.Connection) -> None:
    """Fact table: user funnel events with user attributes joined."""
    df = pd.read_sql("""
        SELECT
            e.event_id,
            e.user_id,
            e.session_id,
            e.stage,
            e.stage_order,
            e.product_id,
            e.timestamp,
            e.date,
            e.week,
            e.month,
            e.device,
            e.country,
            u.channel,
            u.plan,
            u.age_group,
            u.acquisition_date
        FROM stg_events e
        LEFT JOIN stg_users u USING (user_id)
    """, conn)
    df.to_sql("fct_events", conn, if_exists="replace", index=False)


def build_agg_channel_kpis(conn: sqlite3.Connection) -> None:
    """Gold aggregate: per-channel KPIs combining sales + marketing."""
    sales_df = pd.read_sql("""
        SELECT channel,
               COUNT(DISTINCT user_id)   AS buyers,
               SUM(net_revenue)          AS total_revenue,
               AVG(net_revenue)          AS avg_order_value
        FROM fct_orders
        WHERE status = 'completed'
        GROUP BY channel
    """, conn)

    mkt_df = pd.read_sql("""
        SELECT channel,
               SUM(spend)                AS total_spend,
               SUM(conversions)          AS total_conversions,
               AVG(cvr)                  AS avg_cvr,
               AVG(cac)                  AS avg_cac,
               AVG(roas)                 AS avg_roas
        FROM stg_marketing
        GROUP BY channel
    """, conn)

    df = sales_df.merge(mkt_df, on="channel", how="outer")
    # LTV estimate: scale by ROAS tier (high-ROAS channels → 3× AOV, others → 1.5×)
    df["ltv_estimate"] = df.apply(
        lambda r: round(r["avg_order_value"] * 3, 2)
        if (r.get("avg_roas") or 0) >= 2
        else round((r["avg_order_value"] or 0) * 1.5, 2),
        axis=1,
    )
    df.to_sql("agg_channel_kpis", conn, if_exists="replace", index=False)


# ──────────────────────────────────────────────────────────────────────
# Run all transformations
# ──────────────────────────────────────────────────────────────────────

def run_all(verbose: bool = True) -> None:
    conn = get_conn()
    steps = [
        ("stg_users",        build_stg_users),
        ("stg_events",       build_stg_events),
        ("stg_sales",        build_stg_sales),
        ("stg_marketing",    build_stg_marketing),
        ("dim_users",        lambda c: build_dim_users(c)),
        ("dim_products",     lambda c: build_dim_products(c)),
        ("fct_orders",       lambda c: build_fct_orders(c)),
        ("fct_events",       lambda c: build_fct_events(c)),
        ("agg_channel_kpis", lambda c: build_agg_channel_kpis(c)),
    ]
    for name, fn in steps:
        fn(conn)
        conn.commit()
        if verbose:
            count = pd.read_sql(f"SELECT COUNT(*) AS n FROM {name}", conn).iloc[0, 0]
            logger.info("  ✓ Built %-22s → %8d rows", name, count)
    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("🔄 Running silver + gold transformations …")
    run_all()
    logger.info("✅ Done.")
