import os, re, random, asyncio, logging, json, time
from groq import Groq
from duckduckgo_search import DDGS # Web search import
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== 1. SETUP =====
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
DATABASE_CHANNEL_ID = os.getenv("DATABASE_CHANNEL_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ===== 2. GLOBAL VARIABLES =====
USER_DATA = {}
USER_COOLDOWN = {}
COOLDOWN_TIME = 5
PENDING_VERIFICATION = {}
BOT_PERSONALITY = "savage"

# ===== 3. DATABASE FUNCTIONS =====
async def load_data_from_telegram(app):
    global USER_DATA
    USER_DATA = {} 
    print("✅ System Ready: Memory initialized to fresh. Startup stable.")

async def save_user_data(context):
    if not DATABASE_CHANNEL_ID: return
    try:
        data_string = json.dumps(USER_DATA, ensure_ascii=False)
        await context.bot.send_message(chat_id=DATABASE_CHANNEL_ID, text=f"☁️ CLOUD_SAVE:\n{data_string}")
    except Exception as e:
        print(f"❌ Save Error: {e}")

def is_owner(user_id):
    return user_id == OWNER_ID

# ===== 4. HANDLERS =====

# Start Command
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
    await update.message.reply_text(f"RJ Bot active hai bhai! 😎\nMode: {BOT_PERSONALITY.capitalize()}\nWeb Search: ON (/search)")

# Mood Command
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

# Web Search Command
async def web_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Bhai, kya search karna hai? Topic toh likho! \nUsage: `/search Delhi Weather`")
        return

    query = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        results = []
        with DDGS() as ddgs:
            # Top 3 results for speed
            for r in ddgs.text(query, max_results=3):
                results.append(f"🔹 **{r['title']}**\n🔗 {r['href']}")

        if results:
            response = f"🔍 **Search Results for '{query}':**\n\n" + "\n\n".join(results)
            await update.message.reply_text(response, disable_web_page_preview=True)
        else:
            await update.message.reply_text("Bhai, internet par kuch mila hi nahi is baare mein. 🤷‍♂️")

    except Exception as e:
        logging.error(f"Search Error: {e}")
        await update.message.reply_text("Bhai search engine atak gaya, thodi der mein try kar. ☕")

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
        except: 
            return

    # 2. Cooldown
    now = time.time()
    if user_id in USER_COOLDOWN and now - USER_COOLDOWN[user_id] < COOLDOWN_TIME:
        await update.message.reply_text("Ruk ja bhai! ☕")
        return
    USER_COOLDOWN[user_id] = now

    # 3. Groq AI Logic
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    system_prompt = "Tu RJ ka dost hai, dilli ka savage chhora. Use Hinglish mixed with Delhi slang." if BOT_PERSONALITY == "savage" else "Tu ek professional consultant hai."

    try:
        if not GROQ_API_KEY:
            await update.message.reply_text("Bhai Groq API key gayab hai variables se!")
            return

        client = Groq(api_key=GROQ_API_KEY)
        
        chat_completion = await asyncio.to_thread(
            client.chat.completions.create,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            model="llama-3.1-8b-instant", 
        )
        
        response_text = chat_completion.choices[0].message.content

        if str(user_id) in USER_DATA:
            USER_DATA[str(user_id)]["count"] += 1
            if USER_DATA[str(user_id)]["count"] % 10 == 0:
                await save_user_data(context)
                
        await update.message.reply_text(response_text)
    except Exception as e:
        logging.error(f"Groq Error: {e}")
        await update.message.reply_text("Bhai technical error hai, thodi der mein try kar. ☕")

# ===== 6. RUN BOT =====
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_data_from_telegram(app))

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mood", set_mood))
    app.add_handler(CommandHandler("search", web_search)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("RJ BOT PRO Upgraded with Groq & Web Search LIVE! 🚀")
    app.run_polling()
