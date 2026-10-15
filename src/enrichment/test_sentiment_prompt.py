from enrich_reviews import analyse_review


test_reviews = [
    "It was okay, nothing special.",
    "The food was absolutely delicious.",
    "The food was terrible and arrived cold.",
    "The food was good, but delivery was late.",
    "The delivery rider was polite and helpful.",
]

for review in test_reviews:
    print("\n" + "=" * 70)
    print(f"Review: {review}")

    try:
        result = analyse_review(review)

        print(f"Sentiment: {result['sentiment']}")
        print(f"Main theme: {result['main_theme']}")
        print(f"Positive aspect: {result['positive_aspect']}")
        print(f"Explanation: {result['explanation']}")

    except Exception as error:
        print(f"Test failed: {error}")