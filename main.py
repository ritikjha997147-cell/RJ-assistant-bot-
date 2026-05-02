import os
import json
import logging
import random
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

genai.configure(api_key=GEMINI_API_KEY)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_brain():
    try:
        if os.path.exists("brain.json"):
            with open("brain.json", 'r', encoding='utf-8') as f: return json.load(f)
    except: pass
    return {"notes": [], "learned": {}}

def save_brain(brain):
    try:
        with open("brain.json", 'w', encoding='utf-8') as f: json.dump(brain, f, ensure_ascii=False, indent=2)
    except Exception as e: logging.error(f"Save error: {e}")

async def get_ai_reply(user_msg, user_name):
    try:
        brain = load_brain()
        if user_msg.lower() in brain["learned"]: return brain["learned"][user_msg.lower()]
        
        # Model name badla hai - ye wala sabke liye chalta hai
        model = genai.GenerativeModel("gemini-flash-latest")  
        response = model.generate_content(f"Tu RJ ka dost hai. User {user_name} se Hinglish me 1-2 line me dosti bhare andaaz me baat kar. Emojis use kar. Sawal: {user_msg}")
        
        if response.text:
            return response.text
        else:
            return f"Haan {user_name} bhai, kya haal 😅"
            
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        # Backup reply - agar AI fail ho jaye
        backup = [
            f"Bhai {user_name} net slow hai, seedha bol 😎",
            "Kya scene hai bhai 🔥",
            f"Sunn raha hu {user_name} bhai, bol",
            "Phone hang ho gaya tha, ab bol 😂"
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
        
        if user.id != OWNER_ID:
            chat_type = "DM" if chat.type == "private" else f"Group: {chat.title}"
            log_msg = f"📩 New Msg\nFrom: {user.first_name} (@{user.username})\nID: {user.id}\nChat: {chat_type}\nMessage: {msg}"
            try:
                await context.bot.send_message(chat_id=OWNER_ID, text=log_msg)
            except Exception as e:
                logging.error(f"Forward failed: {e}")
        
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        reply = await get_ai_reply(msg, user.first_name)
        await update.message.reply_text(reply)
        
    except Exception as e:
        logging.error(f"Handle Error: {e}")
        await update.message.reply_text("Kuch gadbad ho gayi bhai 😅")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("learn", learn))
    application.add_handler(CommandHandler("note", add_note))
    application.add_handler(CommandHandler("notes", show_notes))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot chalu ho gaya...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
