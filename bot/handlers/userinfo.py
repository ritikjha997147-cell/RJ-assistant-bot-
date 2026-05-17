from telegram import Update
from telegram.ext import ContextTypes

from bot.database.users import get_user


async def userinfo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    data = get_user(user_id)

    if not data:

        await update.message.reply_text(
            "User not found."
        )

        return

    telegram_id = data[0]
    username = data[1]
    first_name = data[2]
    last_name = data[3]
    message_count = data[4]

    text = (
        f"👤 Name: {first_name}\n"
        f"🆔 ID: {telegram_id}\n"
        f"📛 Username: @{username}\n"
        f"💬 Messages: {message_count}"
    )

    await update.message.reply_text(text)
