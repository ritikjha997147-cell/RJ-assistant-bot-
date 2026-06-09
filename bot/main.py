import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())
import logging
from keep_alive import keep_alive
from bot.reminders.scheduler import start_scheduler, restore_reminders
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from bot.config import BOT_TOKEN
from bot.handlers.start import start
from bot.handlers.mood import set_mood
from bot.handlers.message import handle_message
from bot.handlers.image import handle_image
from bot.handlers.showlast import show_last_image
from bot.handlers.reminder import remind, list_reminders, cancel_reminder
from bot.handlers.busy import set_busy
from bot.handlers.status import set_status
from bot.handlers.connect import connect
from bot.handlers.sendlater import sendlater
from bot.handlers.userinfo import userinfo
from bot.handlers.today import today
from bot.handlers.natural_scheduler import natural_scheduler
from bot.handlers.admin_ai import admin_ai_control
from bot.handlers.contact_ai import contact_ai
from bot.reminders.checker import reminder_checker
from bot.reminders.message_scheduler import message_scheduler
from bot.search.ddgs_engine import search_web
from bot.utils.fallback import fallback_reply
from bot.ai.human_neuron import train_brain
logging.basicConfig(level=logging.INFO)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"[GLOBAL ERROR]: {context.error}")

async def brain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(train_brain())

async def safe_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await handle_message(update, context)
    except Exception as e:
        print(f"[MESSAGE ERROR]: {e}")
        await fallback_reply(update)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Bhai kya search karna hai?")
        return
    results = search_web(" ".join(context.args))
    if not results:
        await update.message.reply_text("Kuch nahi mila.")
        return
    await update.message.reply_text("\n\n".join(f"🔹 {r['title']}\n{r['url']}" for r in results))

async def post_init(app):
    asyncio.create_task(reminder_checker(app))
    asyncio.create_task(message_scheduler(app))

def main():
    keep_alive()
    start_scheduler()
    app = (Application.builder().token(BOT_TOKEN).post_init(post_init).job_queue(None).build())
    app.add_error_handler(error_handler)
    restore_reminders(app.bot)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mood", set_mood))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("showlast", show_last_image))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("brain", brain))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("sendlater", sendlater))
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler("busy", set_busy))
    app.add_handler(CommandHandler("status", set_status))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("reminders", list_reminders))
    app.add_handler(CommandHandler("cancelreminder", cancel_reminder))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_scheduler), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, contact_ai), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ai_control), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, safe_handle_message), group=2)
    print("✅ RJ BOT PRO RUNNING")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()