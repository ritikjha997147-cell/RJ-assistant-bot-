import os, re, random, asyncio, logging, json, time
import google.generativeai as genai
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== 1. SETUP =====
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
DATABASE_CHANNEL_ID = os.getenv("DATABASE_CHANNEL_ID") 
API_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 5) if os.getenv(f"GEMINI_API_KEY_{i}")]

# ===== 2. GLOBAL VARIABLES =====
USER_DATA = {}
USER_COOLDOWN = {}
COOLDOWN_TIME = 5
PENDING_VERIFICATION = {} 
BOT_PERSONALITY = "savage"

# ===== 3. DATABASE FUNCTIONS (CLEANED) =====
async def load_data_from_telegram(app):
    """
    Startup par memory initialize karta hai. 
    Note: 'get_chat_history' bots support nahi karte, isliye 
    hum memory ko fresh start kar rahe hain conflict se bachne ke liye.
    """
    global USER_DATA
    USER_DATA = {} 
    print("✅ System Ready: Memory initialized to fresh. Startup stable.")

async def save_user_data(context):
    """Database channel mein JSON save karta hai."""
    if not DATABASE_CHANNEL_ID: return
    try:
        data_string = json.dumps(USER_DATA, ensure_ascii=False)
        await context.bot.send_message(chat_id=DATABASE_CHANNEL_ID, text=f"☁️ CLOUD_SAVE:\n{data_string}")
    except Exception as e:
        print(f"❌ Save Error: {e}")

def is_owner(user_id):
    return user_id == OWNER_ID

# ===== 4. HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if str(user_id) not in USER_DATA:
        num1, num2 = random.randint(1, 10), random.randint(1, 10)
        answer = num1 + num2
        PENDING_VERIFICATION[user_id] = answer
        await update.message.reply_text(
            f"Oye {user_name}! Bot use karne se pehle ye bata: **{num1} + {num2} = ?**"
        )
        return

    await update.message.reply_text(f"RJ Bot active hai bhai! 😎\nMode: {BOT_PERSONALITY.capitalize()}")

async def set_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_PERSONALITY
    if not is_owner(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Mood chuno: `/mood savage` ya `/mood formal`")
        return
    mood = context.args[0].lower()
    if mood in ["savage", "formal"]:
        BOT_PERSONALITY = mood
        await update.message.reply_text(f"✅ Mood set to {mood}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not context.args: return
    msg = " ".join(context.args)
    count = 0
    for uid in list(USER_DATA.keys()):
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"📢 **BROADCAST:**\n\n{msg}")
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(f"✅ Sent to {count} users.")

# ===== 5. MAIN MESSAGE HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = update.message.text

    # 1. Anti-Bot Logic
    if user_id in PENDING_VERIFICATION:
        try:
            if int(text) == PENDING_VERIFICATION[user_id]:
                del PENDING_VERIFICATION[user_id]
                USER_DATA[str(user_id)] = {"name": user_name, "count": 0}
                await save_user_data(context)
                await update.message.reply_text("✅ Pass ho gaya bhai! Ab bol kya scene hai?")
            else:
                await update.message.reply_text("❌ Galat! Phir se try kar.")
            return
        except: return

    # 2. Cooldown
    now = time.time()
    if user_id in USER_COOLDOWN and now - USER_COOLDOWN[user_id] < COOLDOWN_TIME:
        await update.message.reply_text("Ruk ja bhai! ☕")
        return
    USER_COOLDOWN[user_id] = now

    # 3. Gemini Logic
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    system_prompt = "Tu RJ ka dost hai, dilli ka savage chhora. Use Hinglish mixed with Delhi slang." if BOT_PERSONALITY == "savage" else "Tu ek professional consultant hai."

    try:
        active_keys = [k for k in API_KEYS if k]
        if not active_keys:
            await update.message.reply_text("Bhai API keys gayab hain!")
            return

        genai.configure(api_key=random.choice(active_keys))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Async call
        response = await asyncio.to_thread(model.generate_content, f"{system_prompt}\nUser {user_name}: {text}")
        
        if str(user_id) in USER_DATA:
            USER_DATA[str(user_id)]["count"] += 1
            # Har 10th message par auto-save
            if USER_DATA[str(user_id)]["count"] % 10 == 0:
                await save_user_data(context)
                
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        await update.message.reply_text("Bhai technical error hai, thodi der mein try kar. ☕")

# ===== 6. RUN BOT =====
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Startup memory init
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_data_from_telegram(app))

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("mood", set_mood))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("RJ BOT PRO Upgraded & LIVE! 🚀")
    app.run_polling()
