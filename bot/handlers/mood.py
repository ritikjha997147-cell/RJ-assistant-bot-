from telegram import Update
from telegram.ext import ContextTypes

from bot.config import OWNER_ID
from bot.handlers.shared import BOT_PERSONALITY


async def set_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global BOT_PERSONALITY

    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "/mood savage ya /mood formal"
        )

        return

    mood = context.args[0].lower()

    if mood in ["savage", "formal"]:

        import bot.handlers.shared as shared

        shared.BOT_PERSONALITY = mood

        await update.message.reply_text(
            f"✅ Mood set to {mood}"
        )
