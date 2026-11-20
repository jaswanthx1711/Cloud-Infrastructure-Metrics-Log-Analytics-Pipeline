-- =============================================================
-- Analytics Layer: A/B Test Analysis + Segmentation
-- =============================================================

-- ══════════════════════════════════════════════════════════════
-- A/B TEST: Plan tier vs Conversion Rate
-- Treats 'free' as control and paid tiers as treatment groups.
-- ══════════════════════════════════════════════════════════════

-- 1. Sample sizes and conversions per plan (funnel top → purchase)
WITH visitors AS (
    SELECT
        plan,
        COUNT(DISTINCT user_id) AS total_visitors
    FROM fct_events
    WHERE stage = 'visit'
    GROUP BY plan
),
converters AS (
    SELECT
        plan,
        COUNT(DISTINCT user_id) AS total_converters
    FROM fct_orders
    WHERE status = 'completed'
    GROUP BY plan
)
SELECT
    v.plan,
    v.total_visitors,
    COALESCE(c.total_converters, 0)                              AS total_converters,
    ROUND(100.0 * COALESCE(c.total_converters, 0) / v.total_visitors, 4) AS cvr_pct,
    -- Relative lift vs 'free' baseline
    ROUND(
        100.0 * (
            1.0 * COALESCE(c.total_converters, 0) / v.total_visitors -
            (SELECT 1.0 * total_converters / total_visitors FROM converters
             JOIN visitors USING(plan) WHERE visitors.plan = 'free' LIMIT 1)
        ) / NULLIF(
            (SELECT 1.0 * total_converters / total_visitors FROM converters
             JOIN visitors USING(plan) WHERE visitors.plan = 'free' LIMIT 1),
        0), 2
    )                                                            AS lift_vs_free_pct
FROM visitors v
LEFT JOIN converters c USING (plan)
ORDER BY cvr_pct DESC;


-- 2. Channel CVR comparison (which acquisition channel converts best?)
WITH channel_visitors AS (
    SELECT channel, COUNT(DISTINCT user_id) AS visitors
    FROM fct_events WHERE stage = 'visit'
    GROUP BY channel
),
channel_buyers AS (
    SELECT channel, COUNT(DISTINCT user_id) AS buyers
    FROM fct_orders WHERE status = 'completed'
    GROUP BY channel
)
SELECT
    v.channel,
    v.visitors,
    COALESCE(b.buyers, 0)                                      AS buyers,
    ROUND(100.0 * COALESCE(b.buyers, 0) / v.visitors, 2)      AS cvr_pct
FROM channel_visitors v
LEFT JOIN channel_buyers b USING (channel)
ORDER BY cvr_pct DESC;


-- ══════════════════════════════════════════════════════════════
-- RFM Segmentation (Recency, Frequency, Monetary)
-- ══════════════════════════════════════════════════════════════

-- 3. RFM scores per user
WITH rfm_raw AS (
    SELECT
        user_id,
        JULIANDAY('2026-01-01') - JULIANDAY(MAX(order_date)) AS recency_days,
        COUNT(DISTINCT order_id)                              AS frequency,
        SUM(net_revenue)                                      AS monetary
    FROM fct_orders
    WHERE status = 'completed'
    GROUP BY user_id
),
rfm_percentiles AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,  -- 4=most recent
        NTILE(4) OVER (ORDER BY frequency)         AS f_score,
        NTILE(4) OVER (ORDER BY monetary)          AS m_score
    FROM rfm_raw
)
SELECT
    r.user_id,
    u.channel,
    u.plan,
    u.country,
    ROUND(r.recency_days, 1)  AS recency_days,
    r.frequency,
    ROUND(r.monetary, 2)      AS monetary,
    r.r_score,
    r.f_score,
    r.m_score,
    (r.r_score + r.f_score + r.m_score) AS rfm_total,
    CASE
        WHEN r.r_score >= 3 AND r.f_score >= 3 AND r.m_score >= 3 THEN 'Champions'
        WHEN r.r_score >= 3 AND r.f_score >= 2                     THEN 'Loyal Customers'
        WHEN r.r_score >= 3 AND r.f_score = 1                      THEN 'Recent Customers'
        WHEN r.r_score = 2  AND r.f_score >= 2                     THEN 'At Risk'
        WHEN r.r_score = 1  AND r.f_score >= 2                     THEN 'Cannot Lose Them'
        WHEN r.r_score <= 2 AND r.f_score <= 2 AND r.m_score >= 3  THEN 'Hibernating High-Value'
        ELSE 'Lost/Low-Value'
    END                       AS segment
FROM rfm_percentiles r
LEFT JOIN dim_users u USING (user_id)
ORDER BY rfm_total DESC;


-- 4. Segment summary: size and revenue contribution
WITH rfm_raw AS (
    SELECT
        user_id,
        JULIANDAY('2026-01-01') - JULIANDAY(MAX(order_date)) AS recency_days,
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
),
segmented AS (
    SELECT *,
        CASE
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 2                   THEN 'Loyal Customers'
            WHEN r_score >= 3 AND f_score = 1                    THEN 'Recent Customers'
            WHEN r_score = 2  AND f_score >= 2                   THEN 'At Risk'
            WHEN r_score = 1  AND f_score >= 2                   THEN 'Cannot Lose Them'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 3  THEN 'Hibernating High-Value'
            ELSE 'Lost/Low-Value'
        END AS segment
    FROM rfm_scored
)
SELECT
    segment,
    COUNT(*)                          AS users,
    ROUND(AVG(recency_days), 1)       AS avg_recency_days,
    ROUND(AVG(frequency), 2)          AS avg_orders,
    ROUND(AVG(monetary), 2)           AS avg_ltv,
    ROUND(SUM(monetary), 2)           AS total_revenue,
    ROUND(100.0 * SUM(monetary) /
        (SELECT SUM(monetary) FROM rfm_raw), 2) AS revenue_share_pct
FROM segmented
GROUP BY segment
ORDER BY total_revenue DESC;
