import re
import duckdb
from collections import Counter

DB_PATH = "data/warehouse/zomato.duckdb"


def main():
    con = duckdb.connect(DB_PATH, read_only=True)

    try:
        # Basic dataset statistics
        stats = con.execute("""
            SELECT
                COUNT(*) AS total_reviews,
                COUNT(*) FILTER (
                    WHERE review_text IS NULL
                       OR TRIM(review_text) = ''
                ) AS empty_reviews,
                COUNT(*) FILTER (
                    WHERE LENGTH(TRIM(review_text)) < 20
                ) AS short_reviews,
                AVG(LENGTH(review_text)) AS average_review_length
            FROM fact_reviews
        """).fetchone()

        print("REVIEW DATASET PROFILE")
        print("=" * 60)
        print(f"Total reviews: {stats[0]:,}")
        print(f"Empty reviews: {stats[1]:,}")
        print(f"Reviews under 20 characters: {stats[2]:,}")
        print(
            "Average review length: "
            f"{stats[3]:.1f} characters"
            if stats[3] is not None
            else "Average review length: unavailable"
        )

        # Review length distribution
        length_groups = con.execute("""
            SELECT
                CASE
                    WHEN LENGTH(TRIM(review_text)) < 20
                        THEN 'Under 20 characters'
                    WHEN LENGTH(TRIM(review_text)) < 50
                        THEN '20-49 characters'
                    WHEN LENGTH(TRIM(review_text)) < 100
                        THEN '50-99 characters'
                    ELSE '100+ characters'
                END AS length_group,
                COUNT(*) AS review_count
            FROM fact_reviews
            WHERE review_text IS NOT NULL
              AND TRIM(review_text) != ''
            GROUP BY length_group
            ORDER BY MIN(LENGTH(TRIM(review_text)))
        """).fetchall()

        print("\nREVIEW LENGTH DISTRIBUTION")
        print("-" * 60)

        for group, count in length_groups:
            print(f"{group}: {count:,}")

        # Inspect a sample of real reviews
        reviews = con.execute("""
            SELECT review_id, review_rating, review_text
            FROM fact_reviews
            WHERE review_text IS NOT NULL
              AND TRIM(review_text) != ''
            ORDER BY review_id
            LIMIT 30
        """).fetchall()

        print("\nSAMPLE OF REAL REVIEWS")
        print("-" * 60)

        for review_id, rating, text in reviews:
            print(f"\nID: {review_id} | Rating: {rating}")
            print(text[:300].replace("\n", " "))

        # Count common keywords in a sample
        positive_words = [
            "good", "great", "excellent", "delicious",
            "fresh", "amazing", "perfect", "helpful",
            "polite", "smooth"
        ]

        negative_words = [
            "bad", "terrible", "awful", "late",
            "cold", "poor", "expensive", "rude",
            "disappointing", "stale"
        ]

        negation_words = [
            "not", "never", "no", "hardly", "isn't",
            "wasn't", "don't", "didn't", "couldn't"
        ]

        sample_texts = con.execute("""
            SELECT review_text
            FROM fact_reviews
            WHERE review_text IS NOT NULL
              AND TRIM(review_text) != ''
            ORDER BY review_id
            LIMIT 10000
        """).fetchall()

        positive_counts = Counter()
        negative_counts = Counter()
        negation_counts = Counter()

        for (review_text,) in sample_texts:
            text = review_text.lower()

            for word in positive_words:
                if re.search(r"\b" + re.escape(word) + r"\b", text):
                    positive_counts[word] += 1

            for word in negative_words:
                if re.search(r"\b" + re.escape(word) + r"\b", text):
                    negative_counts[word] += 1

            for word in negation_words:
                if re.search(r"\b" + re.escape(word) + r"\b", text):
                    negation_counts[word] += 1

        print("\nKEYWORD FREQUENCIES IN FIRST 10,000 REVIEWS")
        print("-" * 60)

        print("\nPositive keywords:")
        for word, count in positive_counts.most_common():
            print(f"{word}: {count:,}")

        print("\nNegative keywords:")
        for word, count in negative_counts.most_common():
            print(f"{word}: {count:,}")

        print("\nNegation keywords:")
        for word, count in negation_counts.most_common():
            print(f"{word}: {count:,}")

    finally:
        con.close()


if __name__ == "__main__":
    main()