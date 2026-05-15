import logging
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from bot.config import BOT_TOKEN

from bot.handlers.start import start
from bot.handlers.mood import set_mood
from bot.handlers.message import handle_message
from bot.handlers.image import handle_image
from bot.handlers.showlast import show_last_image
from bot.handlers.reminder import remind
from bot.handlers.connect import connect
from bot.handlers.sendlater import sendlater

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
            "Kuch mila nahi bhai."
        )

        return

    formatted = []

    for r in results:

        formatted.append(
            f"🔹 {r['title']}\n{r['url']}"
        )

    response = "\n\n".join(formatted)

    await update.message.reply_text(response)


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

    # GLOBAL ERROR HANDLER

    app.add_error_handler(
        error_handler
    )

    # COMMANDS

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "mood",
            set_mood
        )
    )

    app.add_handler(
        CommandHandler(
            "search",
            search_command
        )
    )

    app.add_handler(
        CommandHandler(
            "showlast",
            show_last_image
        )
    )

    app.add_handler(
        CommandHandler(
            "remind",
            remind
        )
    )

    app.add_handler(
        CommandHandler(
            "connect",
            connect
        )
    )

    app.add_handler(
        CommandHandler(
            "sendlater",
            sendlater
        )
    )

    # IMAGE HANDLER

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_image
        )
    )

    # SAFE TEXT HANDLER

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            safe_handle_message
        )
    )

    print("✅ RJ BOT PRO RUNNING")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":

    main()
