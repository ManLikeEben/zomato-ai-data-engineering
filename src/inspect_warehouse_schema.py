import duckdb

con = duckdb.connect("data/warehouse/zomato.duckdb", read_only=True)

for table in ["dim_restaurant", "dim_user", "dim_food", "fact_orders", "fact_order_items", "fact_reviews"]:
    print(f"\n{table}:")
    for row in con.execute(f"DESCRIBE {table}").fetchall():
        print(f"  {row[0]} ({row[1]})")

con.close()
