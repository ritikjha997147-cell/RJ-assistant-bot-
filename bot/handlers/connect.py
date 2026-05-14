from telegram import Update
from telegram.ext import ContextTypes


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"""
✅ Connected Successfully

Your Chat ID:

{chat_id}

Is ID ko RJ use karega future messages bhejne ke liye.
"""
    )
