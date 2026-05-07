import os, re, random, asyncio, logging, json, time, sqlite3
from datetime import datetime, timedelta
from io import BytesIO
import aiohttp, PyPDF2
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from rapidfuzz import process # Fast Fuzzy Matching
from cachetools import TTLCache # RAM Caching

# ===== 1. CONFIG & DB SETUP =====
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
API_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 5) if os.getenv(f"GEMINI_API_KEY_{i}")]

# SQLite: Permanent Memory (0 Rs Cost)
db = sqlite3.connect("rj_bot.db", check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, count INTEGER, memory TEXT)")
db.commit()

# Cache: Gemini calls bachane ke liye (30 min TTL)
smart_cache = TTLCache(maxsize=100, ttl=1800)

# ===== 2. SMART MANAGERS =====
class KeyManager:
    def __init__(self, keys):
        self.keys = [{"key": k, "active": True, "reset": 0} for k in keys]
        self.idx = 0
    def get_key(self):
        for _ in range(len(self.keys)):
            k = self.keys[self.idx]
            if k["active"] or time.time() > k["reset"]: return k["key"]
            self.idx = (self.idx + 1) % len(self.keys)
        return None
    def mark_dead(self):
        self.keys[self.idx]["active"] = False
        self.keys[self.idx]["reset"] = time.time() + 900 # 15 min ban
        self.idx = (self.idx + 1) % len(self.keys)

key_manager = KeyManager(API_KEYS)

# ===== 3. CORE LOGIC (FUZZY + DB) =====
def get_db_user(user_id, name):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    if not res:
        db.execute("INSERT INTO users VALUES (?, ?, 0, '[]')", (user_id, name))
        db.commit()
        return {"count": 0, "memory": []}
    return {"count": res[2], "memory": json.loads(res[3])}

def save_db_user(user_id, count, memory):
    db.execute("UPDATE users SET count=?, memory=? WHERE id=?", (count + 1, json.dumps(memory[-5:]), user_id))
    db.commit()

# KNOWLEDGE BASE (Same as yours but faster)
KNOWLEDGE = {
    "greeting": {"patterns": ["hi", "hello", "kaise ho", "kya haal"], "replies": ["Haan bhai {name} 😎 Bol kya scene?"]},
    "sad": {"patterns": ["sad", "mood off", "tension"], "replies": ["Bhai {name} tension mat le, main hu na! 💪"]}
}

async def get_smart_reply(user_msg, user_id, user_name):
    user_msg_lower = user_msg.lower().strip()
    
    # 1. Cache Check
    if user_msg_lower in smart_cache: return smart_cache[user_msg_lower]

    # 2. RapidFuzz Matching (Better than SequenceMatcher)
    for cat, data in KNOWLEDGE.items():
        match = process.extractOne(user_msg_lower, data["patterns"], score_cutoff=80)
        if match:
            reply = random.choice(data["replies"]).format(name=user_name)
            smart_cache[user_msg_lower] = reply
            return reply

    # 3. Gemini Logic with Key Rotation
    user_data = get_db_user(user_id, user_name)
    current_key = key_manager.get_key()
    if not current_key: return "Bhai server down hai, 15 min baad try kar 😅"

    genai.configure(api_key=current_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"Tu RJ ka dost hai - dilli ka savage chhora. User {user_name} ne pucha: {user_msg}"
    
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        reply = response.text
        save_db_user(user_id, user_data["count"], user_data["memory"] + [f"U:{user_msg}"])
        return reply
    except Exception as e:
        if "429" in str(e): key_manager.mark_dead()
        return "Bhai thoda busy hu, fir se bol? ☕"

# ===== 4. HANDLERS =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user = update.effective_user
    reply = await get_smart_reply(update.message.text, user.id, user.first_name)
    await update.message.reply_text(reply)

# ===== 5. START BOT =====
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("RJ Bot Optimized Version is LIVE! 🚀")
    app.run_polling()
