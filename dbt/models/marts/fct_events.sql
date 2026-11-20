{{ config(materialized='table') }}

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
FROM {{ ref('stg_events') }} e
LEFT JOIN {{ ref('stg_users') }} u USING (user_id)
