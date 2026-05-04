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
genai.configure(api_key=GEMINI_API_KEY)

# MEMORY SYSTEM - User ko yaad rakhega
USER_DATA = {} # {user_id: {"name": "RJ", "count": 5, "last_msg": "hi", "memory": []}}
MAX_MEMORY = 5

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
    try:
        await asyncio.sleep(1) # Rate limit se bachne ke liye 1 sec ruk
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        pichli_baat = " | ".join(USER_DATA[user_id]["memory"][-3:])
        prompt = f"""
        Tu RJ ka dost hai. Hinglish me baat kar. 1-2 line reply de. 
        User: {user_name}
        Pichli baat: {pichli_baat}
        Abhi poocha: {user_msg}
        """
        
        response = await model.generate_content_async(prompt, request_options={"timeout": 15})
        
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

def main():
    global app
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
