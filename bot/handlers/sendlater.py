import time
import sqlite3

from telegram import Update
from telegram.ext import ContextTypes


conn = sqlite3.connect(
    "bot/database/bot.db",
    check_same_thread=False
)

cursor = conn.cursor()


async def sendlater(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 4:

        await update.message.reply_text(
            "Use:\n/sendlater CHAT_ID 10 sec hello"
        )

        return

    target_id = int(context.args[0])

    value = int(context.args[1])

    unit = context.args[2]

    message = " ".join(context.args[3:])

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

    send_time = time.time() + seconds

    cursor.execute(
        """
        INSERT INTO scheduled_messages
        (sender_id, target_id, message, send_time)
        VALUES (?, ?, ?, ?)
        """,
        (
            update.effective_chat.id,
            target_id,
            message,
            send_time
        )
    )

    conn.commit()

    await update.message.reply_text(
        "✅ Scheduled successfully"
    )
