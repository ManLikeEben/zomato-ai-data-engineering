from src.text_to_sql.execution_service import execute_query


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
        sql, result = execute_query(question)

        print("\nSQL EXECUTED:")
        print(sql)

        print("\nQUERY RESULT:")
        print(result.to_string(index=False))

    except Exception as error:
        print(f"\nERROR: {error}")