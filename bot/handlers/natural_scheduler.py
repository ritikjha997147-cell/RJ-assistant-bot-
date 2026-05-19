import re
import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.database.contacts import get_contact


# =========================
# NATURAL LANGUAGE SCHEDULER
# =========================

async def natural_scheduler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.lower()

    # =========================
    # PATTERN:
    # Devesh ko bol 30 min baad hello
    # =========================

    pattern = (
        r"([a-zA-Z0-9_]+)\sko\s(bol|bhejo)\s(\d+)\s(min|minute|minutes|hr|hour|hours)\s(baad|bad)\s(.+)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return

    # CONTACT NAME

    custom_name = match.group(1)

    # TIME

    amount = int(match.group(3))

    unit = match.group(4)

    # MESSAGE

    message = match.group(6)

    # GET CONTACT

    result = get_contact(custom_name)

    if not result:

        await update.message.reply_text(
            "❌ Contact not found"
        )

        return

    telegram_id = result[0]

    # CONVERT TIME

    seconds = amount * 60

    if unit in ["hr", "hour", "hours"]:

        seconds = amount * 3600

    # CONFIRMATION

    await update.message.reply_text(
        f"✅ Scheduled message for {custom_name}"
    )

    # WAIT

    await asyncio.sleep(seconds)

    # SEND MESSAGE

    try:

        await context.bot.send_message(
            chat_id=telegram_id,
            text=message
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Failed:\n{e}"
        )
