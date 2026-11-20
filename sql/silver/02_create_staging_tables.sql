-- =============================================================
-- Silver Layer: Cleaned & typed staging models
-- =============================================================

-- stg_users: deduplicated, lower-cased emails, plan rank added
CREATE TABLE IF NOT EXISTS stg_users AS
SELECT
    user_id,
    name,
    LOWER(TRIM(email))     AS email,
    country,
    channel,
    DATE(acquisition_date) AS acquisition_date,
    age_group,
    plan,
    CASE plan
        WHEN 'free'       THEN 0
        WHEN 'starter'    THEN 1
        WHEN 'pro'        THEN 2
        WHEN 'enterprise' THEN 3
        ELSE 0
    END                    AS plan_rank
FROM raw_users
GROUP BY user_id  -- dedup
;

-- stg_events: stage ordering, date parts extracted
CREATE TABLE IF NOT EXISTS stg_events AS
SELECT
    event_id,
    user_id,
    session_id,
    stage,
    CASE stage
        WHEN 'visit'         THEN 1
        WHEN 'product_view'  THEN 2
        WHEN 'add_to_cart'   THEN 3
        WHEN 'checkout'      THEN 4
        WHEN 'purchase'      THEN 5
    END                              AS stage_order,
    product_id,
    timestamp,
    DATE(timestamp)                  AS date,
    STRFTIME('%Y-W%W', timestamp)    AS week,
    STRFTIME('%Y-%m', timestamp)     AS month,
    device,
    country
FROM raw_user_events
GROUP BY event_id  -- dedup
;

-- stg_sales: net revenue calculated, date parts added
CREATE TABLE IF NOT EXISTS stg_sales AS
SELECT
    order_id,
    line_id,
    user_id,
    product_id,
    quantity,
    unit_price,
    discount_pct,
    ROUND(unit_price * quantity * (1.0 - discount_pct / 100.0), 2) AS net_revenue,
    DATE(order_date)                 AS order_date,
    STRFTIME('%Y-%m', order_date)    AS month,
    CASE
        WHEN CAST(STRFTIME('%m', order_date) AS INTEGER) BETWEEN 1  AND 3  THEN STRFTIME('%Y', order_date) || '-Q1'
        WHEN CAST(STRFTIME('%m', order_date) AS INTEGER) BETWEEN 4  AND 6  THEN STRFTIME('%Y', order_date) || '-Q2'
        WHEN CAST(STRFTIME('%m', order_date) AS INTEGER) BETWEEN 7  AND 9  THEN STRFTIME('%Y', order_date) || '-Q3'
        ELSE                                                                     STRFTIME('%Y', order_date) || '-Q4'
    END                              AS quarter,
    status,
    channel,
    country
FROM raw_sales
;

-- stg_marketing: computed CTR, CVR, CAC, ROAS
CREATE TABLE IF NOT EXISTS stg_marketing AS
SELECT
    campaign_id,
    campaign_name,
    channel,
    DATE(start_date)                            AS start_date,
    DATE(end_date)                              AS end_date,
    budget,
    spend,
    impressions,
    clicks,
    conversions,
    revenue_attributed,
    ROUND(1.0 * clicks / NULLIF(impressions, 0),    4) AS ctr,
    ROUND(1.0 * conversions / NULLIF(clicks, 0),    4) AS cvr,
    ROUND(spend / NULLIF(conversions, 0),           2) AS cac,
    ROUND(revenue_attributed / NULLIF(spend, 0),    2) AS roas
FROM raw_marketing
;
