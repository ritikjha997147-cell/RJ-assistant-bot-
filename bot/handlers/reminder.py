import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.database.reminder_db import add_reminder


async def remind(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if len(context.args) < 3:

        await update.message.reply_text(
            "Use:\n/remind 10 min Homework"
        )

        return

    try:

        amount = int(context.args[0])

        unit = context.args[1].lower()

        message = " ".join(context.args[2:])

        # TIME CONVERSION

        if unit in ["sec", "second", "seconds"]:

            seconds = amount

        elif unit in ["min", "minute", "minutes"]:

            seconds = amount * 60

        elif unit in ["hr", "hour", "hours"]:

            seconds = amount * 3600

        elif unit in ["day", "days"]:

            seconds = amount * 86400

        else:

            await update.message.reply_text(
                "❌ Time unit galat hai.\nUse: sec / min / hr / day"
            )

            return

        remind_time = time.time() + seconds

        add_reminder(
            update.effective_chat.id,
            message,
            remind_time
        )

        await update.message.reply_text(
            f"✅ Reminder set:\n{amount} {unit}\n📝 {message}"
        )

    except Exception as e:

        print(e)

        await update.message.reply_text(
            "❌ Time samajh nahi aya."
        )
