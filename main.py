import os
import re
import random
import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OWNER_ID = int(os.getenv('OWNER_ID'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini Setup
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_available = True
else:
    gemini_available = False

# MEMORY SYSTEM - User ko yaad rakhega
USER_DATA = {} # {user_id: {"name": "RJ", "count": 5, "last_msg": "hi", "memory": []}}
MAX_MEMORY = 5

# SPAM PROTECTION - 5 sec cooldown
USER_COOLDOWN = {} # ← YE ADD KIYA

# QUOTA TRACKING - Kitne Gemini call bache
GEMINI_CALLS_TODAY = 0 # ← YE ADD KIYA
LAST_RESET_DATE = datetime.now().date() # ← YE ADD KIYA

# BRAIN - Yahan saara gyaan hai. Tu aur add kar sakta hai
KNOWLEDGE = {
    "greetings": {
        "patterns": ["hi", "hello", "hey", "namaste", "kya haal"],
        "replies": ["Haan {name} bhai 🔥", "Bol {name} kya haal", "Namaste {name} ji 😎"]
    },
    "how_are_you": {
        "patterns": ["kaise ho", "kya haal", "how are you", "kya chal raha"],
        "replies": ["Badhiya {name} tu suna", "Bindas bhai 😎 Tu bata", "Sab mast {name}"]
    },
    "name": {
        "patterns": ["naam kya", "who are you", "tu kaun", "tera naam"],
        "replies": ["Main {bot_name} hun, {name} ka assistant 🤖", "Mujhe {bot_name} bolte hain bhai"]
    },
    "time": {
        "patterns": ["time", "kitne baje", "samay", "waqt"],
        "replies": ["Abhi {time} baj rahe hain {name}", "{time} hua hai bhai"]
    },
    "jokes": {
        "patterns": ["joke", "hasao", "funny", "majak"],
        "replies": ["Teacher: Padhai kyu nahi ki?\nBaccha: Network issue tha 😂", "Aloo bola: Main mashoor hun\nTamatar bola: Main bhi laal hun 😂"]
    },
    "thanks": {
        "patterns": ["thanks", "thank you", "shukriya", "dhanyawad"],
        "replies": ["Koi na {name} bhai ❤️", "Welcome yaara 😎", "Are mention not"]
    },
    "bye": {
        "patterns": ["bye", "alvida", "ja raha", "goodbye", "milte"],
        "replies": ["Bye {name} bhai, milte hain 👋", "Chalta hun {name} 🔥", "Okay tata"]
    },
    "pw": {
        "patterns": ["pw", "physics wallah", "live class", "batch"],
        "replies": ["PW ka link bhej de {name}, main check kar lunga live hai ya nahi", "Batch ka naam bata bhai"]
    },
    "owner": {
        "patterns": ["owner", "malik", "kisne banaya", "creator"],
        "replies": ["Mere malik THE RJ hain 🔥", "RJ bhai ne banaya mujhe"]
    }
}

# DEFAULT REPLY - Jab kuch samajh na aaye
DEFAULT_REPLIES = [
    "Samjha nahi {name} bhai 😅 Thoda seedha bol",
    "Ye to high level ho gaya {name} 🤔 Easy wala pooch",
    "Mera CPU heat ho gaya {name} 🥵 Phir se bol",
    "Abhi training chal rahi hai {name} 😂 Baad me batana ye"
]

async def get_smart_reply(user_msg, user_id, user_name):
    global GEMINI_CALLS_TODAY, LAST_RESET_DATE # ← YE ADD KIYA
    
    # QUOTA RESET CHECK - Roz 12:30 PM IST pe reset
    if datetime.now().date() != LAST_RESET_DATE:
        GEMINI_CALLS_TODAY = 0
        LAST_RESET_DATE = datetime.now().date()
    
    user_msg_lower = user_msg.lower()
    
    # 1. MEMORY UPDATE
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"name": user_name, "count": 0, "last_msg": "", "memory": []}
    USER_DATA[user_id]["count"] += 1
    USER_DATA[user_id]["last_msg"] = user_msg
    
    # 2. SABSE PEHLE OFFLINE BRAIN CHECK KAR - Fast reply ke liye
    for category, data in KNOWLEDGE.items():
        for pattern in data["patterns"]:
            if re.search(r'\b' + pattern + r'\b', user_msg_lower):
                reply = random.choice(data["replies"])
                reply = reply.format(
                    name=user_name,
                    bot_name="RJ Bot",
                    time=datetime.now().strftime("%I:%M %p"),
                    count=USER_DATA[user_id]["count"]
                )
                # Memory me daal de
                USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
                if len(USER_DATA[user_id]["memory"]) > MAX_MEMORY:
                    USER_DATA[user_id]["memory"].pop(0)
                return reply
    
    # 3. SPECIAL CASES - Math solve kar de
    if re.search(r'\d+[\+\-\*\/]\d+', user_msg):
        try:
            result = eval(re.sub(r'[^0-9\+\-\*\/\(\)\.]', '', user_msg))
            reply = f"Hisab lagaya {user_name}: {result} 😎"
            USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
            return reply
        except:
            pass
    
    # 4. AGAR OFFLINE ME KUCH NAA MILE TO GEMINI KO POOCH
    if not gemini_available:
        reply = random.choice(DEFAULT_REPLIES).format(name=user_name)
        return reply
    
    # QUOTA CHECK - 1450 pe warning de dena, 1500 se pehle ruk ja
    if GEMINI_CALLS_TODAY >= 1490:
        reply = f"Yaar {user_name} quota khatam hone wala hai 🥵 Dopahar 12:30 baje reset hoga. Abhi offline reply dunga."
        return reply
        
    try:
        await asyncio.sleep(1) # Rate limit se bachne ke liye 1 sec ruk
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        pichli_baat = " | ".join(USER_DATA[user_id]["memory"][-3:])
        prompt = f"""
        Tu RJ ka dost hai. Hinglish me baat kar. 1-2 line reply de. 
        User: {user_name}
        Pichli baat: {pichli_baat}
        Abhi poocha: {user_msg}
        """
        
        response = await model.generate_content_async(prompt, request_options={"timeout": 15})
        GEMINI_CALLS_TODAY += 1 # ← QUOTA COUNT BADHAYA
        
        if response.text:
            reply = response.text
        else:
            raise Exception("Empty response")
            
    except Exception as e:
        # 5. GEMINI FAIL HO GAYA TO DEFAULT + OWNER KO ERROR
        logger.error(f"Gemini Failed: {e}")
        
        # Owner ko error bhej de
        try:
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🚨 GEMINI ERROR 🚨\nUser: {user_name}\nMsg: {user_msg}\nError: {str(e)[:500]}"
            )
        except:
            pass
            
        # User ko default reply
        reply = random.choice(DEFAULT_REPLIES).format(name=user_name)
    
    # 6. MEMORY UPDATE
    USER_DATA[user_id]["memory"].append(f"U: {user_msg} | B: {reply}")
    if len(USER_DATA[user_id]["memory"]) > MAX_MEMORY:
        USER_DATA[user_id]["memory"].pop(0)
    
    return reply

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    now = datetime.now().timestamp()
    
    # 5 SEC COOLDOWN - Spam rokne ke liye ← YE ADD KIYA
    if user.id in USER_COOLDOWN and now - USER_COOLDOWN[user.id] < 5:
        return # Reply mat kar, ignore kar
    
    USER_COOLDOWN[user.id] = now
    
    msg = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await get_smart_reply(msg, user.id, user.first_name)
    await update.message.reply_text(reply)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ram Ram {update.effective_user.first_name} 🔥\nMain hybrid bot hun. Offline + Gemini dono. Kuch bhi pooch le")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    total_users = len(USER_DATA)
    total_msgs = sum([u["count"] for u in USER_DATA.values()])
    await update.message.reply_text(f"Stats:\nUsers: {total_users}\nTotal Msgs: {total_msgs}")

# /QUOTA COMMAND - NAYA ADD KIYA ← YE PURA NAYA HAI
async def quota_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Bhai ye command sirf malik ke liye hai 🔒")
        return
    
    global GEMINI_CALLS_TODAY
    remaining = 1500 - GEMINI_CALLS_TODAY
    percent = (GEMINI_CALLS_TODAY / 1500) * 100
    
    if remaining <= 0:
        status = "❌ KHATAM HO GAYA"
        reset_time = "Dopahar 12:30 PM IST"
    elif remaining < 100:
        status = "⚠️ KHATAM HONE WALA HAI"
        reset_time = "Dopahar 12:30 PM IST"
    else:
        status = "✅ MAST CHAL RAHA"
        reset_time = "Dopahar 12:30 PM IST"
    
    await update.message.reply_text(
        f"📊 **GEMINI QUOTA**\n\n"
        f"Used: {GEMINI_CALLS_TODAY}/1500 ({percent:.1f}%)\n"
        f"Bache: {remaining}\n"
        f"Status: {status}\n"
        f"Reset: {reset_time}"
    )

def main():
    global app
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("quota", quota_cmd)) # ← YE LINE ADD KI
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
