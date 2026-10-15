from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "classifier_comparison_v2.csv"
)


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Comparison file not found: {INPUT_PATH}"
        )

    df = pd.read_csv(INPUT_PATH)
    total = len(df)

    print("=" * 55)
    print("CLASSIFIER COMPARISON ANALYSIS")
    print("=" * 55)

    print(f"\nTotal reviews analysed: {total}")

    # 1. Sentiment distributions
    print("\n1. RULE-BASED SENTIMENT DISTRIBUTION")
    print(df["rule_sentiment"].value_counts(dropna=False).to_string())

    print("\n2. AI SENTIMENT DISTRIBUTION")
    print(df["ai_sentiment"].value_counts(dropna=False).to_string())

    # 2. Keep only successful AI predictions
    successful = df["ai_error"].fillna("").eq("")
    valid = df.loc[successful].copy()

    # Explicitly convert agreement columns to Boolean values
    valid["sentiment_agreement"] = (
        valid["sentiment_agreement"].astype(str).str.lower()
        .map({"true": True, "false": False, "1": True, "0": False})
    )

    valid["aspects_agree"] = (
        valid["aspects_agree"].astype(str).str.lower()
        .map({"true": True, "false": False, "1": True, "0": False})
    )

    print("\n3. SENTIMENT AGREEMENT")

    sentiment_valid = valid["sentiment_agreement"].dropna()

    print(f"Successful AI predictions: {len(valid)}")
    print(f"Comparable sentiment predictions: {len(sentiment_valid)}")

    if len(sentiment_valid):
        agreement = sentiment_valid.mean()
        disagreements_count = (~sentiment_valid).sum()

        print(f"Agreement: {agreement:.1%}")
        print(f"Disagreements: {disagreements_count}")

    # 4. Disagreement patterns
    disagreements = valid.loc[
        valid["sentiment_agreement"] == False
    ]

    print("\n4. DISAGREEMENT PATTERNS")

    if disagreements.empty:
        print("No sentiment disagreements found.")
    else:
        patterns = (
            disagreements.groupby(["rule_sentiment", "ai_sentiment"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )

        print(patterns.to_string(index=False))

    # 5. Aspect agreement
    aspect_valid = valid["aspects_agree"].dropna()

    print("\n5. ASPECT AGREEMENT")

    if len(aspect_valid):
        print(f"Comparable predictions: {len(aspect_valid)}")
        print(f"Exact agreement: {aspect_valid.mean():.1%}")
        print(f"Disagreements: {(~aspect_valid).sum()}")
    else:
        print("No valid aspect comparisons available.")

    # 6. Save sentiment disagreements
    output_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "classifier_disagreements.csv"
    )

    disagreements.to_csv(output_path, index=False)

    print("\n6. OUTPUT FILE")
    print(f"Disagreements saved to: {output_path}")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()