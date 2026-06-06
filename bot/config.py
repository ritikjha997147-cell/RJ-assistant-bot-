import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", 0))

DATABASE_CHANNEL_ID = os.getenv("DATABASE_CHANNEL_ID")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_NAME = "llama-3.1-8b-instant"

COOLDOWN_TIME = 1  # reduced from 5 to 1 second

IMAGE_DB_CHANNEL_ID = os.getenv("IMAGE_DB_CHANNEL_ID")

MEMORY_CHANNEL_ID = os.getenv("MEMORY_CHANNEL_ID")

MAX_SEARCH_RESULTS = 3
