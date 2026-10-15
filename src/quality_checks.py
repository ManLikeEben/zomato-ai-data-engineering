from pathlib import Path
import duckdb

DB_PATH = Path("data/warehouse/zomato.duckdb")
con = duckdb.connect(str(DB_PATH))

try:
    con.execute("SET memory_limit = '3GB'")
    con.execute("SET threads = 2")

    # Primary-key candidates: test for missing and duplicate IDs.
    keys = [
        ("raw_food", "f_id"),
        ("raw_restaurant", "id"),
        ("raw_orders", "order_id"),
        ("raw_order_items", "order_item_id"),
        ("raw_reviews", "review_id"),
        ("raw_users", "user_id"),
    ]

    print("\n=== PRIMARY KEY CHECKS ===")

    for table, key in keys:
        missing, duplicates = con.execute(f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE "{key}" IS NULL OR TRIM("{key}") = ''
                ),
                COUNT(*) - COUNT(DISTINCT "{key}")
            FROM {table}
        """).fetchone()

        print(
            f"{table}.{key}: "
            f"missing={missing:,}, duplicate_excess={duplicates:,}"
        )

    # Foreign-key candidates: count records without matching parent rows.
    relationships = [
        ("raw_orders", "user_id", "raw_users", "user_id"),
        ("raw_orders", "r_id", "raw_restaurant", "id"),
        ("raw_order_items", "order_id", "raw_orders", "order_id"),
        ("raw_reviews", "order_id", "raw_orders", "order_id"),
        ("raw_reviews", "user_id", "raw_users", "user_id"),
        ("raw_reviews", "restaurant_id", "raw_restaurant", "id"),
    ]

    print("\n=== RELATIONSHIP CHECKS ===")

    for child, child_key, parent, parent_key in relationships:
        query = f"""
            SELECT COUNT(*)
            FROM {child} c
            LEFT JOIN {parent} p
                ON c."{child_key}" = p."{parent_key}"
            WHERE c."{child_key}" IS NOT NULL
              AND TRIM(c."{child_key}") <> ''
              AND p."{parent_key}" IS NULL
        """

        orphans = con.execute(query).fetchone()[0]

        print(
            f"{child}.{child_key} -> {parent}.{parent_key}: "
            f"unmatched={orphans:,}"
        )

    print("\nAudit completed. Review the results before making corrections.")

finally:
    con.close()
