import random

from telegram import Update
from telegram.ext import ContextTypes

from bot.memory.user_memory import (
    USER_DATA,
    PENDING_VERIFICATION
)
from telegram import Update

from telegram.ext import ContextTypes

# Async function for /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        text="🤖 **RJ BOT PRO - Help Menu**\n\n"
             "यहाँ मेरी सभी कमांड्स की लिस्ट है:\n"
             "/start - बोट को शुरू करें\n"
             "/hello - वेलकम मैसेज देखें\n"
             "/help - यह हेल्प मेनू देखें"
    )
from bot.memory.db_channel import save_user_data

from bot.handlers.shared import BOT_PERSONALITY


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if str(user_id) not in USER_DATA:

        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)

        answer = num1 + num2

        PENDING_VERIFICATION[user_id] = answer

        await update.message.reply_text(
            f"Oye {user_name}! Bata {num1} + {num2} = ?"
        )

        return

    await update.message.reply_text(
        f"RJ Bot active 😎\nMode: {BOT_PERSONALITY}"
    )
