import csv
from pathlib import Path

RAW_DIR = Path("data/raw")

for file_path in sorted(RAW_DIR.glob("*.csv")):
    print(f"\n{'=' * 80}")
    print(f"FILE: {file_path.name}")
    print(f"SIZE: {file_path.stat().st_size / (1024 ** 2):,.2f} MB")

    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)
            headers = next(reader, None)

            if not headers:
                print("WARNING: File is empty.")
                continue

            print(f"COLUMNS ({len(headers)}): {headers}")

            for row_number, row in enumerate(reader, start=1):
                print(f"SAMPLE ROW {row_number}: {row[:12]}")
                if row_number == 3:
                    break

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
