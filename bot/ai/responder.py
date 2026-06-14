from groq import Groq
from bot.config import GROQ_API_KEY, MODEL_NAME

# safe initialization
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def generate_response(system_prompt, user_message, history=None):

    if not client:
        return "❌ AI disabled: GROQ_API_KEY missing"

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    if history:
        messages.extend(history)

    messages.append(
        {"role": "user", "content": user_message}
    )

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.4,
        max_tokens=300
    )

    return completion.choices[0].message.content.strip()