-- =============================================================
-- Analytics Layer: Funnel Analysis
-- Measures conversion rates at each funnel stage and
-- identifies primary drop-off points.
-- =============================================================

-- 1. Overall funnel conversion rates
SELECT
    stage,
    stage_order,
    COUNT(DISTINCT user_id)                                              AS users_reached,
    LAG(COUNT(DISTINCT user_id)) OVER (ORDER BY stage_order)             AS prev_stage_users,
    ROUND(
        100.0 * COUNT(DISTINCT user_id) /
        NULLIF(FIRST_VALUE(COUNT(DISTINCT user_id)) OVER (ORDER BY stage_order), 0),
        2
    )                                                                    AS pct_of_top_of_funnel,
    ROUND(
        100.0 * COUNT(DISTINCT user_id) /
        NULLIF(LAG(COUNT(DISTINCT user_id)) OVER (ORDER BY stage_order), 0),
        2
    )                                                                    AS step_conversion_rate
FROM fct_events
GROUP BY stage, stage_order
ORDER BY stage_order;


-- 2. Funnel by acquisition channel (identifies best-converting channels)
WITH channel_funnel AS (
    SELECT
        channel,
        stage,
        stage_order,
        COUNT(DISTINCT user_id) AS users
    FROM fct_events
    GROUP BY channel, stage, stage_order
),
top_of_funnel AS (
    SELECT channel, users AS visitors
    FROM channel_funnel
    WHERE stage = 'visit'
)
SELECT
    cf.channel,
    cf.stage,
    cf.stage_order,
    cf.users,
    t.visitors,
    ROUND(100.0 * cf.users / NULLIF(t.visitors, 0), 2) AS pct_of_visitors
FROM channel_funnel cf
JOIN top_of_funnel t USING (channel)
ORDER BY cf.channel, cf.stage_order;


-- 3. Drop-off analysis: where users abandon the most
WITH stage_counts AS (
    SELECT stage, stage_order, COUNT(DISTINCT user_id) AS users
    FROM fct_events GROUP BY stage, stage_order
)
SELECT
    stage,
    users,
    LAG(users) OVER (ORDER BY stage_order) - users AS absolute_dropoff,
    ROUND(
        100.0 * (LAG(users) OVER (ORDER BY stage_order) - users) /
        NULLIF(LAG(users) OVER (ORDER BY stage_order), 0),
        2
    )                                               AS dropoff_rate_pct
FROM stage_counts
ORDER BY stage_order;


-- 4. Funnel by device type
SELECT
    device,
    stage,
    stage_order,
    COUNT(DISTINCT user_id) AS users
FROM fct_events
GROUP BY device, stage, stage_order
ORDER BY device, stage_order;


-- 5. Funnel by plan tier
SELECT
    plan,
    stage,
    stage_order,
    COUNT(DISTINCT user_id) AS users
FROM fct_events
GROUP BY plan, stage, stage_order
ORDER BY stage_order, plan;
