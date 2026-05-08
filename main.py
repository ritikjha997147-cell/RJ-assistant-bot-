import os, re, random, asyncio, logging, json, time
import google.generativeai as genai
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote_plus
import aiohttp
from io import BytesIO
import PyPDF2
from difflib import SequenceMatcher

# ===== 1. SETUP =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

API_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 5) if os.getenv(f"GEMINI_API_KEY_{i}")]

MODEL_LIST = ['gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-1.5-flash-8b', 'gemini-2.0-flash-exp']

# ===== 2. GLOBAL VARIABLES (Files Based) =====
USER_DATA = {}
MAX_MEMORY = 10
CUSTOM_COMMANDS_FILE = "custom_commands.json"
LEARNED_REPLIES_FILE = "learned_replies.json"
REMINDERS_FILE = "reminders.json"
CONTACT_INFO = "Owner: @YourUsername"
USER_COOLDOWN = {}
COOLDOWN_TIME = 5
LINK_PATTERN = re.compile(r'http[s]?://|t\.me/|www\.')

# File Loading Logic (Same as yours)
def load_json(file, default):
    try:
        if os.path.exists(file):
            with open(file, 'r') as f: return json.load(f)
    except: pass
    return default

CUSTOM_COMMANDS = load_json(CUSTOM_COMMANDS_FILE, {})
LEARNED_REPLIES = load_json(LEARNED_REPLIES_FILE, {})
REMINDERS = load_json(REMINDERS_FILE, {})

KNOWLEDGE = {
    "greeting": {
        "patterns": ["hi", "hello", "kaise ho", "kya haal", "namaste", "ram ram"],
        "replies": ["Haan bhai {name} 😎 Kya haal hai?", "Oye {name}! 🔥 Bol kya scene", "Namaste {name} 🙏"]
    },
    "sad": {
        "patterns": ["sad", "mood off", "tension"],
        "replies": ["Kya hua {name} 😢 Bata kya dikkat hai? Main hu na"]
    }
}

SMART_FALLBACK = ["Bhai {name} net thoda slow hai 😅", "Arre {name} dimag hang ho gaya 🤯"]
GEMINI_CALLS = {i: 0 for i in range(len(API_KEYS))}
LAST_RESET_DATE = datetime.now().date()
current_key_index = 0

# ===== 3. HELPER FUNCTIONS =====
def save_data(file, data):
    with open(file, 'w') as f: json.dump(data, f, indent=2)

def is_owner(user_id): return user_id == OWNER_ID

async def search_google(query):
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                return data.get('AbstractText')[:500] if data.get('AbstractText') else None
    except: return None

# ===== 4. CORE LOGIC (Same as your request) =====
async def get_smart_reply(user_msg, user_id, user_name):
    global current_key_index
    user_msg_lower = user_msg.lower().strip()

    # Owners DM List Command (Same as yours)
    if any(k in user_msg_lower for k in ["dm list", "users dikhao"]):
        if not is_owner(user_id): return f"Bhai {user_name} owner hi dekh sakta hai 😅"
        msg = f"📬 **Total Users: {len(USER_DATA)}**\n"
        for i, (uid, data) in enumerate(list(USER_DATA.items())[:10], 1):
            msg += f"{i}. {data.get('name')} - {data.get('count')} msgs\n"
        return msg

    # Fuzzy Matching Logic (Same as yours)
    def similar(a, b): return SequenceMatcher(None, a, b).ratio() > 0.6

    for category, data in KNOWLEDGE.items():
        for pattern in data["patterns"]:
            if pattern in user_msg_lower or similar(pattern, user_msg_lower):
                return random.choice(data["replies"]).format(name=user_name)

    # Gemini Key Rotation Logic
    if not API_KEYS: return random.choice(SMART_FALLBACK).format(name=user_name)

    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"name": user_name, "count": 0, "memory": []}
    USER_DATA[user_id]["count"] += 1

    pichli_baat = " | ".join(USER_DATA[user_id]["memory"][-3:])
    prompt = f"Tu RJ ka dost hai dilli ka chhora. User: {user_name}. Past: {pichli_baat}. Query: {user_msg}"

    # Try different keys
    for _ in range(len(API_KEYS)):
        try:
            genai.configure(api_key=API_KEYS[current_key_index])
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = await asyncio.to_thread(model.generate_content, prompt)
            if response.text:
                USER_DATA[user_id]["memory"].append(f"U:{user_msg}|B:{response.text}")
                return response.text
        except Exception as e:
            if "429" in str(e): # Quota hit
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                continue
            break
    
    return random.choice(SMART_FALLBACK).format(name=user_name)

# ===== 5. HANDLERS =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message or not update.message.text: return

    # Cooldown 5s
    now = time.time()
    if user_id in USER_COOLDOWN and now - USER_COOLDOWN[user_id] < COOLDOWN_TIME:
        await update.message.reply_text("Ruk ja bhai! Spam mat kar 😂")
        return
    USER_COOLDOWN[user_id] = now

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await get_smart_reply(update.message.text, user_id, update.effective_user.first_name)
    await update.message.reply_text(reply)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"RJ Bot chalu hai! 😎\nContact: {CONTACT_INFO}")

# ... (Add other handlers like handle_photo, handle_document same as your original) ...

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is Live!")
    app.run_polling()
