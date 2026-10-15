from pathlib import Path
import duckdb

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/warehouse/zomato.duckdb")

TABLES = [
    "food",
    "menu",
    "order_items",
    "orders",
    "restaurant",
    "reviews",
    "users",
]

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DB_PATH))

try:
    con.execute("SET memory_limit = '3GB'")
    con.execute("SET threads = 2")

    for name in TABLES:
        csv_path = RAW_DIR / f"{name}.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"Missing source file: {csv_path}")

        safe_path = csv_path.resolve().as_posix().replace("'", "''")
        table_name = f"raw_{name}"

        print(f"\nLoading {csv_path.name}...", flush=True)

        con.execute(
            f"""
            CREATE OR REPLACE TABLE {table_name} AS
            SELECT *
            FROM read_csv_auto(
                '{safe_path}',
                header = true,
                all_varchar = true
            )
            """
        )

        row_count = con.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

        print(
            f"Loaded {table_name}: {row_count:,} rows",
            flush=True,
        )

    print("\nAll seven source tables loaded successfully.")
    print(f"Database: {DB_PATH.resolve()}")

finally:
    con.close()
