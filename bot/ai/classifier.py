from groq import Groq

from bot.config import (
    GROQ_API_KEY,
    MODEL_NAME
)

client = Groq(api_key=GROQ_API_KEY)


def needs_web_search(user_message):

    prompt = f"""
You are a classifier.

Determine if this message needs
REAL-TIME internet search.

Reply ONLY:
SEARCH
or
NO_SEARCH

Search needed for:
- latest news
- current events
- live prices
- sports
- weather
- trends
- recent updates

User:
{user_message}
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=5
    )

    result = completion.choices[0].message.content.strip()

    return result == "SEARCH"
