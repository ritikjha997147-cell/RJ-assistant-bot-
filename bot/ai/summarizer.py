from groq import Groq

from bot.config import (
    GROQ_API_KEY,
    MODEL_NAME
)

client = Groq(api_key=GROQ_API_KEY)


def summarize_search_results(search_results):

    combined_text = "\n\n".join(search_results)

    prompt = f"""
Summarize these search results into
SHORT factual bullet points.

Rules:
- Only real facts
- No fake claims
- No exaggeration
- No repetition
- Keep under 120 words

Search Results:
{combined_text}
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=150
    )

    return completion.choices[0].message.content
