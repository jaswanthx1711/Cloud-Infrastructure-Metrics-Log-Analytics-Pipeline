{{ config(materialized='table') }}

WITH sales_agg AS (
    SELECT
        channel,
        COUNT(DISTINCT user_id)  AS buyers,
        SUM(net_revenue)         AS total_revenue,
        AVG(net_revenue)         AS avg_order_value
    FROM {{ ref('fct_orders') }}
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
    FROM {{ ref('stg_marketing') }}
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
LEFT JOIN mkt_agg m USING (channel)

UNION

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
FROM mkt_agg m
LEFT JOIN sales_agg s USING (channel)
WHERE s.channel IS NULL
ORDER BY total_revenue DESC
