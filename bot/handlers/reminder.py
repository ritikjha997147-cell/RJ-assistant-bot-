import time
import dateparser

from telegram import Update
from telegram.ext import ContextTypes

from bot.reminders.reminder_db import add_reminder


async def remind(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Usage:\n/remind tomorrow 7pm study"
        )

        return

    full_text = " ".join(context.args)

    parts = full_text.split(" ")

    if len(parts) < 2:

        await update.message.reply_text(
            "Reminder format galat hai."
        )

        return

    # last word = message
    message = parts[-1]

    # baaki sab = time text
    time_text = " ".join(parts[:-1])

    parsed_time = dateparser.parse(
        time_text
    )

    if not parsed_time:

        await update.message.reply_text(
            "Time samajh nahi aya."
        )

        return

    remind_at = parsed_time.timestamp()

    add_reminder(
        update.effective_chat.id,
        message,
        remind_at
    )

    await update.message.reply_text(
        f"✅ Reminder set for:\n{parsed_time}"
    )
