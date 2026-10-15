import re


POSITIVE_WORDS = [
    "delicious",
    "excellent",
    "amazing",
    "great",
    "good",
    "polite",
    "helpful",
    "smooth",
    "friendly",
    "fresh",
    "perfect",
]

NEGATIVE_WORDS = [
    "terrible",
    "awful",
    "late",
    "cold",
    "disappointing",
    "expensive",
    "poor",
    "bad",
    "rude",
    "stale",
    "worst",
]

ASPECT_KEYWORDS = {
    "food_quality": [
        "food", "delicious", "taste", "flavor", "fresh",
        "stale", "oily", "tasteless", "cold", "hot",
        "gravy", "cooked", "meal", "quality",
    ],
    "delivery": [
        "delivery", "delivered", "arrived", "late",
        "early", "rider", "hour",
    ],
    "packaging": [
        "packaging", "packed", "packing", "spill",
        "spilled", "bag", "eco-friendly",
    ],
    "value_for_money": [
        "expensive", "overpriced", "price", "value",
        "worth", "rupee", "cost",
    ],
    "customer_service": [
        "polite", "helpful", "rude", "service",
        "support", "staff",
    ],
}


def find_matches(text: str, words: list[str]) -> list[str]:
    """Return keywords found as whole words in the review."""

    matches = []

    for word in words:
        pattern = r"\b" + re.escape(word) + r"\b"

        if re.search(pattern, text):
            matches.append(word)

    return matches


def identify_aspects(text: str) -> list[str]:
    """Identify all aspects mentioned in the review."""

    detected = []

    for aspect, keywords in ASPECT_KEYWORDS.items():
        if find_matches(text, keywords):
            detected.append(aspect)

    return detected


def classify_review(review: str) -> dict:
    """Combine basic sentiment detection and aspect identification."""

    text = review.lower()

    positive_matches = find_matches(text, POSITIVE_WORDS)
    negative_matches = find_matches(text, NEGATIVE_WORDS)

    # Handle common negation patterns.
    negation_pattern = (
        r"\b(?:not|never|no|hardly)\b"
        r"(?:\s+\w+){0,2}\s+"
    )

    negated_positive = [
        word for word in positive_matches
        if re.search(
            negation_pattern + re.escape(word) + r"\b",
            text,
        )
    ]

    negated_negative = [
        word for word in negative_matches
        if re.search(
            negation_pattern + re.escape(word) + r"\b",
            text,
        )
    ]

    positive_matches = [
        word for word in positive_matches
        if word not in negated_positive
    ]

    negative_matches = [
        word for word in negative_matches
        if word not in negated_negative
    ]

    # Reverse the polarity of directly negated keywords.
    negative_matches.extend(negated_positive)
    positive_matches.extend(negated_negative)

    if positive_matches and negative_matches:
        sentiment = "mixed"
    elif positive_matches:
        sentiment = "positive"
    elif negative_matches:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "aspects": identify_aspects(text),
        "positive_keywords": positive_matches,
        "negative_keywords": negative_matches,
    }


def main():
    reviews = [
        "It was okay, nothing special.",
        "The food was absolutely delicious.",
        "The food was terrible and arrived cold.",
        "The food was good, but delivery was late.",
        "The delivery rider was polite and helpful.",
        "The food was not good.",
        "The food was not terrible.",
        "The food was good, but the terrible delivery ruined everything.",
        "Far too expensive for what you get.",
        "Neatly packed with no spills.",
    ]

    print("COMBINED REVIEW CLASSIFIER")
    print("=" * 65)

    for review in reviews:
        result = classify_review(review)

        print(f"\nReview: {review}")
        print(f"Sentiment: {result['sentiment']}")
        print(f"Aspects: {result['aspects']}")
        print(f"Positive keywords: {result['positive_keywords']}")
        print(f"Negative keywords: {result['negative_keywords']}")


if __name__ == "__main__":
    main()