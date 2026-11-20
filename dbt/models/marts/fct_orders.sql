{{ config(materialized='table') }}

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
FROM {{ ref('stg_sales') }} s
LEFT JOIN {{ ref('stg_users') }} u USING (user_id)
