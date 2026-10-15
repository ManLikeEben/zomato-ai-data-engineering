from pathlib import Path
import duckdb

db_path = Path("data/warehouse/zomato.duckdb")
con = duckdb.connect(str(db_path))

try:
    con.execute("""
        CREATE TABLE raw_users_safe AS
        SELECT
            user_id,
            "Age",
            "Gender",
            "Marital Status",
            "Occupation",
            "Monthly Income",
            "Educational Qualifications",
            "Family size"
        FROM raw_users
    """)

    con.execute("DROP TABLE raw_users")
    con.execute("ALTER TABLE raw_users_safe RENAME TO raw_users")
    con.execute("CHECKPOINT")

    columns = con.execute("""
        DESCRIBE raw_users
    """).fetchall()

    print("Sanitised raw_users table successfully.")
    print("Remaining columns:")
    for column in columns:
        print(f" - {column[0]}")

finally:
    con.close()
