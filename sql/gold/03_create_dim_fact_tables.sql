-- =============================================================
-- Gold Layer: Dimension + Fact tables
-- =============================================================

-- dim_users
CREATE TABLE IF NOT EXISTS dim_users AS
SELECT * FROM stg_users;

-- dim_products
CREATE TABLE IF NOT EXISTS dim_products AS
SELECT DISTINCT
    product_id,
    CASE (CAST(REPLACE(product_id, 'PROD-', '') AS INTEGER) % 5)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Apparel'
        WHEN 2 THEN 'Home'
        WHEN 3 THEN 'Books'
        WHEN 4 THEN 'Sports'
    END AS category
FROM stg_sales;

-- dim_campaigns
CREATE TABLE IF NOT EXISTS dim_campaigns AS
SELECT * FROM stg_marketing;

-- fct_orders: enriched order lines
CREATE TABLE IF NOT EXISTS fct_orders AS
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
LEFT JOIN stg_users u USING (user_id);

-- fct_events: enriched funnel events
CREATE TABLE IF NOT EXISTS fct_events AS
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
LEFT JOIN stg_users u USING (user_id);

-- agg_channel_kpis: combined revenue + marketing KPIs per channel
CREATE TABLE IF NOT EXISTS agg_channel_kpis AS
WITH sales_agg AS (
    SELECT
        channel,
        COUNT(DISTINCT user_id)  AS buyers,
        SUM(net_revenue)         AS total_revenue,
        AVG(net_revenue)         AS avg_order_value
    FROM fct_orders
    WHERE status = 'completed'
    GROUP BY channel
),
mkt_agg AS (
    SELECT
        channel,
        SUM(spend)               AS total_spend,
        SUM(conversions)         AS total_conversions,
        AVG(cvr)                 AS avg_cvr,
        AVG(cac)                 AS avg_cac,
        AVG(roas)                AS avg_roas
    FROM stg_marketing
    GROUP BY channel
)
SELECT
    COALESCE(s.channel, m.channel)         AS channel,
    COALESCE(s.buyers, 0)                  AS buyers,
    COALESCE(s.total_revenue, 0)           AS total_revenue,
    COALESCE(s.avg_order_value, 0)         AS avg_order_value,
    ROUND(COALESCE(s.avg_order_value, 0) * 3, 2) AS ltv_estimate,
    COALESCE(m.total_spend, 0)             AS total_spend,
    COALESCE(m.total_conversions, 0)       AS total_conversions,
    COALESCE(m.avg_cvr, 0)                AS avg_cvr,
    COALESCE(m.avg_cac, 0)                AS avg_cac,
    COALESCE(m.avg_roas, 0)               AS avg_roas
FROM sales_agg s
FULL OUTER JOIN mkt_agg m USING (channel)
ORDER BY total_revenue DESC;
