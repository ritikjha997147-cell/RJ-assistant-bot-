import logging
import asyncio

from flask import app  # पुराने कोड का फ्लास्क इम्पोर्ट सुरक्षित है
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from bot.config import BOT_TOKEN

from bot.handlers.start import start, help_command
from bot.handlers.mood import set_mood
from bot.handlers.message import handle_message
from bot.handlers.image import handle_image
from bot.handlers.showlast import show_last_image
from bot.handlers.reminder import remind
from bot.handlers.connect import connect
from bot.handlers.sendlater import sendlater
from bot.handlers.userinfo import userinfo
from bot.handlers.today import today

# नए और मर्ज किए गए दोनों फंक्शंस को एक साथ इम्पोर्ट कर लिया
from bot.handlers.send import send_command, handle_owner_confirmation

from bot.handlers.hello import hello_command
from bot.handlers.natural_scheduler import natural_scheduler
from bot.handlers.admin_ai import admin_ai_control
from bot.handlers.contact_ai import contact_ai

from bot.reminders.checker import reminder_checker
from bot.reminders.message_scheduler import message_scheduler

from bot.search.ddgs_engine import search_web
from bot.utils.fallback import fallback_reply

logging.basicConfig(level=logging.INFO)

# =========================
# ERROR HANDLER
# =========================
async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    print(f"[GLOBAL ERROR]: {context.error}")

# =========================
# SAFE MESSAGE HANDLER
# =========================
async def safe_handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if context.user_data.get("handled"):
        context.user_data["handled"] = False
        return

    try:
        await handle_message(
            update,
            context
        )
    except Exception as e:
        print(f"[MESSAGE ERROR]: {e}")
        await fallback_reply(update)

# =========================
# SEARCH COMMAND
# =========================
async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "Bhai kya search karna hai?"
        )
        return

    query = " ".join(context.args)
    results = search_web(query)

    if not results:
        await update.message.reply_text(
            "ye kya bak rhe ho muje kuch nhi mila web pe."
        )
        return

    formatted = []
    for r in results:
        formatted.append(
            f"🔹 {r['title']}\n{r['url']}"
        )

    response = "\n\n".join(formatted)
    await update.message.reply_text(
        response
    )

# =========================
# BACKGROUND TASKS
# =========================
async def post_init(app):
    asyncio.create_task(
        reminder_checker(app)
    )
    asyncio.create_task(
        message_scheduler(app)
    )

# =========================
# MAIN BOT
# =========================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ERROR HANDLER
    app.add_error_handler(
        error_handler
    )

    # ---------------------------------------------------------
    # 1. ALL COMMAND HANDLERS REGISTERED FIRST (No Group - Default Group 0)
    # ---------------------------------------------------------
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("mood", set_mood))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("showlast", show_last_image))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("sendlater", sendlater))
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler(["send", "msg"], send_command))

    # ---------------------------------------------------------
    # 2. IMAGE HANDLER (Default Group 0)
    # ---------------------------------------------------------
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_image
        )
    )

    # ---------------------------------------------------------
    # 3. MESSAGE HANDLERS (Sequential Group Allocation)
    # ---------------------------------------------------------
    
    # OWNER CONFIRMATION: सबसे पहले ओनर का 'haa change kar naam' रिपॉन्स कैप्चर होगा (Top Priority)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_owner_confirmation
        ),
        group=1
    )

    # बाकी सारे पुराने एआई हैंडलर्स बिना लॉजिक बदले एक-एक ग्रुप नीचे शिफ्ट कर दिए गए हैं
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            natural_scheduler
        ),
        group=2
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            contact_ai
        ),
        group=3
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_ai_control
        ),
        group=4
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            safe_handle_message
        ),
        group=5
    )

    print("✅ RJ BOT ASSISTANT is running smoothly with multi-agent routing...")

    app.run_polling(
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()