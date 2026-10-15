from src.text_to_sql.query_service import generate_sql


questions = [
    "What are the top 5 cities by delivered revenue?",
    "How many orders were cancelled in January 2026?",
    "What are the top 10 restaurants by delivered revenue?",
]

for question in questions:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    try:
        sql = generate_sql(question)
        print(f"\nGENERATED SQL:\n{sql}")

    except Exception as error:
        print(f"\nERROR: {error}")