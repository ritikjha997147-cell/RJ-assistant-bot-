import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from bot.config import BOT_TOKEN

from bot.handlers.start import start
from bot.handlers.mood import set_mood
from bot.handlers.message import handle_message
from bot.handlers.image import handle_image

from bot.search.ddgs_engine import search_web


logging.basicConfig(level=logging.INFO)


async def search_command(update, context):

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


def main():

    app = Application.builder().token(BOT_TOKEN).build()

    # commands

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("mood", set_mood)
    )

    app.add_handler(
        CommandHandler("search", search_command)
    )

    # image handler

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_image
        )
    )

    # text handler

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("✅ RJ BOT PRO RUNNING")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":

    main()
