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

NEGATIONS = {
    "not",
    "never",
    "no",
    "hardly",
}


def find_matches(text: str, words: list[str]) -> list[str]:
    """Find whole-word matches without matching inside other words."""
    matches = []

    for word in words:
        pattern = r"\b" + re.escape(word) + r"\b"

        if re.search(pattern, text):
            matches.append(word)

    return matches


def classify_review(review: str) -> dict:
    """Classify a review using simple keyword and negation rules."""

    text = review.lower()
    positive_matches = find_matches(text, POSITIVE_WORDS)
    negative_matches = find_matches(text, NEGATIVE_WORDS)

    # Handle common negation patterns before assigning sentiment.
    negated_positive = []
    negated_negative = []

    for word in positive_matches:
        pattern = (
            r"\b(?:not|never|no|hardly)\b"
            r"(?:\s+\w+){0,2}\s+"
            + re.escape(word)
            + r"\b"
        )

        if re.search(pattern, text):
            negated_positive.append(word)

    for word in negative_matches:
        pattern = (
            r"\b(?:not|never|no|hardly)\b"
            r"(?:\s+\w+){0,2}\s+"
            + re.escape(word)
            + r"\b"
        )

        if re.search(pattern, text):
            negated_negative.append(word)

    # Remove directly negated words from their original categories.
    positive_matches = [
        word for word in positive_matches
        if word not in negated_positive
    ]

    negative_matches = [
        word for word in negative_matches
        if word not in negated_negative
    ]

    # A negated positive word may signal dissatisfaction.
    negative_matches.extend(negated_positive)

    # A negated negative word may signal a positive assessment.
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
        "positive_matches": positive_matches,
        "negative_matches": negative_matches,
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
        "The food was not bad.",
        "The food was fresh and excellent.",
    ]

    print("IMPROVED RULE-BASED CLASSIFIER")
    print("=" * 65)

    for review in reviews:
        result = classify_review(review)

        print(f"\nReview: {review}")
        print(f"Sentiment: {result['sentiment']}")
        print(f"Positive matches: {result['positive_matches']}")
        print(f"Negative matches: {result['negative_matches']}")


if __name__ == "__main__":
    main()