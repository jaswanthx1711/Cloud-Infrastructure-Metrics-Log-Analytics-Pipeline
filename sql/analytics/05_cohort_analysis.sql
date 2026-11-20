-- =============================================================
-- Analytics Layer: Cohort Analysis
-- Tracks user retention across weekly and monthly cohorts.
-- =============================================================

-- 1. Weekly cohort retention matrix
WITH cohort_start AS (
    SELECT
        user_id,
        MIN(week) AS cohort_week
    FROM fct_events
    WHERE stage = 'visit'
    GROUP BY user_id
),
user_activity AS (
    SELECT DISTINCT
        e.user_id,
        e.week          AS activity_week,
        c.cohort_week
    FROM fct_events e
    JOIN cohort_start c USING (user_id)
),
cohort_sizes AS (
    SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohort_start
    GROUP BY cohort_week
)
SELECT
    a.cohort_week,
    a.activity_week,
    cs.cohort_size,
    COUNT(DISTINCT a.user_id)                                        AS active_users,
    ROUND(100.0 * COUNT(DISTINCT a.user_id) / cs.cohort_size, 2)    AS retention_rate
FROM user_activity a
JOIN cohort_sizes cs USING (cohort_week)
GROUP BY a.cohort_week, a.activity_week, cs.cohort_size
ORDER BY a.cohort_week, a.activity_week;


-- 2. Monthly cohort purchase retention
WITH cohort_start AS (
    SELECT user_id, STRFTIME('%Y-%m', acquisition_date) AS cohort_month
    FROM dim_users
),
monthly_purchases AS (
    SELECT DISTINCT
        o.user_id,
        o.month         AS purchase_month,
        c.cohort_month
    FROM fct_orders o
    JOIN cohort_start c USING (user_id)
    WHERE o.status = 'completed'
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohort_start
    GROUP BY cohort_month
)
SELECT
    mp.cohort_month,
    mp.purchase_month,
    cs.cohort_size,
    COUNT(DISTINCT mp.user_id)                                           AS purchasing_users,
    ROUND(100.0 * COUNT(DISTINCT mp.user_id) / cs.cohort_size, 2)       AS purchase_retention_rate,
    SUM(o.net_revenue)                                                   AS cohort_revenue
FROM monthly_purchases mp
JOIN cohort_sizes cs USING (cohort_month)
JOIN fct_orders o ON mp.user_id = o.user_id AND mp.purchase_month = o.month
WHERE o.status = 'completed'
GROUP BY mp.cohort_month, mp.purchase_month, cs.cohort_size
ORDER BY mp.cohort_month, mp.purchase_month;


-- 3. Cohort LTV over time (cumulative revenue per user)
WITH cohort_start AS (
    SELECT user_id, STRFTIME('%Y-%m', acquisition_date) AS cohort_month
    FROM dim_users
),
cohort_revenue AS (
    SELECT
        c.cohort_month,
        o.month,
        COUNT(DISTINCT o.user_id) AS buyers,
        SUM(o.net_revenue)        AS revenue
    FROM fct_orders o
    JOIN cohort_start c USING (user_id)
    WHERE o.status = 'completed'
    GROUP BY c.cohort_month, o.month
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohort_start
    GROUP BY cohort_month
)
SELECT
    cr.cohort_month,
    cr.month,
    cs.cohort_size,
    cr.revenue,
    SUM(cr.revenue) OVER (
        PARTITION BY cr.cohort_month ORDER BY cr.month
    )                                                                AS cumulative_revenue,
    ROUND(
        SUM(cr.revenue) OVER (PARTITION BY cr.cohort_month ORDER BY cr.month) /
        NULLIF(cs.cohort_size, 0),
        2
    )                                                                AS cumulative_ltv_per_user
FROM cohort_revenue cr
JOIN cohort_sizes cs USING (cohort_month)
ORDER BY cr.cohort_month, cr.month;
