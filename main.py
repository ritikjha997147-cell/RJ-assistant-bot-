import os
import json
import logging
import random
import asyncio
import time
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

genai.configure(api_key=GEMINI_API_KEY)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FIX 1: Brain load safe ho gaya - corrupt hua to bhi chalega
def load_brain():
    try:
        if os.path.exists("brain.json"):
            with open("brain.json", 'r', encoding='utf-8') as f: 
                return json.load(f)
    except Exception as e:
        logger.error(f"Brain load error: {e}. Naya bana raha hu")
    return {"notes": [], "learned": {}}

def save_brain(brain):
    try:
        # Temp file me likh ke rename - crash hua to file corrupt nahi hogi
        with open("brain_temp.json", 'w', encoding='utf-8') as f: 
            json.dump(brain, f, ensure_ascii=False, indent=2)
        os.replace("brain_temp.json", "brain.json")
    except Exception as e: 
        logger.error(f"Save error: {e}")

# FIX 2: Gemini ab 5 baar try karega + timeout 30s
async def get_ai_reply(user_msg, user_name):
    brain = load_brain()
    if user_msg.lower() in brain["learned"]: 
        return brain["learned"][user_msg.lower()]
    
    for attempt in range(5):
        try:
            model = genai.GenerativeModel("gemini-flash-latest")  
            response = await model.generate_content_async(
                f"Tu RJ ka dost hai. User {user_name} se Hinglish me 1-2 line me dosti bhare andaaz me baat kar. Emojis use kar. Sawal: {user_msg}",
                request_options={"timeout": 30}
            )
            if response.text:
                return response.text
            else:
                return f"Haan {user_name} bhai, kya haal 😅"
                
        except ResourceExhausted:
            logger.warning("Quota khatam")
            return f"Bhai {user_name} abhi thoda rush hai 😅 1 min baad try karna"
        
        except (ServiceUnavailable, DeadlineExceeded):
            if attempt < 4:
                wait = 2 ** attempt  # 2,4,8,16 sec wait
                logger.warning(f"Gemini down. {wait}s baad retry {attempt+1}/5")
                await asyncio.sleep(wait)
                continue
            return f"Google ka server so gaya {user_name} 😴 30 sec baad poochna"
            
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            break
    
    # FIX 3: Backup reply - AI fail ho bhi jaye to bot zinda rahega
    backup = [
        f"Bhai {user_name} thoda traffic hai, seedha bol 😎",
        f"Kya scene hai {user_name} bhai 🔥",
        f"Sunn raha hu {user_name}, bol kya baat hai",
        "Dimag restart kar raha hun 😂 Tu bol kya kaam hai"
    ]
    return random.choice(backup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("RJ ka bot on hai bhai 😎\nBol kya kaam hai? /help likh")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands:\n/learn hello ka reply namaste\n/note doodh lana hai\n/notes")

async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: 
        await update.message.reply_text("Sirf boss sikha sakta hai 😎"); return
    try:
        text = ' '.join(context.args)
        trigger, response = text.split(' ka reply ', 1)
        brain = load_brain(); brain["learned"][trigger.lower()] = response; save_brain(brain)
        await update.message.reply_text(f"Seekh gaya ✅")
    except: await update.message.reply_text("Aise: /learn hi ka reply hello")

async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = ' '.join(context.args)
    if not note: return
    brain = load_brain(); brain["notes"].append(note); save_brain(brain)
    await update.message.reply_text(f"Note kar liya ✅: {note}")

async def show_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    brain = load_brain()
    if not brain["notes"]: await update.message.reply_text("Koi note nahi"); return
    notes_text = "\n".join([f"{i+1}. {note}" for i, note in enumerate(brain["notes"])])
    await update.message.reply_text(f"Tere Notes:\n{notes_text}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat
        msg = update.message.text
        
        # Owner ko forward - isme error aaye to bhi bot chalta rahe
        if user.id != OWNER_ID:
            try:
                chat_type = "DM" if chat.type == "private" else f"Group: {chat.title}"
                log_msg = f"📩 New Msg\nFrom: {user.first_name} (@{user.username})\nID: {user.id}\nChat: {chat_type}\nMessage: {msg}"
                await context.bot.send_message(chat_id=OWNER_ID, text=log_msg)
            except Exception as e:
                logger.error(f"Forward failed: {e}")
        
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        reply = await get_ai_reply(msg, user.first_name)
        await update.message.reply_text(reply)
        
    except Exception as e:
        logger.error(f"Handle Error: {e}")
        await update.message.reply_text("Chhota sa jhatka laga tha 😂 Ab theek hu. Phir se bol")

# FIX 4: Global Error Handler - Kuch bhi ho jaye bot crash nahi hoga
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling update: {context.error}")
    if update and hasattr(update, 'effective_message') and update.effective_message:
        await update.effective_message.reply_text("Arey bhai technical dikkat 😅 Ab theek hu")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_error_handler(error_handler)  # Ye line add kari hai
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("learn", learn))
    application.add_handler(CommandHandler("note", add_note))
    application.add_handler(CommandHandler("notes", show_notes))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot chalu ho gaya... Amarr wala version 💪")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
