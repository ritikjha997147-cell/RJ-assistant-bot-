from google import genai
from bot.config import GEMINI_API_KEYS, MODEL_NAME

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

User: {user_message}
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEYS[0])
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        result = response.text.strip()
        return result == "SEARCH"

    except Exception as e:
        print(f"[CLASSIFIER ERROR]: {e}")
        return False