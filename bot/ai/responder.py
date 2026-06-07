from google import genai
from groq import Groq
from bot.config import GEMINI_API_KEYS, GROQ_API_KEY, MODEL_NAME

current_key_index = 0

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
            client = genai.Client(api_key=GEMINI_API_KEYS[current_key_index])
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=conversation
            )
            print(f"[AI] Gemini key {current_key_index + 1} used")
            return response.text
        except Exception as e:
            error = str(e).lower()
            if "quota" in error or "429" in error or "exhausted" in error or "limit" in error:
                print(f"[KEY {current_key_index + 1} LIMIT] Switching...")
                current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS)
            else:
                print(f"[GEMINI ERROR]: {e}")
                break

    try:
        print("[AI] Falling back to Groq...")
        groq_client = Groq(api_key=GROQ_API_KEY)
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4,
            max_tokens=1000
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[GROQ ERROR]: {e}")
        return "Abhi thoda busy hoon, thodi der baad try karo!"
