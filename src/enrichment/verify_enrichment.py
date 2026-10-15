import duckdb

DB_PATH = "data/warehouse/zomato.duckdb"

con = duckdb.connect(DB_PATH, read_only=True)

try:
    # Count the successfully stored AI analyses.
    total = con.execute("""
        SELECT COUNT(*)
        FROM review_ai_enrichment
    """).fetchone()[0]

    print(f"Total enriched reviews: {total}")

    # Display the actual results.
    results = con.execute("""
        SELECT
            review_id,
            sentiment,
            main_theme,
            positive_aspect,
            explanation,
            model_name
        FROM review_ai_enrichment
        ORDER BY review_id
    """).fetchdf()

    print("\nAI ENRICHMENT RESULTS")
    print("=" * 80)
    print(results.to_string(index=False))

finally:
    con.close()