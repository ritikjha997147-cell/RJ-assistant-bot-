from telegram import Update
from telegram.ext import ContextTypes

from datetime import datetime, timedelta

from bot.reminders.scheduler import scheduler


async def send_reminder(bot, chat_id, text):

    await bot.send_message(
        chat_id=chat_id,
        text=f"⏰ Reminder:\n{text}"
    )


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 3:

        await update.message.reply_text(
            "Use:\n/remind 1 min drink water"
        )

        return

    time_value = int(context.args[0])

    time_unit = context.args[1]

    message = " ".join(context.args[2:])

    seconds = 0

    if time_unit == "sec":

        seconds = time_value

    elif time_unit == "min":

        seconds = time_value * 60

    elif time_unit == "hr":

        seconds = time_value * 3600

    else:

        await update.message.reply_text(
            "Use sec / min / hr"
        )

        return

    chat_id = update.effective_chat.id

    scheduler.add_job(
        send_reminder,
        "date",
        run_date=datetime.now() + timedelta(seconds=seconds),
        args=[context.bot, chat_id, message]
    )

    await update.message.reply_text(
        f"✅ Reminder set.\n{time_value} {time_unit} baad yaad dilaunga."
    )
