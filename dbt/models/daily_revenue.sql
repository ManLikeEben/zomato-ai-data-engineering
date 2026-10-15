SELECT
    order_date,
    restaurant_city,
    currency,

    COUNT(*) AS total_orders,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(order_status)) = 'delivered'
    ) AS delivered_orders,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(order_status)) = 'cancelled'
    ) AS cancelled_orders,

    COUNT(*) FILTER (
        WHERE LOWER(TRIM(order_status)) = 'refunded'
    ) AS refunded_orders,

    SUM(
        CASE
            WHEN LOWER(TRIM(order_status)) = 'delivered'
            THEN sales_amount
            ELSE 0
        END
    ) AS delivered_revenue,

    AVG(
        CASE
            WHEN LOWER(TRIM(order_status)) = 'delivered'
            THEN delivery_time_min
        END
    ) AS avg_delivery_time_min

FROM {{ ref('stg_orders') }}
GROUP BY
    order_date,
    restaurant_city,
    currency
