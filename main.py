import os, re, random, asyncio, logging, json, time, sqlite3
from datetime import datetime, timedelta
from io import BytesIO
import aiohttp, PyPDF2
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from rapidfuzz import process
from cachetools import TTLCache

# ===== 1. SETUP & DB =====
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
API_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 5) if os.getenv(f"GEMINI_API_KEY_{i}")]

# Permanent Database Connection
db = sqlite3.connect("rj_bot.db", check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, count INTEGER, memory TEXT)")
db.commit()

# Settings
USER_COOLDOWN = {}
COOLDOWN_TIME = 5 # 5 seconds gap
smart_cache = TTLCache(maxsize=100, ttl=1800)

# ===== 2. KEY MANAGER =====
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
        self.keys[self.idx]["reset"] = time.time() + 900
        self.idx = (self.idx + 1) % len(self.keys)

key_manager = KeyManager(API_KEYS)

# ===== 3. KNOWLEDGE BASE =====
KNOWLEDGE = {
    "greeting": {"patterns": ["hi", "hello", "kaise ho", "hey"], "replies": ["Haan bhai {name} 😎 Bol kya scene?", "Oye {name}! 🔥 Kya haal hai?"]},
    "sad": {"patterns": ["sad", "mood off", "tension"], "replies": ["Bhai {name} tension mat le, main hu na! 💪"]}
}

# ===== 4. CORE FUNCTIONS =====
def get_user_data(user_id, name):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    if not res:
        db.execute("INSERT INTO users VALUES (?, ?, 0, '[]')", (user_id, name))
        db.commit()
        return 0, []
    return res[2], json.loads(res[3])

async def get_smart_reply(user_msg, user_id, user_name):
    user_msg_lower = user_msg.lower().strip()
    
    # Check Cache
    if user_msg_lower in smart_cache: return smart_cache[user_msg_lower]

    # Fuzzy Matching (Instant Reply)
    for cat, data in KNOWLEDGE.items():
        match = process.extractOne(user_msg_lower, data["patterns"], score_cutoff=80)
        if match:
            reply = random.choice(data["replies"]).format(name=user_name)
            smart_cache[user_msg_lower] = reply
            return reply

    # Gemini Integration
    count, memory = get_user_data(user_id, user_name)
    current_key = key_manager.get_key()
    if not current_key: return "Bhai saari keys exhausted hain, thodi der mein try kar 😅"

    genai.configure(api_key=current_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    # Memory management (Last 5 chats)
    pichli_baat = " | ".join(memory[-5:])
    prompt = f"Tu RJ ka dost hai - savage dilli chhora. Context: {pichli_baat}. User {user_name}: {user_msg}"
    
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        reply = response.text
        new_memory = memory + [f"U:{user_msg}", f"B:{reply}"]
        db.execute("UPDATE users SET count=?, memory=? WHERE id=?", (count + 1, json.dumps(new_memory[-10:]), user_id))
        db.commit()
        return reply
    except Exception as e:
        if "429" in str(e): key_manager.mark_dead()
        return "Bhai thoda technical error hai, phir se try kar ☕"

# ===== 5. HANDLERS =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    current_time = time.time()

    # --- 🛡️ SPAM PROTECTION (5 Sec Cooldown) ---
    if user_id in USER_COOLDOWN:
        if current_time - USER_COOLDOWN[user_id] < COOLDOWN_TIME:
            await update.message.reply_text(f"Oye {user_name}, itni jaldi kya hai? 😂 5 sec ruk ja.")
            return
    USER_COOLDOWN[user_id] = current_time

    # --- ✍️ TYING ACTION ---
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1) # Thoda natural feel ke liye

    reply = await get_smart_reply(update.message.text, user_id, user_name)
    await update.message.reply_text(reply)

# ===== 6. RUN BOT =====
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("RJ Bot (Spam Protected) is LIVE! 🚀")
    app.run_polling()
