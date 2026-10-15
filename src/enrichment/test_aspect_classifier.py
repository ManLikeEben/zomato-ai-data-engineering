import re


ASPECT_KEYWORDS = {
    "food_quality": [
        "food",
        "delicious",
        "taste",
        "flavor",
        "fresh",
        "stale",
        "oily",
        "tasteless",
        "cold",
        "hot",
        "gravy",
        "cooked",
        "meal",
    ],
    "delivery": [
        "delivery",
        "delivered",
        "arrived",
        "late",
        "early",
        "rider",
        "hour",
        "partner",
    ],
    "packaging": [
        "packaging",
        "packed",
        "packing",
        "spill",
        "spilled",
        "bag",
        "eco-friendly",
    ],
    "value_for_money": [
        "expensive",
        "overpriced",
        "price",
        "value",
        "worth",
        "rupee",
        "cost",
    ],
    "customer_service": [
        "polite",
        "helpful",
        "rude",
        "service",
        "support",
        "staff",
        "partner",
    ],
}


def identify_aspects(review: str) -> list[str]:
    """Identify aspects explicitly mentioned in a review."""

    text = review.lower()
    detected_aspects = []

    for aspect, keywords in ASPECT_KEYWORDS.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pattern, text):
                detected_aspects.append(aspect)
                break

    return detected_aspects


def main():
    reviews = [
        "Arrived earlier than expected.",
        "Far too expensive for what you get.",
        "Oily, stale and tasteless.",
        "Gravy spilled all over the bag. Quality has really dropped lately.",
        "The delivery partner was rude. Overpriced and not worth it.",
        "Neatly packed with no spills. The delivery partner was polite and helpful.",
        "Authentic taste, cooked perfectly. The delivery partner was polite and helpful.",
    ]

    print("ASPECT CLASSIFIER")
    print("=" * 65)

    for review in reviews:
        aspects = identify_aspects(review)

        print(f"\nReview: {review}")
        print(f"Detected aspects: {aspects}")


if __name__ == "__main__":
    main()