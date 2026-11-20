-- =============================================================
-- Bronze Layer: Raw staging DDL
-- These tables mirror the source CSVs exactly.
-- =============================================================

-- Raw users
CREATE TABLE IF NOT EXISTS raw_users (
    user_id          TEXT,
    name             TEXT,
    email            TEXT,
    country          TEXT,
    channel          TEXT,
    acquisition_date TEXT,
    age_group        TEXT,
    plan             TEXT
);

-- Raw user events (clickstream / funnel)
CREATE TABLE IF NOT EXISTS raw_user_events (
    event_id    TEXT,
    user_id     TEXT,
    session_id  TEXT,
    stage       TEXT,
    product_id  TEXT,
    timestamp   TEXT,
    device      TEXT,
    country     TEXT
);

-- Raw sales (transactional)
CREATE TABLE IF NOT EXISTS raw_sales (
    order_id     TEXT,
    line_id      INTEGER,
    user_id      TEXT,
    product_id   TEXT,
    quantity     INTEGER,
    unit_price   REAL,
    discount_pct REAL,
    order_date   TEXT,
    status       TEXT,
    channel      TEXT,
    country      TEXT,
    revenue      REAL
);

-- Raw marketing campaigns
CREATE TABLE IF NOT EXISTS raw_marketing (
    campaign_id          TEXT,
    campaign_name        TEXT,
    channel              TEXT,
    start_date           TEXT,
    end_date             TEXT,
    budget               REAL,
    spend                REAL,
    impressions          INTEGER,
    clicks               INTEGER,
    conversions          INTEGER,
    revenue_attributed   REAL
);
