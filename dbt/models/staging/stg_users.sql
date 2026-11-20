{{ config(materialized='view') }}

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
FROM {{ source('bronze', 'raw_users') }}
GROUP BY user_id
