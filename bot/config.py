import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
DATABASE_CHANNEL_ID = os.getenv("DATABASE_CHANNEL_ID")

GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]
GEMINI_API_KEYS = [k for k in GEMINI_API_KEYS if k]

MODEL_NAME = "gemini-2.0-flash"
COOLDOWN_TIME = 1
IMAGE_DB_CHANNEL_ID = os.getenv("IMAGE_DB_CHANNEL_ID")
MEMORY_CHANNEL_ID = os.getenv("MEMORY_CHANNEL_ID")
MAX_SEARCH_RESULTS = 3
