import os
from dotenv import load_dotenv
import pathlib

# force correct path
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

def get(key, default=None):
    value = os.getenv(key, default)
    return value

# CORE KEYS
BOT_TOKEN = get("BOT_TOKEN")
GROQ_API_KEY = get("GROQ_API_KEY")

# OPTIONAL KEYS (SAFE)
OWNER_ID = int(get("OWNER_ID", 0) or 0)
DATABASE_CHANNEL_ID = get("DATABASE_CHANNEL_ID", "")
IMAGE_DB_CHANNEL_ID = get("IMAGE_DB_CHANNEL_ID", "")
MEMORY_CHANNEL_ID = get("MEMORY_CHANNEL_ID", "")

MODEL_NAME = "llama-3.1-8b-instant"
COOLDOWN_TIME = 5
MAX_SEARCH_RESULTS = 3