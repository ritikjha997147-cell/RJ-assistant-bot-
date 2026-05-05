import os
import re
import random
import asyncio
import logging
from datetime import datetime

import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — read from environment variables
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ["BOT_TOKEN"]

# Support up to 4 Gemini API keys (GEMINI_API_KEY_1 … GEMINI_API_KEY_4)
API_KEYS = [
    os.environ[k]
    for k in ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4"]
    if k in os.environ and os.environ[k].strip()
]
# Fallback: single key under GEMINI_API_KEY
if not API_KEYS and "GEMINI_API_KEY" in os.environ:
    API_KEYS = [os.environ["GEMINI_API_KEY"]]

OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

MODEL_LIST = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-pro",
]

MAX_MEMORY = 10

# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------
USER_DATA: dict = {}
GEMINI_CALLS: dict = {i: 0 for i in range(len(API_KEYS))}
LAST_RESET_DATE = datetime.now().date()
gemini_available: bool = bool(API_KEYS)
current_key_index: int = 0

if API_KEYS:
    genai.configure(api_key=API_KEYS[0])

# ---------------------------------------------------------------------------
# Offline knowledge base
# ---------------------------------------------------------------------------
KNOWLEDGE = {
    "greeting": {
        "patterns": ["hi", "hello", "hey", "hii", "helo", "namaste", "namaskar", "salam"],
        "replies": [
            "Arre {name} bhai! Kya haal hai? 😄",
            "Hello {name}! Bol kya scene hai? 🤙",
            "Hey {name}! Kaise ho yaar? 😎",
        ],
    },
    "how_are_you": {
        "patterns": ["kaise ho", "kaisa hai", "how are you", "kya haal", "kya chal raha"],
        "replies": [
            "Ekdum mast {name}! Tu bata? 😄",
            "Bindass hoon yaar! Tera kya haal? 🤙",
            "Sab badhiya {name}! Kya scene hai? 😎",
        ],
    },
    "bye": {
        "patterns": ["bye", "goodbye", "alvida", "baad mein", "phir milenge", "tata"],
        "replies": [
            "Bye {name}! Phir aana 😄",
            "Alvida {name}! Take care 🤙",
            "Chal phir {name}, milte hain! 😎",
        ],
    },
    "thanks": {
        "patterns": ["thanks", "thank you", "shukriya", "dhanyawad", "thx", "ty"],
        "replies": [
            "Arre {name} yaar, koi baat nahi! 😄",
            "Welcome {name}! Kuch aur chahiye? 🤙",
            "No problem {name}! 😎",
        ],
    },
    "bot_name": {
        "patterns": ["tera naam", "your name", "kaun hai tu", "who are you", "kya naam hai"],
        "replies": [
            "Main hoon {bot_name} - RJ ka dost! 😎",
            "Mujhe {bot_name} kehte hain yaar! 🤙",
        ],
    },
    "time": {
        "patterns": ["time kya hai", "what time", "kitne baje", "samay kya hai"],
        "replies": [
            "Abhi {time} baj rahe hain {name}! ⏰",
            "Time hai {time} {name}! ⏰",
        ],
    },
}

DEFAULT_REPLIES = [
    "Bhai {name} abhi thoda busy hoon, baad mein baat karte hain! 😅",
    "Arre {name} yaar, net slow hai abhi! 🐌",
    "Haan {name} sun raha hoon, ek second! 🤔",
]

# ---------------------------------------------------------------------------
# Gemini smart reply
# ---------------------------------------------------------------------------
async def get_smart_reply(user_msg: str, user_id: int, user_name: str) -> str:
    global GEMINI_CALLS, LAST_RESET_DATE, gemini_available, current_key_index

    # Daily quota reset
    if datetime.now().date() != LAST_RESET_DATE:
        GEMINI_CALLS = {i: 0 for i in range(len(API_KEYS))}
        LAST_RESET_DATE = datetime.now().date()
        if not gemini_available and API_KEYS:
            gemini_available = True
            current_key_index = 0
            genai.configure(api_key=API_KEYS[0])

    user_msg_lower = user_msg.lower()

    # 1. Memory init
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"name": user_name, "count": 0, "last_msg": "", "memory": []}
    USER_DATA[user_id]["count"] += 1
    USER_DATA[user_id]["last_msg"] = user_msg

    # 2. Offline knowledge base
    for category, data in KNOWLEDGE.items():
        for pattern in data["patterns"]:
            if re.search(r'\b' + pattern + r'\b', user_msg_lower):
                reply = random.choice(data["replies"]).format(
                    name=user_name,
                    bot_name="RJ Bot",
                    time=datetime.now().strftime("%I:%M %p"),
                    count=USER_DATA[user_id]["count"],
                )
                USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
                if len(USER_DATA[user_id]["memory"]) > MAX_MEMORY:
                    USER_DATA[user_id]["memory"].pop(0)
                return reply

    # 3. Quick math
    if re.search(r'\d+[\+\-\*\/]\d+', user_msg):
        try:
            result = eval(re.sub(r'[^0-9\+\-\*\/\(\)\.]', '', user_msg))
            reply = f"Hisab lagaya {user_name}: {result} 😎"
            USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
            return reply
        except Exception:
            pass

    # 4. No Gemini keys available
    if not gemini_available or not API_KEYS:
        return random.choice(DEFAULT_REPLIES).format(name=user_name)

    # 5. Gemini with key + model fallback (4 keys × 4 models = 16 attempts)
    pichli_baat = " | ".join(USER_DATA[user_id]["memory"][-3:])
    prompt = f"""
Tu RJ ka dost hai - dilli ka chhora, bindass aur savage.
User: {user_name}
Pichli baat: {pichli_baat}
Abhi poocha: {user_msg}

RULE: User kuch bhi puche - padhai, love, coding, topics - sabka jawab dena hai.
Hinglish me 2-3 line me reply de. Emoji use kar.
Agar na pata ho to bhi andaaza laga ke bol de.
"""

    for key_attempt in range(len(API_KEYS)):
        current_key = API_KEYS[current_key_index]
        genai.configure(api_key=current_key)

        for model_name in MODEL_LIST:
            try:
                await asyncio.sleep(0.5)
                model = genai.GenerativeModel(model_name)
                response = await asyncio.to_thread(model.generate_content, prompt)

                if response.text:
                    GEMINI_CALLS[current_key_index] += 1
                    reply = response.text
                    USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
                    if len(USER_DATA[user_id]["memory"]) > MAX_MEMORY:
                        USER_DATA[user_id]["memory"].pop(0)
                    return reply

            except Exception as e:
                error_str = str(e).lower()
                if "404" in error_str or "not found" in error_str:
                    logger.info(f"Model {model_name} unavailable, trying next")
                    continue
                if "429" in error_str or "quota" in error_str or "exhausted" in error_str:
                    logger.warning(f"Key {current_key_index + 1} quota exhausted")
                    break
                logger.error(f"Gemini error [{model_name}]: {e}")
                continue

        # Rotate to next key
        old_index = current_key_index
        current_key_index = (current_key_index + 1) % len(API_KEYS)

        if current_key_index == 0:
            gemini_available = False
            if OWNER_ID:
                try:
                    from telegram import Bot
                    bot = Bot(token=BOT_TOKEN)
                    await bot.send_message(
                        chat_id=OWNER_ID,
                        text="🚨 All Gemini keys exhausted! Will reset tomorrow.",
                    )
                except Exception:
                    pass
            break

        if OWNER_ID:
            try:
                from telegram import Bot
                bot = Bot(token=BOT_TOKEN)
                await bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"🔄 KEY SWITCH: Key {old_index + 1} exhausted → Key {current_key_index + 1} active",
                )
            except Exception:
                pass

    return f"Bhai {user_name} abhi net slow hai 😅 Par sun... {random.choice(['Tu mast banda hai', 'Chai pi le tab tak', 'Meme bhej kya?'])}"


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name or "Bhai"
    logger.info(f"/start from {user.id} ({name})")
    await update.message.reply_text(
        f"Arre {name}! Main hoon RJ Bot 🤖\n"
        "Kuch bhi pooch - main jawab dunga! 😎\n"
        "Bas message bhej de!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_id = user.id
    user_name = user.first_name or "Bhai"
    user_msg = update.message.text.strip()

    logger.info(f"Message from {user_id} ({user_name}): {user_msg[:80]}")

    try:
        reply = await get_smart_reply(user_msg, user_id, user_name)
        await update.message.reply_text(reply)
        logger.info(f"Replied to {user_id}: {reply[:80]}")
    except Exception as e:
        logger.error(f"Error handling message from {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            f"Arre yaar, kuch gadbad ho gayi 😅 Thodi der baad try kar!"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Telegram error: {context.error}", exc_info=context.error)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> None:
    print("Bot starting...", flush=True)
    logger.info("Bot starting...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    if not API_KEYS:
        logger.warning("No Gemini API keys found — bot will use offline replies only")
    else:
        logger.info(f"Loaded {len(API_KEYS)} Gemini API key(s)")

    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)

    print("Handlers registered", flush=True)
    logger.info("Handlers registered")

    print("Bot polling started", flush=True)
    logger.info("Bot polling started")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
