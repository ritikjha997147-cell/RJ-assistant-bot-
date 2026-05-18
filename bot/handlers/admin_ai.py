import re

from telegram import Update
from telegram.ext import ContextTypes


ADMIN_ID = 7859072136


async def admin_ai_control(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # ONLY OWNER

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text


    # =========================
    # SEND MESSAGE SYSTEM
    # =========================

    pattern = r"(\d+)\sko\s(bhejo|bolo)\s(.+)"

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        target_id = int(
            match.group(1)
        )

        message = match.group(3)

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=message
            )

            await update.message.reply_text(
                "✅ Message sent"
            )

        except Exception as e:

            await update.message.reply_text(
                f"❌ Error:\n{e}"
            )

        return


    # =========================
    # HELP
    # =========================

    if "admin help" in text.lower():

        await update.message.reply_text(

            "ADMIN AI COMMANDS\n\n"

            "Example:\n"
            "7859072136 ko bhejo hello\n\n"

            "OR\n\n"

            "7859072136 ko bolo kal test hai"
        )
