"""
test_pipeline.py
Unit tests for the ETL pipeline components.
Run with: pytest tests/ -v
"""

import os
import sys
import sqlite3

import pandas as pd
import pytest
from scipy.stats import chi2_contingency

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def tmp_db(tmp_path_factory):
    """Create a temp SQLite DB and seed it with minimal fixtures."""
    db_path = str(tmp_path_factory.mktemp("data") / "test_analytics.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Minimal raw_users
    cur.execute("""
        CREATE TABLE raw_users (
            user_id TEXT, name TEXT, email TEXT, country TEXT,
            channel TEXT, acquisition_date TEXT, age_group TEXT, plan TEXT
        )
    """)
    cur.executemany("INSERT INTO raw_users VALUES (?,?,?,?,?,?,?,?)", [
        ("U00001", "Alice", "Alice@Test.COM", "US", "organic_search", "2025-01-10", "25-34", "pro"),
        ("U00002", "Bob",   "bob@test.com",   "UK", "paid_search",    "2025-02-15", "35-44", "free"),
        ("U00003", "Carol", "carol@test.com", "DE", "social_media",   "2025-03-01", "18-24", "enterprise"),
        ("U00001", "Alice", "alice@test.com",  "US", "organic_search", "2025-01-10", "25-34", "pro"),  # duplicate
    ])

    # Minimal raw_sales
    cur.execute("""
        CREATE TABLE raw_sales (
            order_id TEXT, line_id INT, user_id TEXT, product_id TEXT,
            quantity INT, unit_price REAL, discount_pct REAL,
            order_date TEXT, status TEXT, channel TEXT, country TEXT, revenue REAL
        )
    """)
    cur.executemany("INSERT INTO raw_sales VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("ORD-001", 1, "U00001", "PROD-001", 2, 50.0, 10, "2025-03-01", "completed", "organic_search", "US", 90.0),
        ("ORD-002", 1, "U00002", "PROD-002", 1, 30.0,  0, "2025-03-05", "returned",  "paid_search",    "UK", 30.0),
        ("ORD-003", 1, "U00003", "PROD-003", 3, 20.0,  0, "2025-04-01", "completed", "social_media",   "DE", 60.0),
    ])

    # Minimal raw_user_events
    cur.execute("""
        CREATE TABLE raw_user_events (
            event_id TEXT, user_id TEXT, session_id TEXT, stage TEXT,
            product_id TEXT, timestamp TEXT, device TEXT, country TEXT
        )
    """)
    cur.executemany("INSERT INTO raw_user_events VALUES (?,?,?,?,?,?,?,?)", [
        ("EVT-001", "U00001", "SES-A", "visit",        None,       "2025-03-01 10:00", "desktop", "US"),
        ("EVT-002", "U00001", "SES-A", "product_view", "PROD-001", "2025-03-01 10:05", "desktop", "US"),
        ("EVT-003", "U00001", "SES-A", "purchase",     "PROD-001", "2025-03-01 10:15", "desktop", "US"),
        ("EVT-004", "U00002", "SES-B", "visit",        None,       "2025-03-05 09:00", "mobile",  "UK"),
        ("EVT-005", "U00003", "SES-C", "visit",        None,       "2025-04-01 08:00", "tablet",  "DE"),
        ("EVT-006", "U00003", "SES-C", "product_view", "PROD-003", "2025-04-01 08:10", "tablet",  "DE"),
    ])

    # Minimal raw_marketing
    cur.execute("""
        CREATE TABLE raw_marketing (
            campaign_id TEXT, campaign_name TEXT, channel TEXT,
            start_date TEXT, end_date TEXT, budget REAL, spend REAL,
            impressions INT, clicks INT, conversions INT, revenue_attributed REAL
        )
    """)
    cur.executemany("INSERT INTO raw_marketing VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
        ("CMP-001", "SEO Campaign",    "organic_search", "2025-01-01", "2025-03-31",
         5000, 4500, 100000, 3000, 150, 12000),
        ("CMP-002", "Social Campaign", "social_media",   "2025-02-01", "2025-04-30",
         3000, 2800, 80000, 2000, 80, 8000),
    ])

    conn.commit()
    return db_path, conn


# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────

class TestDataGeneration:
    """Tests for synthetic data generation."""

    def test_generate_users_count(self):
        """Users dataframe should have the requested number of unique user_ids."""
        from etl.generate_data import generate_users
        df = generate_users()
        assert len(df) == 5_000
        assert df["user_id"].nunique() == 5_000

    def test_generate_users_required_columns(self):
        from etl.generate_data import generate_users
        df = generate_users()
        required = {"user_id", "channel", "plan", "acquisition_date", "country"}
        assert required.issubset(df.columns)

    def test_generate_sales_revenue_positive(self):
        from etl.generate_data import generate_users, generate_sales
        users = generate_users()
        sales = generate_sales(users)
        assert (sales["revenue"] >= 0).all(), "All revenue values must be non-negative"

    def test_generate_marketing_metrics_range(self):
        from etl.generate_data import generate_marketing
        mkt = generate_marketing()
        assert (mkt["clicks"] <= mkt["impressions"]).all(), "Clicks must not exceed impressions"
        assert (mkt["conversions"] <= mkt["clicks"]).all(), "Conversions must not exceed clicks"


class TestTransformations:
    """Tests for silver/gold layer transforms."""

    def test_stg_users_deduplication(self, tmp_db):
        """stg_users should deduplicate on user_id."""
        from etl.transform import build_stg_users
        _, conn = tmp_db
        df = build_stg_users(conn)
        assert df["user_id"].nunique() == df["user_id"].count(), "Duplicate user_ids remain after dedup"

    def test_stg_users_email_lowercased(self, tmp_db):
        """Emails should be lower-cased by stg_users."""
        from etl.transform import build_stg_users
        _, conn = tmp_db
        df = build_stg_users(conn)
        assert df["email"].str.lower().equals(df["email"]), "Emails are not uniformly lower-cased"

    def test_stg_sales_net_revenue_formula(self, tmp_db):
        """Net revenue = unit_price * quantity * (1 - discount_pct/100)."""
        from etl.transform import build_stg_sales
        _, conn = tmp_db
        df = build_stg_sales(conn)
        expected = (df["unit_price"] * df["quantity"] * (1 - df["discount_pct"] / 100)).round(2)
        pd.testing.assert_series_equal(df["net_revenue"].round(2), expected.round(2), check_names=False)

    def test_stg_marketing_ctr_bounds(self, tmp_db):
        """CTR must be between 0 and 1."""
        from etl.transform import build_stg_marketing
        _, conn = tmp_db
        df = build_stg_marketing(conn)
        assert (df["ctr"] >= 0).all() and (df["ctr"] <= 1).all(), "CTR out of [0,1] range"

    def test_stg_events_stage_order_assigned(self, tmp_db):
        """All known stages should have a stage_order > 0."""
        from etl.transform import build_stg_events
        _, conn = tmp_db
        df = build_stg_events(conn)
        assert (df["stage_order"] > 0).all(), "Some stages missing a stage_order"

    def test_fct_orders_has_rows(self, tmp_db):
        """fct_orders should have at least one row after build."""
        from etl.transform import build_stg_users, build_stg_sales, build_fct_orders
        _, conn = tmp_db
        build_stg_users(conn)
        build_stg_sales(conn)
        build_fct_orders(conn)
        df = pd.read_sql("SELECT COUNT(*) AS n FROM fct_orders", conn)
        assert df.iloc[0]["n"] > 0

    def test_fct_orders_no_null_order_id(self, tmp_db):
        """fct_orders must not have null order_id values."""
        from etl.transform import build_stg_users, build_stg_sales, build_fct_orders
        _, conn = tmp_db
        build_stg_users(conn)
        build_stg_sales(conn)
        build_fct_orders(conn)
        df = pd.read_sql("SELECT * FROM fct_orders WHERE order_id IS NULL", conn)
        assert len(df) == 0, "Null order_id found in fct_orders"

    def test_fct_events_stage_order_valid(self, tmp_db):
        """fct_events stage_order must be in 1-5 range."""
        from etl.transform import build_stg_users, build_stg_events, build_fct_events
        _, conn = tmp_db
        build_stg_users(conn)
        build_stg_events(conn)
        build_fct_events(conn)
        df = pd.read_sql("SELECT * FROM fct_events", conn)
        assert df["stage_order"].between(1, 5).all(), "stage_order out of [1,5] range"

    def test_agg_channel_kpis_has_channels(self, tmp_db):
        """agg_channel_kpis must contain at least one channel row."""
        from etl.transform import (build_stg_users, build_stg_sales, build_stg_marketing,
                                    build_stg_events, build_fct_orders, build_agg_channel_kpis)
        _, conn = tmp_db
        build_stg_users(conn)
        build_stg_sales(conn)
        build_stg_marketing(conn)
        build_stg_events(conn)
        build_fct_orders(conn)
        build_agg_channel_kpis(conn)
        df = pd.read_sql("SELECT * FROM agg_channel_kpis", conn)
        assert len(df) > 0, "agg_channel_kpis is empty"

    def test_net_revenue_non_negative(self, tmp_db):
        """All net_revenue values in fct_orders must be >= 0."""
        from etl.transform import build_stg_users, build_stg_sales, build_fct_orders
        _, conn = tmp_db
        build_stg_users(conn)
        build_stg_sales(conn)
        build_fct_orders(conn)
        df = pd.read_sql("SELECT net_revenue FROM fct_orders WHERE net_revenue < 0", conn)
        assert len(df) == 0, "Negative net_revenue found in fct_orders"

    def test_dim_users_has_ltv_tier(self, tmp_db):
        """dim_users should have ltv_tier and is_active columns after build."""
        from etl.transform import build_stg_users, build_dim_users
        _, conn = tmp_db
        build_stg_users(conn)
        build_dim_users(conn)
        df = pd.read_sql("SELECT * FROM dim_users LIMIT 1", conn)
        assert "ltv_tier" in df.columns,  "ltv_tier column missing from dim_users"
        assert "is_active" in df.columns, "is_active column missing from dim_users"


class TestPipelineIntegration:
    """End-to-end pipeline smoke tests."""

    def test_full_pipeline_creates_processed_dir(self, tmp_db):
        """After running all transforms on a seeded DB, gold tables must exist."""
        from etl.transform import (
            build_stg_users, build_stg_sales, build_stg_events, build_stg_marketing,
            build_dim_users, build_dim_products, build_fct_orders, build_fct_events,
            build_agg_channel_kpis,
        )
        _, conn = tmp_db
        build_stg_users(conn)
        build_stg_sales(conn)
        build_stg_events(conn)
        build_stg_marketing(conn)
        build_dim_users(conn)
        build_dim_products(conn)
        build_fct_orders(conn)
        build_fct_events(conn)
        build_agg_channel_kpis(conn)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        gold_tables = {"fct_orders", "fct_events", "agg_channel_kpis", "dim_users", "dim_products"}
        assert gold_tables.issubset(tables), f"Missing gold tables: {gold_tables - tables}"

    def test_db_has_expected_tables(self, tmp_db):
        """After seeding, at minimum raw tables must exist."""
        _, conn = tmp_db
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        required = {"raw_users", "raw_sales", "raw_user_events", "raw_marketing"}
        assert required.issubset(tables), f"Missing tables: {required - tables}"


class TestKPICalculations:
    """Tests for business KPI formulas."""

    def test_cvr_between_0_and_100(self, tmp_db):
        """CVR percent should always be between 0 and 100."""
        _, conn = tmp_db
        from etl.transform import build_stg_users, build_stg_sales, build_stg_events
        build_stg_users(conn)
        build_stg_sales(conn)
        build_stg_events(conn)

        df_events = pd.read_sql("SELECT COUNT(DISTINCT user_id) AS v FROM stg_events WHERE stage='visit'", conn)
        df_orders = pd.read_sql("SELECT COUNT(DISTINCT user_id) AS c FROM stg_sales WHERE status='completed'", conn)
        visitors   = df_events.iloc[0]["v"]
        converters = df_orders.iloc[0]["c"]
        cvr = converters / visitors * 100 if visitors > 0 else 0
        assert 0 <= cvr <= 100, f"CVR {cvr} out of range"

    def test_roas_non_negative(self, tmp_db):
        """ROAS (revenue/spend) should be >= 0 (or NaN where spend=0)."""
        from etl.transform import build_stg_marketing
        _, conn = tmp_db
        df = build_stg_marketing(conn)
        # Where ROAS is not NaN (i.e. spend > 0), it must be >= 0
        valid = df["roas"].dropna()
        assert (valid >= 0).all(), "Negative ROAS detected"

    def test_cac_null_where_zero_conversions(self, tmp_db):
        """CAC should be NaN (not inflated) when conversions = 0."""
        from etl.transform import build_stg_marketing
        _, conn = tmp_db
        df = build_stg_marketing(conn)
        zero_conv = df[df["conversions"] == 0]
        if len(zero_conv) > 0:
            assert zero_conv["cac"].isna().all(), "CAC should be NaN where conversions = 0"


class TestABTest:
    """Tests for A/B test statistical validity."""

    def test_ab_chi2_pvalue_computable(self, tmp_db):
        """Chi-squared test should be computable on plan vs. conversion data."""
        from etl.transform import build_stg_users, build_stg_sales, build_stg_events
        _, conn = tmp_db
        build_stg_users(conn)
        build_stg_sales(conn)
        build_stg_events(conn)
        users_df  = pd.read_sql("SELECT user_id, plan FROM stg_users", conn)
        buyers_df = pd.read_sql("SELECT DISTINCT user_id FROM stg_sales WHERE status='completed'", conn)
        users_df  = users_df.copy()
        users_df["converted"] = users_df["user_id"].isin(buyers_df["user_id"])
        contingency = pd.crosstab(users_df["plan"], users_df["converted"])
        if contingency.shape[0] < 2 or contingency.shape[1] < 2:
            pytest.skip("Not enough plan/conversion combinations in fixture for chi2 test")
        chi2, p, dof, _expected = chi2_contingency(contingency)
        assert 0 <= p <= 1,  f"p-value {p} out of [0,1] range"
        assert chi2 >= 0,    "Chi2 statistic must be non-negative"
        assert dof >= 1,     "Degrees of freedom must be >= 1"


class TestDataQuality:
    """Data quality checks on generated synthetic data."""

    def test_no_post_2025_acquisition_dates(self):
        """No user should have an acquisition_date beyond 2025."""
        from etl.generate_data import generate_users
        df = generate_users()
        df["acquisition_date"] = pd.to_datetime(df["acquisition_date"])
        assert (df["acquisition_date"].dt.year <= 2025).all(), \
            "Some users have acquisition dates beyond 2025"

    def test_session_id_consistent_within_session(self):
        """Events generated within one outer loop iteration share the same session_id.

        Because session_id is an 8-char UUID prefix there may be rare collisions
        between different sessions, so we validate the invariant at the row level:
        every event's session_id must NOT be None/empty, and the number of distinct
        session_ids must be close to N_EVENTS (one per outer loop), not 1.
        """
        from etl.generate_data import generate_users, generate_events, N_EVENTS
        users  = generate_users()
        events = generate_events(users)
        # All session_ids must be populated
        assert events["session_id"].notna().all(), "Some events have null session_id"
        assert (events["session_id"].str.len() > 0).all(), "Some events have empty session_id"
        # With the fix, session_id is shared per outer iteration; total uniques < total rows
        n_unique_sessions = events["session_id"].nunique()
        assert n_unique_sessions < len(events), \
            "session_id appears to be unique per row (not shared within a session)"
        # Sanity: approximately N_EVENTS unique sessions (allow for 8-char prefix collisions)
        assert n_unique_sessions > N_EVENTS * 0.5, \
            f"Too few unique session_ids ({n_unique_sessions}), expected ~{N_EVENTS}"
