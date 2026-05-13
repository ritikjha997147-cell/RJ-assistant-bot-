import asyncio
import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.ai.responder import generate_response
from bot.ai.classifier import needs_web_search

from bot.memory.user_memory import (
    USER_DATA,
    USER_COOLDOWN,
    PENDING_VERIFICATION,
    USER_HISTORY
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
    # user history setup

    if user_id not in USER_HISTORY:

        USER_HISTORY[user_id] = []

    USER_HISTORY[user_id].append(
        {
            "role": "user",
            "content": text
        }
    )

    # keep only last 5 messages

    USER_HISTORY[user_id] = USER_HISTORY[user_id][-5:]
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

    # search detection

    search_needed = await asyncio.to_thread(
        needs_web_search,
        text
    )

    print("SEARCH NEEDED:", search_needed)

    # personality

    if BOT_PERSONALITY == "savage":

        with open(
            "bot/personality/savage.txt",
            "r",
            encoding="utf-8"
        ) as file:

            system_prompt = file.read()

    else:

        system_prompt = (
            "You are a professional AI consultant.\n\n"

            "RULES:\n"
            "- Explain clearly\n"
            "- Give structured answers\n"
            "- Use professional tone\n"
            "- Never invent facts\n"
            "- If unsure, say so clearly\n"
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
