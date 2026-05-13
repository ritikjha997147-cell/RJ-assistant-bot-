import asyncio

from telegram import Update
from telegram.ext import ContextTypes


async def remind_later(
    context,
    chat_id,
    seconds,
    message
):

    await asyncio.sleep(seconds)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ Reminder:\n{message}"
    )


async def reminder_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if len(context.args) < 2:

        await update.message.reply_text(
            "Use:\n/remind 60 Homework kar"
        )

        return

    try:

        seconds = int(context.args[0])

    except:

        await update.message.reply_text(
            "Time number me do."
        )

        return

    reminder_text = " ".join(context.args[1:])

    asyncio.create_task(
        remind_later(
            context,
            update.effective_chat.id,
            seconds,
            reminder_text
        )
    )

    await update.message.reply_text(
        f"✅ Reminder set.\n{seconds} sec baad yaad dilaunga."
    )
