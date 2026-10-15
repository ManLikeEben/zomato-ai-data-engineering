import duckdb

DB_PATH = "data/warehouse/zomato.duckdb"

con = duckdb.connect(DB_PATH, read_only=True)

columns = con.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'review_ai_enrichment'
    ORDER BY ordinal_position
""").fetchall()

print("TABLE COLUMNS:")
for column in columns:
    print(column)

row_count = con.execute("""
    SELECT COUNT(*)
    FROM review_ai_enrichment
""").fetchone()[0]

print("\nNUMBER OF ENRICHED REVIEWS:", row_count)

con.close()