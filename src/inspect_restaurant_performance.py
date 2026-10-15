import duckdb

con = duckdb.connect(
    "data/warehouse/zomato.duckdb",
    read_only=True
)

print("\n=== TOP 10 RESTAURANTS BY DELIVERED REVENUE ===")
print(con.execute("""
    SELECT
        restaurant_name,
        restaurant_city,
        currency,
        delivered_orders,
        ROUND(delivered_revenue, 2) AS delivered_revenue,
        ROUND(avg_delivered_order_rating, 2) AS avg_rating,
        ROUND(avg_delivery_time_min, 1) AS avg_delivery_min
    FROM analytics.restaurant_performance
    ORDER BY delivered_revenue DESC
    LIMIT 10
""").fetchdf().to_string(index=False))

print("\n=== RESTAURANT MODEL CHECK ===")
print(con.execute("""
    SELECT
        COUNT(*) AS restaurant_groups,
        SUM(total_orders) AS total_orders,
        SUM(delivered_orders) AS delivered_orders
    FROM analytics.restaurant_performance
""").fetchdf().to_string(index=False))

con.close()
