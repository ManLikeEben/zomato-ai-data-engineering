import time

import duckdb

from enrich_reviews import analyse_review


DB_PATH = "data/warehouse/zomato.duckdb"
BENCHMARK_SIZE = 10


def main():
    con = duckdb.connect(DB_PATH, read_only=True)

    try:
        reviews = con.execute(
            """
            SELECT review_id, review_text
            FROM fact_reviews
            WHERE review_text IS NOT NULL
              AND TRIM(review_text) != ''
            ORDER BY review_id
            LIMIT ?
            """,
            [BENCHMARK_SIZE],
        ).fetchall()

    finally:
        con.close()

    if not reviews:
        print("No reviews available for benchmarking.")
        return

    durations = []
    successful = 0
    failed = 0

    print(f"Benchmarking {len(reviews)} reviews...")
    print("=" * 60)

    for index, (review_id, review_text) in enumerate(reviews, start=1):
        started = time.perf_counter()

        try:
            result = analyse_review(review_text)

            elapsed = time.perf_counter() - started
            durations.append(elapsed)
            successful += 1

            print(
                f"{index}/{len(reviews)} | "
                f"Review {review_id} | "
                f"{elapsed:.1f}s | "
                f"{result['sentiment']}"
            )

        except Exception as error:
            failed += 1
            print(f"{index}/{len(reviews)} | Review {review_id} failed: {error}")

    print("\nBENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if durations:
        average = sum(durations) / len(durations)
        print(f"Average inference time: {average:.1f} seconds")
        print(f"Estimated time for 300,000 reviews: {average * 300000 / 86400:.1f} days")


if __name__ == "__main__":
    main()
