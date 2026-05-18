from telegram import Update
from telegram.ext import ContextTypes

import sqlite3


ADMIN_ID = 7859072136


async def today(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id != ADMIN_ID:

        await update.message.reply_text(
            "Access denied"
        )

        return

    conn = sqlite3.connect("bot.db")

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            telegram_id,
            first_name,
            message_count
        FROM users
        ORDER BY message_count DESC
        LIMIT 10
        """
    )

    users = cursor.fetchall()

    if not users:

        await update.message.reply_text(
            "No users found"
        )

        return

    text = "📊 TODAY USERS\n\n"

    for user in users:

        text += (
            f"👤 {user[1]}\n"
            f"🆔 {user[0]}\n"
            f"💬 Messages: {user[2]}\n\n"
        )

    await update.message.reply_text(text)
