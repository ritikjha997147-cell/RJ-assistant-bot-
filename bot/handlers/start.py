import random
from telegram import Update
from telegram.ext import ContextTypes

from bot.memory.user_memory import (
    USER_DATA,
    PENDING_VERIFICATION
)
from bot.memory.db_channel import save_user_data
from bot.handlers.shared import BOT_PERSONALITY

# =========================
# ASYNC HELP COMMAND
# =========================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # parse_mode="Markdown" इस्तेमाल किया है ताकि ** बोल्ड टेक्स्ट काम करे
    await update.message.reply_text(
        text=(
            "🤖 *RJ BOT PRO - Help Menu*\n\n"
            "यहाँ मेरी सभी कमांड्स की लिस्ट है:\n"
            "🔹 /start - बोट को शुरू करें\n"
            "🔹 /hello - वेलकम मैसेज देखें\n"
            "🔹 /help - यह हेल्प मेनू देखें\n"
            "🔹 /today - आज का शेड्यूल / टास्क देखें\n"
            "🔹 /mood - बोट का मूड बदलें\n"
            "🔹 /search <query> - वेब पर सर्च करें\n"
            "🔹 /showlast - आखिरी फोटो देखें\n"
            "🔹 /remind - रिमाइन्डर सेट करें\n"
            "🔹 /connect - नए कनेक्शन सेट करें\n"
            "🔹 /sendlater - मैसेज शेड्यूल करें\n"
            "🔹 /userinfo - अपनी यूजर प्रोफाइल देखें\n"
            "🔹 /send या /msg - डायरेक्ट मैसेज भेजें"
        ),
        parse_mode="Markdown"
    )

# =========================
# ASYNC START COMMAND
# =========================
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