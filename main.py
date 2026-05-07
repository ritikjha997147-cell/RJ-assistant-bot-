import os
import re
import random
import asyncio
import logging
import json
import time
import google.generativeai as genai
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== 1. SETUP =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
]
API_KEYS = [key for key in API_KEYS if key]

MODEL_LIST = [
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro-latest',
    'gemini-1.5-flash-8b',
    'gemini-2.0-flash-exp'
]

# ===== 2. GLOBAL VARIABLES =====
USER_DATA = {}
MAX_MEMORY = 10
CUSTOM_COMMANDS_FILE = "custom_commands.json"
LEARNED_REPLIES_FILE = "learned_replies.json" # ← NAYA: Learning ke liye
CONTACT_INFO = "Owner: @YourUsername"
USER_COOLDOWN = {}
COOLDOWN_TIME = 5

# Load custom commands from file
try:
    with open(CUSTOM_COMMANDS_FILE, 'r') as f:
        CUSTOM_COMMANDS = json.load(f)
except:
    CUSTOM_COMMANDS = {}

# ← NAYA: Learned replies load karo
try:
    with open(LEARNED_REPLIES_FILE, 'r') as f:
        LEARNED_REPLIES = json.load(f)
except:
    LEARNED_REPLIES = {}

KNOWLEDGE = {
    "greeting": {
        "patterns": ["hi", "hello", "hey", "namaste"],
        "replies": ["Haan bhai {name} 😎", "Kya haal {name}?", "Bol {name} kya scene hai"]
    }
}

SMART_FALLBACK = [
    "Bhai {name} net thoda slow hai 😅 Par tu suna kya haal hai?",
    "Arre {name} server busy hai. Tu chai pi le tab tak, main aa raha 2 min me ☕",
    "Bhai {name} dimag hang ho gaya mera 🤯 Tu 2 sec me phir se pooch le",
    "Oye {name} connection week hai aaj 😂 Par tu mast banda hai, bol kya help chahiye?",
    "Bhai {name} technical dikkat aa gayi 💀 Par apni dosti to pakki hai na?"
]

DEFAULT_REPLIES = ["Bhai {name} samjha nahi 😅", "Phir se bol {name}"]
GEMINI_CALLS = {i: 0 for i in range(len(API_KEYS))}
LAST_RESET_DATE = datetime.now().date()
gemini_available = len(API_KEYS) > 0
current_key_index = 0

if gemini_available:
    genai.configure(api_key=API_KEYS[0])
    os.environ["GRPC_DNS_RESOLVER"] = "native"

# ===== 3. HELPER FUNCTIONS =====
def save_custom_commands():
    with open(CUSTOM_COMMANDS_FILE, 'w') as f:
        json.dump(CUSTOM_COMMANDS, f, indent=2)

# ← NAYA: Learned replies save karne ka function
def save_learned_replies():
    with open(LEARNED_REPLIES_FILE, 'w') as f:
        json.dump(LEARNED_REPLIES, f, indent=2)

def is_owner(user_id):
    return user_id == OWNER_ID

def check_cooldown(user_id):
    current_time = time.time()
    if user_id in USER_COOLDOWN:
        if current_time - USER_COOLDOWN[user_id] < COOLDOWN_TIME:
            return False
    USER_COOLDOWN[user_id] = current_time
    return True

# ===== 4. SMART REPLY FUNCTION =====
async def get_smart_reply(user_msg, user_id, user_name):
    global GEMINI_CALLS, LAST_RESET_DATE, gemini_available, current_key_index

    if datetime.now().date()!= LAST_RESET_DATE:
        GEMINI_CALLS = {i: 0 for i in range(len(API_KEYS))}
        LAST_RESET_DATE = datetime.now().date()
        if not gemini_available and len(API_KEYS) > 0:
            gemini_available = True
            current_key_index = 0
            genai.configure(api_key=API_KEYS[0])

    user_msg_lower = user_msg.lower()

    # 0. CUSTOM COMMAND CHECK
    if user_msg_lower in CUSTOM_COMMANDS:
        return CUSTOM_COMMANDS[user_msg_lower].format(name=user_name)

    # ← NAYA: LEARNED REPLIES CHECK - Sabse pehle
    if user_msg_lower in LEARNED_REPLIES:
        reply = random.choice(LEARNED_REPLIES[user_msg_lower]).format(name=user_name)
        return reply

    # 1. MEMORY UPDATE
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"name": user_name, "count": 0, "last_msg": "", "memory": []}
    USER_DATA[user_id]["count"] += 1
    USER_DATA[user_id]["last_msg"] = user_msg

    # 2. OFFLINE BRAIN
    for category, data in KNOWLEDGE.items():
        for pattern in data["patterns"]:
            if re.search(r'\b' + pattern + r'\b', user_msg_lower):
                reply = random.choice(data["replies"])
                reply = reply.format(name=user_name, bot_name="RJ Bot", time=datetime.now().strftime("%I:%M %p"), count=USER_DATA[user_id]["count"])
                USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
                if len(USER_DATA[user_id]["memory"]) > MAX_MEMORY:
                    USER_DATA[user_id]["memory"].pop(0)
                return reply

    # 3. MATH
    if re.search(r'\d+[\+\-\*\/]\d+', user_msg):
        try:
            result = eval(re.sub(r'[^0-9\+\-\*\/\(\)\.]', '', user_msg))
            reply = f"Hisab lagaya {user_name}: {result} 😎"
            USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
            return reply
        except:
            pass

    # 4. GEMINI FALLBACK
    if not gemini_available:
        reply = random.choice(SMART_FALLBACK).format(name=user_name)
        return reply

    pichli_baat = " | ".join(USER_DATA[user_id]["memory"][-3:])
    prompt = f"""
    Tu RJ ka dost hai - dilli ka chhora, bindass aur savage.
    User: {user_name}
    Pichli baat: {pichli_baat}
    Abhi poocha: {user_msg}

    RULE: User kuch bhi puche - padhai, love, coding, politics - sabka jawab dena hai.
    Koi mana nahi karna. Hinglish me 2-3 line me reply de. Emoji use kar.
    Insan jaisa dosti wala reply de, robot jaisa nahi.
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
                    logger.info(f"Model {model_name} band hai")
                    continue
                if "429" in error_str or "quota" in error_str:
                    logger.error(f"Key {current_key_index+1} Quota Khatam")
                    break
                else:
                    continue

        old_index = current_key_index
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        if current_key_index == 0:
            gemini_available = False
            try:
                await app.bot.send_message(chat_id=OWNER_ID, text=f"🚨 SABHI 4 KEYS FAIL 🚨")
            except: pass
            break
        try:
            await app.bot.send_message(chat_id=OWNER_ID, text=f"🔄 KEY SWITCH\nKey {old_index+1} → Key {current_key_index+1}")
        except: pass

    reply = random.choice(SMART_FALLBACK).format(name=user_name)
    USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
    return reply

# ===== 5. OWNER COMMANDS =====
async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Bhai ye command sirf owner ke liye hai 😅")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Use: /addcmd command reply\nexample: /addcmd price Bot ka price 499 hai")
        return

    cmd = context.args[0].lower()
    reply = " ".join(context.args[1:])
    CUSTOM_COMMANDS[cmd] = reply
    save_custom_commands()
    await update.message.reply_text(f"✅ Command add ho gayi: {cmd} → {reply}")

async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Bhai ye command sirf owner ke liye hai 😅")
        return

    if not context.args:
        await update.message.reply_text("Use: /delcmd command")
        return

    cmd = context.args[0].lower()
    if cmd in CUSTOM_COMMANDS:
        del CUSTOM_COMMANDS[cmd]
        save_custom_commands()
        await update.message.reply_text(f"✅ Command delete ho gayi: {cmd}")
    else:
        await update.message.reply_text(f"❌ Command nahi mili: {cmd}")

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not CUSTOM_COMMANDS:
        await update.message.reply_text("Koi custom command nahi hai abhi")
        return

    msg = "📋 Custom Commands:\n\n"
    for cmd, reply in CUSTOM_COMMANDS.items():
        msg += f"/{cmd} → {reply[:30]}...\n"
    await update.message.reply_text(msg)

# ← NAYA: LEARN COMMAND - Bot ko sikhane ke liye
async def learn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Bhai ye command sirf owner ke liye hai 😅")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Use: /learn question | answer\nexample: /learn tumhara naam | Mera naam RJ Bot hai 😎")
        return

    full_text = " ".join(context.args)
    if "|" not in full_text:
        await update.message.reply_text("❌ Format galat hai bhai\nUse: /learn question | answer")
        return

    question, answer = full_text.split("|", 1)
    question = question.strip().lower()
    answer = answer.strip()

    if question not in LEARNED_REPLIES:
        LEARNED_REPLIES[question] = []
    
    LEARNED_REPLIES[question].append(answer)
    save_learned_replies()
    await update.message.reply_text(f"✅ Seekh gaya bhai!\nQ: {question}\nA: {answer}")

# ← NAYA: UNLEARN COMMAND - Sikhaya hua bhulane ke liye
async def unlearn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Bhai ye command sirf owner ke liye hai 😅")
        return

    if not context.args:
        await update.message.reply_text("Use: /unlearn question")
        return

    question = " ".join(context.args).lower()
    if question in LEARNED_REPLIES:
        del LEARNED_REPLIES[question]
        save_learned_replies()
        await update.message.reply_text(f"✅ Bhool gaya: {question}")
    else:
        await update.message.reply_text(f"❌ Ye to maine seekha hi nahi tha: {question}")

async def set_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CONTACT_INFO
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Bhai ye command sirf owner ke liye hai 😅")
        return

    if not context.args:
        await update.message.reply_text(f"Current: {CONTACT_INFO}\nUse: /setcontact Naya contact info")
        return

    CONTACT_INFO = " ".join(context.args)
    await update.message.reply_text(f"✅ Contact update ho gaya:\n{CONTACT_INFO}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    total_users = len(USER_DATA)
    total_calls = sum(GEMINI_CALLS.values())
    msg = f"📊 Bot Stats:\n\n👥 Total Users: {total_users}\n🤖 Gemini Calls: {total_calls}\n🔑 Active Key: {current_key_index+1}\n💬 Custom Commands: {len(CUSTOM_COMMANDS)}\n🧠 Learned Replies: {len(LEARNED_REPLIES)}"
    await update.message.reply_text(msg)

# ===== 6. NORMAL HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"RJ Bot chalu hai bhai 😎 Kuch bhi pooch le\n\nContact: {CONTACT_INFO}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not check_cooldown(user_id):
        await update.message.reply_text(f"Bhai {update.effective_user.first_name} ruk ja 5 sec 😂 Spam mat kar")
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1)
    
    reply = await get_smart_reply(update.message.text, user_id, update.effective_user.first_name)
    await update.message.reply_text(reply)

# ===== 7. BOT START =====
if __name__ == "__main__":
    print("Bot starting...")
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN nahi mila")
        exit()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addcmd", add_cmd))
    app.add_handler(CommandHandler("delcmd", del_cmd))
    app.add_handler(CommandHandler("listcmd", list_cmd))
    app.add_handler(CommandHandler("setcontact", set_contact))
    app.add_handler(CommandHandler("stats", stats))
    # ← NAYE COMMANDS ADD KIYE
    app.add_handler(CommandHandler("learn", learn_cmd))
    app.add_handler(CommandHandler("unlearn", unlearn_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Application started")
    app.run_polling()
