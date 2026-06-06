from google import genai
from bot.config import GEMINI_API_KEYS, MODEL_NAME

current_key_index = 0

def get_client():
    global current_key_index
    key = GEMINI_API_KEYS[current_key_index]
    return genai.Client(api_key=key)

def generate_response(system_prompt, user_message, history=None):
    global current_key_index

    conversation = system_prompt + "\n\n"

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conversation += f"{role}: {content}\n"

    conversation += f"user: {user_message}"

    for attempt in range(len(GEMINI_API_KEYS)):
        try:
            client = get_client()
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=conversation
            )
            return response.text

        except Exception as e:
            error = str(e).lower()
            if "quota" in error or "429" in error or "exhausted" in error or "limit" in error:
                print(f"[KEY {current_key_index + 1} LIMIT REACHED] Switching...")
                current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS)
            else:
                raise e

    return "All API keys have reached their limit. Try again later."
