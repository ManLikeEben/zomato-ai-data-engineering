import duckdb


DB_PATH = "data/warehouse/zomato.duckdb"

con = duckdb.connect(DB_PATH, read_only=True)

query = """
    SELECT
        review_id,
        order_id,
        restaurant_id,
        review_rating,
        review_text,
        review_date
    FROM fact_reviews
    WHERE review_text IS NOT NULL
      AND TRIM(review_text) != ''
    LIMIT 5
"""

reviews = con.execute(query).fetchdf()

print("\nSAMPLE CUSTOMER REVIEWS")
print("=" * 60)
print(reviews.to_string(index=False))

con.close()