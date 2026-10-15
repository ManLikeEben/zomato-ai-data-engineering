import json
import time

import duckdb
import requests


DB_PATH = "data/warehouse/zomato.duckdb"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"

BATCH_SIZE = 5
REQUEST_TIMEOUT = 180


def analyse_review(review_text: str) -> dict:
    """Analyse one customer review using the local Ollama model."""

    prompt = f"""
You are an expert customer feedback analyst for a food delivery business.

Analyse the complete customer review below.

REVIEW:
{review_text}

Return a JSON object with exactly these keys:
- sentiment
- main_theme
- positive_aspect
- explanation

SENTIMENT RULES:

1. positive:
   The overall review expresses satisfaction, praise, or enjoyment.

2. neutral:
   The review describes an ordinary, acceptable, or uneventful
   experience without a clear overall positive or negative judgement.

3. negative:
   The overall review expresses dissatisfaction, disappointment,
   criticism, or a clearly bad experience.

4. For mixed reviews, consider both positive and negative details
   and classify the overall sentiment according to the review's
   overall meaning. Do not ignore either side.

POSITIVE ASPECT RULES:

1. Extract an explicitly positive detail from the review.
2. Use a short phrase that preserves the customer's meaning.
3. For "The food was absolutely delicious", return
   "absolutely delicious food".
4. For "The food was good, but delivery was late", return
   "good food".
5. For "The delivery rider was polite and helpful", return
   "polite and helpful delivery rider".
6. Return null only when the review contains no identifiable
   positive detail.
7. Never invent a positive aspect.

MAIN THEME RULES:

Identify the main subject, such as food quality, delivery,
customer service, packaging, or value for money.
For mixed reviews, the theme may mention both subjects.

EXPLANATION RULES:

Explain the classification in one concise sentence.
The explanation must agree with the sentiment label.
For mixed reviews, acknowledge both positive and negative details.

Return valid JSON only.
Do not include Markdown fences or text outside the JSON.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0,
            },
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    response_text = response.json()["message"]["content"]
    analysis = json.loads(response_text)

    required_keys = {
        "sentiment",
        "main_theme",
        "positive_aspect",
        "explanation",
    }

    if not isinstance(analysis, dict):
        raise ValueError("The AI response must be a JSON object.")

    if not required_keys.issubset(analysis.keys()):
        raise ValueError("The AI response is missing required fields.")

    sentiment = analysis["sentiment"]

    if not isinstance(sentiment, str):
        raise ValueError("Sentiment must be a string.")

    sentiment = sentiment.strip().lower()

    if sentiment not in {"positive", "neutral", "negative"}:
        raise ValueError(f"Unexpected sentiment: {sentiment}")

    if not isinstance(analysis["main_theme"], str):
        raise ValueError("Main theme must be a string.")

    if analysis["positive_aspect"] is not None and not isinstance(
        analysis["positive_aspect"], str
    ):
        raise ValueError("Positive aspect must be a string or null.")

    if not isinstance(analysis["explanation"], str):
        raise ValueError("Explanation must be a string.")

    analysis["sentiment"] = sentiment
    analysis["main_theme"] = analysis["main_theme"].strip()
    analysis["explanation"] = analysis["explanation"].strip()

    if isinstance(analysis["positive_aspect"], str):
        analysis["positive_aspect"] = analysis["positive_aspect"].strip()

    return analysis


def main():
    con = duckdb.connect(DB_PATH)

    try:
        # Store AI results separately; preserve the original reviews.
        con.execute("""
            CREATE TABLE IF NOT EXISTS review_ai_enrichment (
                review_id VARCHAR PRIMARY KEY,
                sentiment VARCHAR,
                main_theme VARCHAR,
                positive_aspect VARCHAR,
                explanation VARCHAR,
                model_name VARCHAR,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Select reviews that have not already been processed.
        reviews = con.execute(
            """
            SELECT
                review_id,
                review_text
            FROM fact_reviews
            WHERE review_text IS NOT NULL
              AND TRIM(review_text) != ''
              AND review_id NOT IN (
                  SELECT review_id
                  FROM review_ai_enrichment
              )
            ORDER BY review_id
            LIMIT ?
            """,
            [BATCH_SIZE],
        ).fetchall()

        if not reviews:
            print("No unprocessed reviews found.")
            return

        print(f"Processing {len(reviews)} reviews...")

        started = time.perf_counter()
        successful = 0
        failed = 0

        for review_id, review_text in reviews:
            try:
                analysis = analyse_review(review_text)

                con.execute(
                    """
                    INSERT INTO review_ai_enrichment (
                        review_id,
                        sentiment,
                        main_theme,
                        positive_aspect,
                        explanation,
                        model_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        review_id,
                        analysis["sentiment"],
                        analysis["main_theme"],
                        analysis["positive_aspect"],
                        analysis["explanation"],
                        MODEL,
                    ],
                )

                successful += 1

                print(
                    f"[{successful + failed}/{len(reviews)}] "
                    f"Review {review_id}: {analysis['sentiment']}"
                )

            except (
                requests.RequestException,
                json.JSONDecodeError,
                KeyError,
                ValueError,
            ) as error:
                failed += 1
                print(f"Review {review_id} failed: {error}")

        elapsed = time.perf_counter() - started

        print("\nBATCH SUMMARY")
        print("=" * 40)
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Elapsed time: {elapsed:.1f} seconds")

    finally:
        con.close()


if __name__ == "__main__":
    main()