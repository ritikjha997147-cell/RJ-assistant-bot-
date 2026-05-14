import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.reminders.db import conn, cursor


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 3:

        await update.message.reply_text(
            "Use:\n/remind 1 min drink water"
        )

        return

    value = int(context.args[0])

    unit = context.args[1]

    message = " ".join(context.args[2:])

    seconds = 0

    if unit == "sec":

        seconds = value

    elif unit == "min":

        seconds = value * 60

    elif unit == "hr":

        seconds = value * 3600

    else:

        await update.message.reply_text(
            "Use sec / min / hr"
        )

        return

    remind_time = time.time() + seconds

    cursor.execute(
        "INSERT INTO reminders (chat_id, message, remind_time) VALUES (?, ?, ?)",
        (
            update.effective_chat.id,
            message,
            remind_time
        )
    )

    conn.commit()

    await update.message.reply_text(
        f"✅ Reminder set for {value} {unit}"
    )
