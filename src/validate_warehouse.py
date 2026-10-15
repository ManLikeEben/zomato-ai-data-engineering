import duckdb

con = duckdb.connect("data/warehouse/zomato.duckdb", read_only=True)
con.execute("SET memory_limit = '3GB'")
con.execute("SET threads = 2")

def check(label, sql):
    result = con.execute(sql).fetchone()
    print(f"{label}: {result[0]}")

print("\n=== 1. CRITICAL MISSING VALUES ===")

checks = [
    ("Orders missing order_id", "SELECT COUNT(*) FROM fact_orders WHERE order_id IS NULL"),
    ("Orders missing user_id", "SELECT COUNT(*) FROM fact_orders WHERE user_id IS NULL"),
    ("Orders missing restaurant_id", "SELECT COUNT(*) FROM fact_orders WHERE restaurant_id IS NULL"),
    ("Orders missing order_timestamp", "SELECT COUNT(*) FROM fact_orders WHERE order_timestamp IS NULL"),
    ("Orders missing sales_amount", "SELECT COUNT(*) FROM fact_orders WHERE sales_amount IS NULL"),
    ("Order items missing order_id", "SELECT COUNT(*) FROM fact_order_items WHERE order_id IS NULL"),
    ("Order items missing food_id", "SELECT COUNT(*) FROM fact_order_items WHERE food_id IS NULL"),
    ("Restaurants missing name", "SELECT COUNT(*) FROM dim_restaurant WHERE restaurant_name IS NULL OR TRIM(restaurant_name) = ''"),
]

for label, sql in checks:
    check(label, sql)

print("\n=== 2. DUPLICATE KEY CHECKS ===")

for table, key in [
    ("dim_restaurant", "restaurant_id"),
    ("dim_user", "user_id"),
    ("dim_food", "food_id"),
    ("fact_orders", "order_id"),
    ("fact_order_items", "order_item_id"),
    ("fact_reviews", "review_id"),
]:
    check(f"{table}: duplicate {key} values", f"""
        SELECT COUNT(*) FROM (
            SELECT {key} FROM {table}
            GROUP BY {key} HAVING COUNT(*) > 1
        ) duplicates
    """)

print("\n=== 3. RELATIONSHIP CHECKS ===")

relationships = [
    ("Orders with unknown users", """
        SELECT COUNT(*) FROM fact_orders o
        LEFT JOIN dim_user u ON o.user_id = u.user_id
        WHERE o.user_id IS NOT NULL AND u.user_id IS NULL
    """),
    ("Orders with unknown restaurants", """
        SELECT COUNT(*) FROM fact_orders o
        LEFT JOIN dim_restaurant r ON o.restaurant_id = r.restaurant_id
        WHERE o.restaurant_id IS NOT NULL AND r.restaurant_id IS NULL
    """),
    ("Order items with unknown orders", """
        SELECT COUNT(*) FROM fact_order_items i
        LEFT JOIN fact_orders o ON i.order_id = o.order_id
        WHERE i.order_id IS NOT NULL AND o.order_id IS NULL
    """),
    ("Order items with unknown food", """
        SELECT COUNT(*) FROM fact_order_items i
        LEFT JOIN dim_food f ON i.food_id = f.food_id
        WHERE i.food_id IS NOT NULL AND f.food_id IS NULL
    """),
    ("Reviews with unknown orders", """
        SELECT COUNT(*) FROM fact_reviews r
        LEFT JOIN fact_orders o ON r.order_id = o.order_id
        WHERE r.order_id IS NOT NULL AND o.order_id IS NULL
    """),
    ("Reviews with unknown users", """
        SELECT COUNT(*) FROM fact_reviews r
        LEFT JOIN dim_user u ON r.user_id = u.user_id
        WHERE r.user_id IS NOT NULL AND u.user_id IS NULL
    """),
    ("Reviews with unknown restaurants", """
        SELECT COUNT(*) FROM fact_reviews r
        LEFT JOIN dim_restaurant d ON r.restaurant_id = d.restaurant_id
        WHERE r.restaurant_id IS NOT NULL AND d.restaurant_id IS NULL
    """),
]

for label, sql in relationships:
    check(label, sql)

print("\n=== 4. NUMERIC AND DATE SANITY CHECKS ===")

checks = [
    ("Orders with negative sales_amount", "SELECT COUNT(*) FROM fact_orders WHERE sales_amount < 0"),
    ("Orders with negative delivery time", "SELECT COUNT(*) FROM fact_orders WHERE delivery_time_min < 0"),
    ("Orders with negative item count", "SELECT COUNT(*) FROM fact_orders WHERE items_count < 0"),
    ("Orders with customer rating outside 1-5", "SELECT COUNT(*) FROM fact_orders WHERE customer_rating IS NOT NULL AND (customer_rating < 1 OR customer_rating > 5)"),
    ("Reviews with rating outside 1-5", "SELECT COUNT(*) FROM fact_reviews WHERE review_rating IS NOT NULL AND (review_rating < 1 OR review_rating > 5)"),
    ("Restaurants with rating outside 0-5", "SELECT COUNT(*) FROM dim_restaurant WHERE restaurant_rating IS NOT NULL AND (restaurant_rating < 0 OR restaurant_rating > 5)"),
    ("Order items with non-positive quantity", "SELECT COUNT(*) FROM fact_order_items WHERE quantity IS NULL OR quantity <= 0"),
    ("Order items with negative price", "SELECT COUNT(*) FROM fact_order_items WHERE price < 0"),
]

for label, sql in checks:
    check(label, sql)

print("\n=== 5. ORDER DATE COVERAGE ===")

print(con.execute("""
    SELECT
        MIN(order_date) AS earliest_order,
        MAX(order_date) AS latest_order,
        COUNT(*) FILTER (WHERE order_date IS NULL) AS missing_order_dates
    FROM fact_orders
""").fetchdf().to_string(index=False))

print("\n=== 6. ORDER STATUS DISTRIBUTION ===")

print(con.execute("""
    SELECT order_status, COUNT(*) AS order_count
    FROM fact_orders
    GROUP BY order_status
    ORDER BY order_count DESC
    LIMIT 15
""").fetchdf().to_string(index=False))

print("\nWarehouse validation finished.")
con.close()
