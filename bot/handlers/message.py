import asyncio
import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.ai.responder import generate_response
from bot.ai.classifier import needs_web_search

from bot.memory.user_memory import (
    USER_DATA,
    USER_COOLDOWN,
    PENDING_VERIFICATION
)

from bot.memory.db_channel import save_user_data

from bot.handlers.shared import BOT_PERSONALITY

from bot.config import COOLDOWN_TIME


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    user_name = update.effective_user.first_name

    text = update.message.text

    # AI search detection

    search_needed = await asyncio.to_thread(
        needs_web_search,
        text
    )

    print("SEARCH NEEDED:", search_needed)

    # verification

    if user_id in PENDING_VERIFICATION:

        try:

            if int(text) == PENDING_VERIFICATION[user_id]:

                del PENDING_VERIFICATION[user_id]

                USER_DATA[str(user_id)] = {
                    "name": user_name,
                    "count": 0
                }

                await save_user_data(context)

                await update.message.reply_text(
                    "✅ Verification successful"
                )

            else:

                await update.message.reply_text(
                    "❌ Wrong answer"
                )

            return

        except:
            return

    # cooldown

    now = time.time()

    if (
        user_id in USER_COOLDOWN
        and now - USER_COOLDOWN[user_id]
        < COOLDOWN_TIME
    ):

        await update.message.reply_text(
            "Ruk ja bhai ☕"
        )

        return

    USER_COOLDOWN[user_id] = now

    # personality

    if BOT_PERSONALITY == "savage":

        system_prompt = (
            "You are RJ BOT PRO. "
            "Speak like savage Delhi guy "
            "using Hinglish."
        )

    else:

        system_prompt = (
            "You are a professional consultant."
        )

    # ai response

    response = await asyncio.to_thread(
        generate_response,
        system_prompt,
        text
    )

    # stats

    if str(user_id) in USER_DATA:

        USER_DATA[str(user_id)]["count"] += 1

    await update.message.reply_text(response)
