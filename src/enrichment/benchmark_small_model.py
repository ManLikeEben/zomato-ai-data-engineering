import json
import time
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:1.5b"
REQUEST_TIMEOUT = 180


def analyse_review(review_text: str) -> dict:
    prompt = f"""
Classify this food delivery review.

Review: {review_text}

Return JSON with exactly these keys:
- sentiment: positive, neutral, or negative
- main_theme: the main subject
- positive_aspect: an explicitly positive detail, otherwise null
- explanation: one short sentence

Rules:
- Positive means clear praise or satisfaction.
- Neutral means acceptable or uneventful without clear overall sentiment.
- Negative means clear dissatisfaction or criticism.
- For mixed reviews, acknowledge both positive and negative details.
- Do not invent information.
- The positive_aspect must contain an actual positive detail from the review.
- The explanation must agree with the sentiment.
- Return JSON only.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    result = json.loads(response.json()["message"]["content"])

    required_keys = {
        "sentiment",
        "main_theme",
        "positive_aspect",
        "explanation",
    }

    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object.")

    if not required_keys.issubset(result):
        raise ValueError("Required fields are missing.")

    if result["sentiment"] not in {
        "positive", "neutral", "negative"
    }:
        raise ValueError("Invalid sentiment.")

    return result


def main():
    test_reviews = [
        "It was okay, nothing special.",
        "The food was absolutely delicious.",
        "The food was terrible and arrived cold.",
        "The food was good, but delivery was late.",
        "The delivery rider was polite and helpful.",
    ]

    durations = []

    print(f"Testing {MODEL} with five reviews")
    print("=" * 60)

    for index, review in enumerate(test_reviews, start=1):
        started = time.perf_counter()

        try:
            result = analyse_review(review)
            elapsed = time.perf_counter() - started
            durations.append(elapsed)

            print(f"\nTest {index}: {review}")
            print(f"Sentiment: {result['sentiment']}")
            print(f"Theme: {result['main_theme']}")
            print(f"Positive aspect: {result['positive_aspect']}")
            print(f"Explanation: {result['explanation']}")
            print(f"Time: {elapsed:.1f} seconds")

        except (
            requests.RequestException,
            json.JSONDecodeError,
            KeyError,
            ValueError,
        ) as error:
            print(f"\nTest {index} failed: {error}")

    if durations:
        average = sum(durations) / len(durations)

        print("\nBENCHMARK SUMMARY")
        print("=" * 60)
        print(f"Successful requests: {len(durations)}/5")
        print(f"Average time: {average:.1f} seconds")
        print(
            "Estimated time for 300,000 reviews: "
            f"{average * 300000 / 86400:.1f} days"
        )


if __name__ == "__main__":
    main()