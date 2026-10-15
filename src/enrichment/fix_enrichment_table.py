import duckdb

DB_PATH = "data/warehouse/zomato.duckdb"

con = duckdb.connect(DB_PATH)

try:
    # Confirm the table is empty before making changes.
    row_count = con.execute("""
        SELECT COUNT(*)
        FROM review_ai_enrichment
    """).fetchone()[0]

    if row_count != 0:
        raise RuntimeError(
            f"Expected an empty table, but found {row_count} records. "
            "Stopping to protect existing AI results."
        )

    # Remove the incorrectly defined, empty table.
    con.execute("DROP TABLE review_ai_enrichment")

    # Recreate it using the correct data type.
    con.execute("""
        CREATE TABLE review_ai_enrichment (
            review_id VARCHAR PRIMARY KEY,
            sentiment VARCHAR,
            main_theme VARCHAR,
            positive_aspect VARCHAR,
            explanation VARCHAR,
            model_name VARCHAR,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("SUCCESS: Table recreated with the correct data types.")

    # Verify the new schema.
    columns = con.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'review_ai_enrichment'
        ORDER BY ordinal_position
    """).fetchall()

    print("\nUPDATED TABLE COLUMNS:")
    for column in columns:
        print(column)

finally:
    con.close()