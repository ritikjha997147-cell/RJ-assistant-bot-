import asyncio
import time

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from bot.ai.responder import generate_response
from bot.ai.classifier import needs_web_search

from bot.memory.chat_backup import backup_chat

from bot.memory.user_memory import (
    USER_DATA,
    USER_COOLDOWN,
    PENDING_VERIFICATION
)

from bot.memory.db_channel import save_user_data

from bot.handlers.shared import BOT_PERSONALITY

from bot.config import COOLDOWN_TIME

from bot.database.chat_memory import (
    save_message,
    get_last_messages
)


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = update.message.text

    # TYPING STATUS

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    # SAVE USER MESSAGE

    save_message(
        user_id,
        "user",
        text
    )

    await backup_chat(
        context,
        user_id,
        "user",
        text
    )

    # VERIFICATION SYSTEM

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

    # COOLDOWN

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

    # SEARCH CHECK

    search_needed = await asyncio.to_thread(
        needs_web_search,
        text
    )

    print("SEARCH NEEDED:", search_needed)

    # PERSONALITY

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

    # LOAD MEMORY FROM DATABASE

    memory = get_last_messages(
        user_id,
        limit=10
    )

    conversation_context = ""

    for role, msg in memory:

        conversation_context += (
            f"{role}: {msg}\n"
        )

    # FINAL PROMPT

    final_prompt = (
        f"{conversation_context}\n"
        f"user: {text}"
    )

    # AI RESPONSE

    response = await asyncio.to_thread(
        generate_response,
        system_prompt,
        final_prompt
    )

    # HUMAN LIKE DELAY

    await asyncio.sleep(5)

    # SAVE BOT REPLY

    save_message(
        user_id,
        "assistant",
        response
    )

    await backup_chat(
        context,
        user_id,
        "bot",
        response
    )

    # USER STATS

    if str(user_id) in USER_DATA:

        USER_DATA[str(user_id)]["count"] += 1

    # SEND REPLY

    await update.message.reply_text(
        response
    )
