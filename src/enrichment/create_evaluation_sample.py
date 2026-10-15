import duckdb
import pandas as pd

DB_PATH = "data/warehouse/zomato.duckdb"
OUTPUT_PATH = "data/processed/review_evaluation_sample.csv"

SAMPLE_SIZE = 100
RANDOM_SEED = 42


def main():
    con = duckdb.connect(DB_PATH, read_only=True)

    try:
        reviews = con.execute(
            """
            SELECT
                review_id,
                review_rating,
                review_text
            FROM fact_reviews
            WHERE review_text IS NOT NULL
              AND TRIM(review_text) != ''
            ORDER BY RANDOM()
            LIMIT ?
            """,
            [SAMPLE_SIZE],
        ).fetchdf()

    finally:
        con.close()

    # Create columns for manual labels and model predictions.
    reviews["true_sentiment"] = ""
    reviews["true_aspects"] = ""
    reviews["notes"] = ""

    # Random ordering makes the sample less dependent on review IDs.
    reviews = reviews.sample(
        frac=1,
        random_state=RANDOM_SEED,
    )

    reviews.to_csv(OUTPUT_PATH, index=False)

    print("Evaluation sample created successfully.")
    print(f"Number of reviews: {len(reviews)}")
    print(f"File: {OUTPUT_PATH}")
    print()
    print("Open the CSV and complete these columns:")
    print("  true_sentiment: positive, neutral, negative, or mixed")
    print("  true_aspects: food_quality;delivery;packaging;")
    print("                value_for_money;customer_service")
    print("  notes: optional explanation of ambiguous cases")


if __name__ == "__main__":
    main()