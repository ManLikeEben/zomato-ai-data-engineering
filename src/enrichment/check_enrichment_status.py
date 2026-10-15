import duckdb

DB_PATH = "data/warehouse/zomato.duckdb"

con = duckdb.connect(DB_PATH, read_only=True)

try:
    total_reviews = con.execute("""
        SELECT COUNT(*)
        FROM fact_reviews
        WHERE review_text IS NOT NULL
          AND TRIM(review_text) != ''
    """).fetchone()[0]

    enriched_reviews = con.execute("""
        SELECT COUNT(*)
        FROM review_ai_enrichment
    """).fetchone()[0]

    duplicate_ids = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT review_id
            FROM review_ai_enrichment
            GROUP BY review_id
            HAVING COUNT(*) > 1
        ) AS duplicates
    """).fetchone()[0]

    print("ENRICHMENT STATUS")
    print("=" * 40)
    print(f"Reviews available: {total_reviews:,}")
    print(f"Reviews enriched: {enriched_reviews:,}")
    print(f"Reviews remaining: {total_reviews - enriched_reviews:,}")
    print(f"Duplicate review IDs: {duplicate_ids:,}")

finally:
    con.close()