import json
import time
from pathlib import Path

import pandas as pd
import requests

from review_classifier import classify_review


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "review_evaluation_sample.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "classifier_comparison_v2.csv"

# Local AI model
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:1.5b"

# Start small so we can benchmark performance
TEST_SIZE = 100


def classify_with_ai(review: str) -> dict:
    """Ask the local Ollama model to classify one review."""

    prompt = f"""
You are a careful restaurant-review analysis system.

Analyse the review below and identify its sentiment and all
aspects explicitly mentioned.

REVIEW:
{review}

PART 1: SENTIMENT

Choose exactly one:
- positive: the review expresses favourable opinions.
- negative: the review expresses unfavourable opinions.
- neutral: the review is neither clearly favourable nor unfavourable.
- mixed: the review expresses both favourable and unfavourable opinions.

Do not assume a review is positive or negative without textual evidence.

PART 2: ASPECTS

Evaluate each category independently.

1. food_quality
   Taste, flavour, freshness, temperature, food preparation,
   portion quality, or food being delicious, stale, oily or tasteless.

2. delivery
   Delivery speed, lateness, early arrival, delivery time,
   arrival experience or delivery delays.

3. packaging
   Packaging quality, containers, bags, spills, leakage,
   damaged packaging or food presentation during transport.

4. value_for_money
   Price, affordability, expense, cost or whether the order
   was worth its price.

5. customer_service
   Staff or delivery-partner behaviour, politeness, helpfulness,
   rudeness or customer support.

IMPORTANT RULES:
- Consider all five aspects separately.
- Return every aspect explicitly supported by the review.
- A review may contain multiple aspects.
- Do not automatically assign food_quality to every review.
- "Arrived earlier than expected" supports delivery.
- "Neatly packed with no spills" supports packaging.
- "Gravy spilled all over the bag" supports packaging.
- "The delivery partner was polite" supports customer_service.
- If an aspect is not mentioned, do not include it.
- If no listed aspect is mentioned, return an empty list.

Return only valid JSON in this format:
{{
    "sentiment": "positive",
    "aspects": ["food_quality", "packaging"]
}}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
        },
        timeout=120,
    )

    response.raise_for_status()

    result = response.json()
    prediction = json.loads(result["message"]["content"])

    sentiment = prediction.get("sentiment")
    aspects = prediction.get("aspects")

    valid_sentiments = {"positive", "neutral", "negative", "mixed"}
    valid_aspects = {
        "food_quality",
        "delivery",
        "packaging",
        "value_for_money",
        "customer_service",
    }

    if sentiment not in valid_sentiments:
        raise ValueError(f"Invalid AI sentiment: {sentiment}")

    if not isinstance(aspects, list):
        raise ValueError("AI aspects must be a list.")

    if not all(aspect in valid_aspects for aspect in aspects):
        raise ValueError(f"Invalid AI aspects: {aspects}")

    return {
        "sentiment": sentiment,
        "aspects": aspects,
    }


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation sample not found: {INPUT_PATH}"
        )

    reviews = pd.read_csv(INPUT_PATH)

    required_columns = {"review_id", "review_text"}

    if not required_columns.issubset(reviews.columns):
        raise ValueError(
            f"CSV must contain these columns: {required_columns}"
        )

    # Limit the initial experiment to a small sample.
    reviews = reviews.head(TEST_SIZE).copy()

    results = []
    start_time = time.time()

    print(f"Comparing classifiers on {len(reviews)} reviews.")
    print(f"AI model: {MODEL_NAME}")
    print("Keep Ollama running while this script executes.\n")

    for index, row in reviews.iterrows():
        review_id = row["review_id"]
        review_text = str(row["review_text"])

        print(
            f"Review {index + 1}/{len(reviews)} "
            f"(ID: {review_id})"
        )

        # Existing Python rule-based classifier
        rule_prediction = classify_review(review_text)

        # Local AI classifier
        try:
            ai_prediction = classify_with_ai(review_text)
            ai_error = ""
        except Exception as error:
            ai_prediction = {
                "sentiment": None,
                "aspects": [],
            }
            ai_error = str(error)

            print(f"  AI classification failed: {error}")

        rule_aspects = set(rule_prediction["aspects"])
        ai_aspects = set(ai_prediction["aspects"])

        results.append(
            {
                "review_id": review_id,
                "review_text": review_text,
                "rule_sentiment": rule_prediction["sentiment"],
                "ai_sentiment": ai_prediction["sentiment"],
                "sentiment_agreement": (
                    rule_prediction["sentiment"]
                    == ai_prediction["sentiment"]
                    if ai_prediction["sentiment"] is not None
                    else None
                ),
                "rule_aspects": ";".join(sorted(rule_aspects)),
                "ai_aspects": ";".join(sorted(ai_aspects)),
                "aspects_agree": (
                    rule_aspects == ai_aspects
                    if ai_prediction["sentiment"] is not None
                    and not ai_error
                    else None
                ),
                "ai_error": ai_error,
            }
        )

        print(f"  Rule-based: {rule_prediction['sentiment']}")
        print(f"  AI:         {ai_prediction['sentiment']}")

    output = pd.DataFrame(results)
    output.to_csv(OUTPUT_PATH, index=False)

    elapsed = time.time() - start_time

    successful = output["ai_error"].eq("").sum()
    sentiment_agreement = (
        output.loc[
            output["ai_error"].eq(""),
            "sentiment_agreement",
        ].mean()
    )

    print("\n" + "=" * 45)
    print("COMPARISON COMPLETE")
    print("=" * 45)
    print(f"Reviews processed: {len(output)}")
    print(f"Successful AI predictions: {successful}")
    print(f"Elapsed time: {elapsed:.1f} seconds")

    if successful:
        print(
            "Sentiment agreement: "
            f"{sentiment_agreement:.1%}"
        )

    print(f"Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()