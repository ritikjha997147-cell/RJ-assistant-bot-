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

# ===== 1. SETUP (Wahi Purana) =====
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
API_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 5) if os.getenv(f"GEMINI_API_KEY_{i}")]

# ===== 2. GLOBAL VARIABLES (Naye Features Ke Liye) =====
USER_DATA = {}
USER_COOLDOWN = {}
COOLDOWN_TIME = 5
USER_DATA_FILE = "user_data.json"
# NAYA: Anti-Bot aur Personality ke liye
PENDING_VERIFICATION = {} 
BOT_PERSONALITY = "savage" # Default: Savage

# Data Load Karne Ka Logic
try:
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            USER_DATA = json.load(f)
except:
    USER_DATA = {}

def save_user_data():
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(USER_DATA, f, indent=2)

def is_owner(user_id):
    return user_id == OWNER_ID

# ===== 3. FEATURE 1: ANTI-BOT (Verification) =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Check if user already exists
    if str(user_id) not in USER_DATA:
        # Generate random math question
        num1, num2 = random.randint(1, 10), random.randint(1, 10)
        answer = num1 + num2
        PENDING_VERIFICATION[user_id] = answer
        
        await update.message.reply_text(
            f"Oye {user_name}! Bot use karne se pehle ye bata ki tu robot to nahi hai? 😂\n\n"
            f"Bata: **{num1} + {num2} = ?**"
        )
        return

    await update.message.reply_text(f"RJ Bot active hai bhai! 😎\nPersonality: {BOT_PERSONALITY.capitalize()}\nBol kya scene hai?")

# ===== 4. FEATURE 2: PERSONALITY SWITCH =====
async def set_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_PERSONALITY
    if not is_owner(update.effective_user.id): return

    if not context.args:
        await update.message.reply_text("Mood chuno: `/mood savage` ya `/mood formal`")
        return

    mood = context.args[0].lower()
    if mood in ["savage", "formal"]:
        BOT_PERSONALITY = mood
        await update.message.reply_text(f"✅ Done! Bot ab **{mood}** mode mein baat karega.")
    else:
        await update.message.reply_text("❌ Galat mood! Sirf 'savage' ya 'formal' allowed hai.")

# ===== 5. FEATURE 3: BROADCAST (Marketing) =====
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return

    if not context.args:
        await update.message.reply_text("Message to likho! Example: `/broadcast Aaj naya video aane wala hai!`")
        return

    msg = " ".join(context.args)
    count = 0
    await update.message.reply_text(f"🚀 {len(USER_DATA)} users ko message bhej raha hoon...")

    for uid in list(USER_DATA.keys()):
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"📢 **BROADCAST FROM OWNER:**\n\n{msg}")
            count += 1
            await asyncio.sleep(0.1) # Flood se bachne ke liye
        except:
            pass
    
    await update.message.reply_text(f"✅ Done! {count} users ko message pahuch gaya.")

# ===== 6. MAIN MESSAGE HANDLER (Logic Integrated) =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = update.message.text

    # 1. Anti-Bot Verification Logic
    if user_id in PENDING_VERIFICATION:
        try:
            user_answer = int(text)
            if user_answer == PENDING_VERIFICATION[user_id]:
                del PENDING_VERIFICATION[user_id]
                USER_DATA[str(user_id)] = {"name": user_name, "count": 0, "memory": []}
                save_user_data()
                await update.message.reply_text("✅ Pass ho gaya bhai! Ab bol kya help chahiye? 😎")
            else:
                await update.message.reply_text("❌ Galat jawaab! Phir se try kar robot kahin ke. 😂")
            return
        except ValueError:
            await update.message.reply_text("Bhai number mein jawaab de! 1 + 1 kitna hota hai?")
            return

    # 2. Cooldown Logic
    now = time.time()
    if user_id in USER_COOLDOWN and now - USER_COOLDOWN[user_id] < COOLDOWN_TIME:
        await update.message.reply_text(f"Ruk ja {user_name}! Itni jaldi kya hai? ☕")
        return
    USER_COOLDOWN[user_id] = now

    # 3. Gemini Reply with Personality
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Prompt based on personality
    if BOT_PERSONALITY == "savage":
        system_prompt = "Tu RJ ka dost hai, dilli ka savage chhora. Ekdum bindass Hinglish bol."
    else:
        system_prompt = "Tu ek professional admission consultant hai. Tahzeeb se Hinglish mein help kar."

    # Gemini Call Logic (Wahi purana rotation wala)
    try:
        genai.configure(api_key=random.choice(API_KEYS))
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        full_prompt = f"{system_prompt}\nUser {user_name}: {text}"
        response = await asyncio.to_thread(model.generate_content, full_prompt)
        
        # Stats Update
        if str(user_id) in USER_DATA:
            USER_DATA[str(user_id)]["count"] += 1
            save_user_data()
            
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("Bhai thoda technical error hai, 2 min mein try kar ☕")

# ===== 7. RUN BOT =====
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("mood", set_mood))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("RJ BOT PRO Upgraded & LIVE! 🚀")
    app.run_polling()
