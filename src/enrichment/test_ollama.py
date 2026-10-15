import json
import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"

review = """
The food was terrible, but the delivery rider was very polite.
"""

prompt = f"""
Analyse the following customer review.

Review:
{review}

Return a JSON object with exactly these four keys:
- sentiment: "positive", "neutral", or "negative"
- main_theme: a short description of the main complaint or topic
- positive_aspect: an exact positive detail from the review, or null
- explanation: one short sentence explaining the sentiment

Rules:
1. Read the entire review before answering.
2. Extract positive details even when the overall sentiment is negative.
3. If the review praises a delivery rider, include that praise in positive_aspect.
4. Never use null if the review contains an explicit positive detail.
5. Do not invent information.
6. Return valid JSON only, without Markdown fences.
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
        "stream": False,
    },
    timeout=180,
)

response.raise_for_status()

result = response.json()

ai_text = result["message"]["content"]

try:
    analysis = json.loads(ai_text)

    print("\nAI REVIEW ANALYSIS")
    print("=" * 40)

    print("Sentiment:", analysis["sentiment"])
    print("Main theme:", analysis["main_theme"])
    print("Positive aspect:", analysis["positive_aspect"])
    print("Explanation:", analysis["explanation"])

except (json.JSONDecodeError, KeyError) as error:
    print("Could not parse the AI response.")
    print("Error:", error)
    print("Raw response:", ai_text)