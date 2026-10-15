from pathlib import Path
from collections import Counter

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "classifier_comparison.csv"
)


def parse_aspects(value):
    """Convert a semicolon-separated string into a set of aspects."""

    if pd.isna(value) or not str(value).strip():
        return set()

    return {
        aspect.strip()
        for aspect in str(value).split(";")
        if aspect.strip()
    }


def main():
    df = pd.read_csv(INPUT_PATH)

    python_counts = Counter()
    ai_counts = Counter()
    shared_counts = Counter()
    python_only_counts = Counter()
    ai_only_counts = Counter()

    exact_matches = 0
    partial_matches = 0
    complete_mismatches = 0

    for _, row in df.iterrows():
        python_aspects = parse_aspects(row["rule_aspects"])
        ai_aspects = parse_aspects(row["ai_aspects"])

        python_counts.update(python_aspects)
        ai_counts.update(ai_aspects)

        shared = python_aspects & ai_aspects
        python_only = python_aspects - ai_aspects
        ai_only = ai_aspects - python_aspects

        shared_counts.update(shared)
        python_only_counts.update(python_only)
        ai_only_counts.update(ai_only)

        if python_aspects == ai_aspects:
            exact_matches += 1
        elif shared:
            partial_matches += 1
        else:
            complete_mismatches += 1

    aspects = sorted(
        set(python_counts)
        | set(ai_counts)
        | set(shared_counts)
    )

    print("=" * 60)
    print("ASPECT CLASSIFICATION ANALYSIS")
    print("=" * 60)

    print("\n1. PREDICTION COUNTS BY ASPECT")

    results = []

    for aspect in aspects:
        results.append(
            {
                "aspect": aspect,
                "python_predictions": python_counts[aspect],
                "ai_predictions": ai_counts[aspect],
                "shared_predictions": shared_counts[aspect],
                "python_only": python_only_counts[aspect],
                "ai_only": ai_only_counts[aspect],
            }
        )

    print(pd.DataFrame(results).to_string(index=False))

    total = len(df)

    print("\n2. OVERALL ASPECT AGREEMENT")
    print(f"Total reviews: {total}")
    print(f"Exact matches: {exact_matches}")
    print(f"Partial matches: {partial_matches}")
    print(f"No shared aspects: {complete_mismatches}")

    print("\n3. PERCENTAGES")
    print(f"Exact agreement: {exact_matches / total:.1%}")
    print(f"Partial agreement: {partial_matches / total:.1%}")
    print(f"No shared aspects: {complete_mismatches / total:.1%}")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()