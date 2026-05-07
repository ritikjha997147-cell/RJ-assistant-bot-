import os
import re
import random
import asyncio
import logging
import json
import time
import google.generativeai as genai
from datetime import datetime, timedelta
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote_plus
import aiohttp
from io import BytesIO
import PyPDF2

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
LEARNED_REPLIES_FILE = "learned_replies.json"
REMINDERS_FILE = "reminders.json" # ← NAYA: Reminders ke liye
CONTACT_INFO = "Owner: @YourUsername"
USER_COOLDOWN = {}
COOLDOWN_TIME = 5
LINK_PATTERN = re.compile(r'http[s]?://|t\.me/|www\.') # ← NAYA: Link detect

try:
    with open(CUSTOM_COMMANDS_FILE, 'r') as f:
        CUSTOM_COMMANDS = json.load(f)
except:
    CUSTOM_COMMANDS = {}

try:
    with open(LEARNED_REPLIES_FILE, 'r') as f:
        LEARNED_REPLIES = json.load(f)
except:
    LEARNED_REPLIES = {}

# ← NAYA: Reminders load karo
try:
    with open(REMINDERS_FILE, 'r') as f:
        REMINDERS = json.load(f)
except:
    REMINDERS = {}

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

def save_learned_replies():
    with open(LEARNED_REPLIES_FILE, 'w') as f:
        json.dump(LEARNED_REPLIES, f, indent=2)

# ← NAYA: Reminders save
def save_reminders():
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(REMINDERS, f, indent=2)

def is_owner(user_id):
    return user_id == OWNER_ID

def check_cooldown(user_id):
    current_time = time.time()
    if user_id in USER_COOLDOWN:
        if current_time - USER_COOLDOWN[user_id] < COOLDOWN_TIME:
            return False
    USER_COOLDOWN[user_id] = current_time
    return True

# ← NAYA: DuckDuckGo Search Function
async def search_google(query):
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                if data.get('AbstractText'):
                    return data['AbstractText'][:500]
                elif data.get('RelatedTopics'):
                    topics = [t['Text'] for t in data['RelatedTopics'][:2] if 'Text' in t]
                    return " | ".join(topics)[:500] if topics else None
    except:
        return None

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

    if user_msg_lower in CUSTOM_COMMANDS:
        return CUSTOM_COMMANDS[user_msg_lower].format(name=user_name)

    if user_msg_lower in LEARNED_REPLIES:
        reply = random.choice(LEARNED_REPLIES[user_msg_lower]).format(name=user_name)
        return reply

    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"name": user_name, "count": 0, "last_msg": "", "memory": []}
    USER_DATA[user_id]["count"] += 1
    USER_DATA[user_id]["last_msg"] = user_msg

    for category, data in KNOWLEDGE.items():
        for pattern in data["patterns"]:
            if re.search(r'\b' + pattern + r'\b', user_msg_lower):
                reply = random.choice(data["replies"])
                reply = reply.format(name=user_name, bot_name="RJ Bot", time=datetime.now().strftime("%I:%M %p"), count=USER_DATA[user_id]["count"])
                USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
                if len(USER_DATA[user_id]["memory"]) > MAX_MEMORY:
                    USER_DATA[user_id]["memory"].pop(0)
                return reply

    if re.search(r'\d+[\+\-\*\/]\d+', user_msg):
        try:
            result = eval(re.sub(r'[^0-9\+\-\*\/\(\)\.]', '', user_msg))
            reply = f"Hisab lagaya {user_name}: {result} 😎"
            USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
            return reply
        except:
            pass

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

async def get_image_reply(image_bytes, user_prompt, user_name):
    global GEMINI_CALLS, current_key_index, gemini_available

    if not gemini_available:
        return f"Bhai {user_name} abhi photo nahi dekh pa raha, keys khatam 😅"

    prompt = f"""
    Tu RJ ka dost hai - dilli ka chhora. User: {user_name}
    Ye photo dekh aur bata isme kya hai.
    User ne pucha: {user_prompt if user_prompt else 'Photo me kya hai?'}

    RULE: Hinglish me 2-3 line me dosti wale style me reply de. Emoji use kar.
    Agar meme hai to hasa ke roast kar. Agar padhai ka hai to samjha de.
    """

    for key_attempt in range(len(API_KEYS)):
        current_key = API_KEYS[current_key_index]
        genai.configure(api_key=current_key)

        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            image_part = {"mime_type": "image/jpeg", "data": image_bytes}
            response = await asyncio.to_thread(model.generate_content, [prompt, image_part])

            if response.text:
                GEMINI_CALLS[current_key_index] += 1
                return response.text
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str:
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                continue
            else:
                logger.error(f"Vision Error: {e}")
                break

    return f"Bhai {user_name} photo samjh nahi aayi 😅 Dubara bhej clear wali"

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

# ← NAYA: GOOGLE SEARCH COMMAND
async def google_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /google python kya hai")
        return

    query = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    result = await search_google(query)
    if result:
        await update.message.reply_text(f"🔍 Google Search: {query}\n\n{result}")
    else:
        await update.message.reply_text(f"Bhai {update.effective_user.first_name} search nahi mila 😅 Gemini se puch le")

# ← NAYA: REMINDER COMMAND
async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /remind 2h Call karna hai\nYa: /remind 30m Paani peena")
        return

    time_str = context.args[0].lower()
    msg = " ".join(context.args[1:])
    user_id = str(update.effective_user.id)

    # Parse time: 2h, 30m, 1d
    try:
        if 'h' in time_str:
            hours = int(time_str.replace('h', ''))
            delta = timedelta(hours=hours)
        elif 'm' in time_str:
            mins = int(time_str.replace('m', ''))
            delta = timedelta(minutes=mins)
        elif 'd' in time_str:
            days = int(time_str.replace('d', ''))
            delta = timedelta(days=days)
        else:
            await update.message.reply_text("❌ Time format: 2h ya 30m ya 1d")
            return

        remind_time = datetime.now() + delta
        if user_id not in REMINDERS:
            REMINDERS[user_id] = []

        REMINDERS[user_id].append({
            "time": remind_time.isoformat(),
            "msg": msg,
            "chat_id": update.effective_chat.id
        })
        save_reminders()

        await update.message.reply_text(f"✅ Done bhai! {time_str} baad yaad dila dunga:\n{msg}")
    except:
        await update.message.reply_text("❌ Galat format. Use: /remind 2h message")

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
    msg = f"📊 Bot Stats:\n\n👥 Total Users: {total_users}\n🤖 Gemini Calls: {total_calls}\n🔑 Active Key: {current_key_index+1}\n💬 Custom Commands: {len(CUSTOM_COMMANDS)}\n🧠 Learned Replies: {len(LEARNED_REPLIES)}\n⏰ Active Reminders: {sum(len(v) for v in REMINDERS.values())}"
    await update.message.reply_text(msg)

# ===== 6. NORMAL HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"RJ Bot chalu hai bhai 😎\n\n📸 Photo bhejo → Bataunga kya hai\n📄 PDF bhejo → Summary dunga\n🔍 /google → Search karunga\n⏰ /remind 2h → Yaad dilaunga\n\nContact: {CONTACT_INFO}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ← NAYA: Anti-Link for Groups
    if update.effective_chat.type in ['group', 'supergroup']:
        if LINK_PATTERN.search(update.message.text):
            try:
                await update.message.delete()
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"@{update.effective_user.username or update.effective_user.first_name} bhai link allowed nahi hai 🚫"
                )
                return
            except:
                pass

    if not check_cooldown(user_id):
        await update.message.reply_text(f"Bhai {update.effective_user.first_name} ruk ja 5 sec 😂 Spam mat kar")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1)

    user_text = update.message.text or update.message.caption or ""

    reply = await get_smart_reply(user_text, user_id, update.effective_user.first_name)
    await update.message.reply_text(reply)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if not check_cooldown(user_id):
        await update.message.reply_text(f"Bhai {user_name} ruk ja 5 sec 😂")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    user_prompt = update.message.caption or ""

    reply = await get_image_reply(photo_bytes, user_prompt, user_name)
    await update.message.reply_text(reply)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not check_cooldown(user_id):
        await update.message.reply_text(f"Bhai {update.effective_user.first_name} ruk ja 5 sec 😂")
        return

    await update.message.reply_text("🎤 Voice sun raha hu bhai... Par abhi text me hi reply dunga 😅\n\nTu likh ke bhej de na")

# ← NAYA: PDF READER FUNCTION
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if not check_cooldown(user_id):
        return

    file_name = update.message.document.file_name

    # PDF hai to padho
    if file_name.lower().endswith('.pdf'):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await update.message.reply_text("📄 PDF padh raha hu bhai... Ruk ja 5 sec")

        try:
            pdf_file = await update.message.document.get_file()
            pdf_bytes = await pdf_file.download_as_bytearray()
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))

            text = ""
            for page in pdf_reader.pages[:3]: # Pehle 3 page
                text += page.extract_text()

            if text:
                # Gemini se summary
                summary_prompt = f"Is PDF ka summary 3 line me bata Hinglish me:\n\n{text[:3000]}"
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                response = await asyncio.to_thread(model.generate_content, summary_prompt)

                if response.text:
                    await update.message.reply_text(f"📄 PDF Summary:\n\n{response.text}")
                else:
                    await update.message.reply_text("Bhai PDF khali lag rahi hai 😅")
            else:
                await update.message.reply_text("❌ PDF se text nahi nikal paya. Shayad scanned hai")
        except Exception as e:
            await update.message.reply_text(f"❌ PDF error: {str(e)[:100]}")
    else:
        await update.message.reply_text(f"📄 File mil gayi: {file_name}\n\nAbhi sirf PDF padh sakta hu bhai 😅")

        try:
            await context.bot.forward_message(chat_id=OWNER_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass

# ← NAYA: WELCOME NEW MEMBER
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text("😎 RJ Bot aa gaya hai! /start dabao")
        else:
            await update.message.reply_text(
                f"Welcome {member.first_name} bhai! 🎉\n\n"
                f"Rules: 1) Gaali nahi 2) Link nahi 3) Bot se dosti kar 😎\n"
                f"Kuch bhi puchna ho /start dabao"
            )

# ← NAYA: REMINDER CHECKER BACKGROUND TASK
async def check_reminders(app):
    while True:
        await asyncio.sleep(60) # Har minute check
        now = datetime.now()
        to_remove = []

        for user_id, user_reminders in REMINDERS.items():
            for reminder in user_reminders[:]:
                remind_time = datetime.fromisoformat(reminder['time'])
                if now >= remind_time:
                    try:
                        await app.bot.send_message(
                            chat_id=reminder['chat_id'],
                            text=f"⏰ Reminder bhai!\n\n{reminder['msg']}"
                        )
                        user_reminders.remove(reminder)
                    except:
                        pass

            if not user_reminders:
                to_remove.append(user_id)

        for user_id in to_remove:
            del REMINDERS[user_id]

        if to_remove:
            save_reminders()

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
    app.add_handler(CommandHandler("learn", learn_cmd))
    app.add_handler(CommandHandler("unlearn", unlearn_cmd))
    app.add_handler(CommandHandler("google", google_cmd)) # ← NAYA
    app.add_handler(CommandHandler("remind", remind_cmd)) # ← NAYA

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document)) # ← PDF READER
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member)) # ← WELCOME

    # Background task for reminders
    app.job_queue.run_once(lambda ctx: asyncio.create_task(check_reminders(app)), 1)

    print("Application started")
    app.run_polling()
