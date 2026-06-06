from google import genai
from google.genai import types
from bot.config import GEMINI_API_KEY, MODEL_NAME

genai.configure(api_key=GEMINI_API_KEY)
model = client = genai.Client(api_key=key)
return client
def generate_response(system_prompt, user_message, history=None):

    conversation = system_prompt + "\n\n"

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conversation += f"{role}: {content}\n"

    conversation += f"user: {user_message}"

response = model.models.generate_content(
    model=MODEL_NAME,
    contents=conversation
)
return response.text
