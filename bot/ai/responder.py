from groq import Groq

from bot.config import (
    GROQ_API_KEY,
    MODEL_NAME
)

client = Groq(api_key=GROQ_API_KEY)


def generate_response(
    system_prompt,
    user_message
):

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.4,
        max_tokens=300
    )

    return completion.choices[0].message.content
