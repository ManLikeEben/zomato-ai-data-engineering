import duckdb

DB_PATH = "data/warehouse/zomato.duckdb"

con = duckdb.connect(DB_PATH, read_only=True)

try:
    results = con.execute("""
        SELECT
            r.review_id,
            r.review_rating,
            r.review_text,
            a.sentiment AS ai_sentiment,
            a.main_theme,
            a.positive_aspect,
            a.explanation
        FROM fact_reviews AS r
        INNER JOIN review_ai_enrichment AS a
            ON r.review_id = a.review_id
        ORDER BY r.review_id
    """).fetchall()

    print(f"Reviews evaluated: {len(results)}")
    print("=" * 100)

    for row in results:
        (
            review_id,
            rating,
            review_text,
            sentiment,
            theme,
            positive_aspect,
            explanation,
        ) = row

        print(f"\nReview ID: {review_id}")
        print(f"Customer rating: {rating}")
        print(f"Original review: {review_text}")
        print(f"AI sentiment: {sentiment}")
        print(f"Main theme: {theme}")
        print(f"Positive aspect: {positive_aspect}")
        print(f"AI explanation: {explanation}")
        print("-" * 100)

finally:
    con.close()