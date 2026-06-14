import asyncio
import re
import time
import traceback
from datetime import datetime
from typing import Optional, Tuple

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.ai.classifier import needs_web_search
from bot.ai.responder import generate_response
from bot.config import COOLDOWN_TIME, IMAGE_DB_CHANNEL_ID
from bot.database.chat_memory import get_last_messages, save_message
from bot.database.contacts import get_contact
from bot.database.images import search_image_by_keyword
from bot.database.users import create_user, update_user_activity
from bot.memory.chat_backup import backup_chat
from bot.memory.db_channel import save_user_data
from bot.memory.user_memory import (
    PENDING_IMAGE_DESCRIPTION,
    PENDING_VERIFICATION,
    USER_COOLDOWN,
    USER_DATA,
)
from bot.handlers.shared import BOT_PERSONALITY

SEND_CONTACT_BLOCK_RE = re.compile(
    # Accept either 'name:' or 'contact_name:' label, tags on their own lines.
    r"---SEND_CONTACT_START---\s*"
    r"(?:contact_name|name)\s*:\s*(?P<name>.+?)\s*\n"
    r"message\s*:\s*(?P<message>.+?)\s*\n"
    r"---SEND_CONTACT_END---",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


def _extract_contact_directive(response: str) -> Optional[Tuple[str, str, str]]:
    match = SEND_CONTACT_BLOCK_RE.search(response)
    if not match:
        return None

    # Normalize and clean extracted fields
    contact_name = match.group("name").strip()
    # prefer lowercased canonical name for lookup
    contact_name_normalized = contact_name.lower()

    contact_message = match.group("message").strip()

    # Remove the directive block from the human-readable response
    cleaned_response = (response[: match.start()] + response[match.end() :]).strip()

    return contact_name_normalized, contact_message, cleaned_response


def _is_image_request(text: str) -> bool:
    if not text:
        return False

    text = text.lower()
    has_image_keyword = bool(
        re.search(r"\b(image|photo|pic|picture|tasveer)\b", text)
    )
    has_action_word = bool(
        re.search(r"\b(bhejo|dikhao|dekh[ao]?|show|send|mujhe|please)\b", text)
    )

    return has_image_keyword and has_action_word


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    user_name = first_name
    text = update.message.text

    # IMAGE DESCRIPTION MODE
    if user_id in PENDING_IMAGE_DESCRIPTION:
        file_id = PENDING_IMAGE_DESCRIPTION[user_id]

        caption = (
            f"📸 New Image\n\n"
            f"User: {user_name}\n"
            f"ID: {user_id}\n"
            f"Time: {datetime.now()}\n\n"
            f"Description:\n{text}\n\n"
            f"FileID:\n{file_id}"
        )

        await context.bot.send_photo(
            chat_id=IMAGE_DB_CHANNEL_ID,
            photo=file_id,
            caption=caption,
        )

        del PENDING_IMAGE_DESCRIPTION[user_id]
        await update.message.reply_text("✅ Image saved with description")
        return

    # SAVE USER
    create_user(user_id, username, first_name, last_name)
    update_user_activity(user_id)

    # TYPING STATUS
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    # SAVE USER MESSAGE
    save_message(user_id, "user", text)
    await backup_chat(context, user_id, "user", text)

    # VERIFICATION SYSTEM
    if user_id in PENDING_VERIFICATION:
        try:
            if int(text) == PENDING_VERIFICATION[user_id]:
                del PENDING_VERIFICATION[user_id]
                USER_DATA[str(user_id)] = {
                    "name": user_name,
                    "count": 0,
                }
                await save_user_data(context)
                await update.message.reply_text("✅ Verification successful")
            else:
                await update.message.reply_text("❌ Wrong answer")
            return
        except Exception:
            return

    # COOLDOWN
    now = time.time()
    if (
        user_id in USER_COOLDOWN
        and now - USER_COOLDOWN[user_id] < COOLDOWN_TIME
    ):
        await update.message.reply_text("Ruk ja bhai ☕")
        return

    USER_COOLDOWN[user_id] = now

    # DIRECT FORWARDING PATTERN (Legacy Compatibility)
    direct_forward_match = re.match(r"^(\d+)\s+(\w+)\s+(.+)$", text.strip())
    if direct_forward_match:
        try:
            target_id = int(direct_forward_match.group(1))
            target_name = direct_forward_match.group(2)
            message_to_send = direct_forward_match.group(3).strip()

            await context.bot.send_message(chat_id=target_id, text=message_to_send)
            response = f"✅ Message sent to {target_name}."
            save_message(user_id, "assistant", response)
            await backup_chat(context, user_id, "bot", response)
            if str(user_id) in USER_DATA:
                USER_DATA[str(user_id)]["count"] += 1
            await update.message.reply_text(response)
            return
        except ValueError:
            pass
        except Exception as exc:
            traceback.print_exc()
            await update.message.reply_text(f"❌ Failed to send: {exc}")
            return

    # NATURAL LANGUAGE IMAGE RETRIEVAL
    if _is_image_request(text):
        file_id = search_image_by_keyword(text)

        if file_id:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=file_id,
                )
                response = "✅ Image mil gayi, dekh lijiye."
                save_message(user_id, "assistant", response)
                await backup_chat(context, user_id, "bot", response)
                if str(user_id) in USER_DATA:
                    USER_DATA[str(user_id)]["count"] += 1
                await update.message.reply_text(response)
                return
            except Exception as exc:
                await update.message.reply_text(
                    f"❌ Image mili, lekin bhejne mein problem hui: {exc}"
                )
                return

        await update.message.reply_text(
            "Bhai, mere database mein aisi koi image nahi mili."
        )
        return

    # SEARCH CHECK
    search_needed = await asyncio.to_thread(needs_web_search, text)
    print("SEARCH NEEDED:", search_needed)

    # PERSONALITY
    if BOT_PERSONALITY == "savage":
        with open("bot/personality/savage.txt", "r", encoding="utf-8") as file:
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

    system_prompt = (
        "STRICT INSTRUCTION: The user is asking to send a message to a registered contact. "
        "Do NOT engage in casual conversation or say 'Bhai, yehi ho raha tha'. "
        "You MUST immediately and exclusively format your response with the following directive tags, nothing else:\n"
        "---SEND_CONTACT_START---\n"
        "contact_name: ritik\n"
        "message: main late ho jaunga\n"
        "---SEND_CONTACT_END---\n"
        "If you fail to output these exact tags, the system will break."
    ) + "\n" + system_prompt

    system_prompt += (
        "\n\n⚠️ RULE NUMBER 1: If the user commands you to send/forward a message to anyone registered (e.g., 'ritik ko hi bhejo'), you must NOT reply with plain conversational text. You MUST strictly append this exact block to your output so the parser can catch it:\n"
        "---SEND_CONTACT_START---\n"
        "contact_name: ritik\n"
        "message: <user's intended message>\n"
        "---SEND_CONTACT_END---\n"
        "Only append this block for actual contact send requests. Do not invent or modify it for other outputs."
    )

    # LOAD MEMORY FROM DATABASE
    memory = get_last_messages(user_id, limit=10)
    conversation_context = ""
    for role, msg in memory:
        conversation_context += f"{role}: {msg}\n"

    # FINAL PROMPT
    final_prompt = f"{conversation_context}\nuser: {text}"

    # AI RESPONSE
    response = await asyncio.to_thread(generate_response, system_prompt, final_prompt)

    # DEBUG: record raw LLM output for auditing
    try:
        print("LLM RAW OUTPUT:", response)
        save_message(user_id, "assistant_llm", response)
        await backup_chat(context, user_id, "llm", response)
    except Exception:
        traceback.print_exc()

    # DETECT CONTACT SEND INTENT
    directive = _extract_contact_directive(response)
    if directive:
        target_name, message_to_send, cleaned_response = directive
        # contact_name is already normalized to lowercase by the extractor
        # Debug: log extracted directive for auditing
        try:
            print("EXTRACTED DIRECTIVE:", target_name, message_to_send)
            save_message(user_id, "assistant_directive", f"{target_name}: {message_to_send}")
            await backup_chat(context, user_id, "directive", f"{target_name}: {message_to_send}")
        except Exception:
            traceback.print_exc()
        contact = get_contact(target_name)

        if not contact:
            response = (
                (cleaned_response + "\n\n") if cleaned_response else ""
            ) + f"❌ Contact not found: {target_name}\nPlease register the contact and try again."
        else:
            telegram_id = contact[0]
            try:
                await context.bot.send_message(chat_id=telegram_id, text=message_to_send)
                response = (
                    (cleaned_response + "\n\n") if cleaned_response else ""
                ) + f"✅ Message sent to {target_name}."
            except Exception as exc:
                traceback.print_exc()
                response = (
                    (cleaned_response + "\n\n") if cleaned_response else ""
                ) + f"❌ Failed to send to {target_name}: {exc}"

    # HUMAN LIKE DELAY
    await asyncio.sleep(5)

    # SAVE BOT REPLY
    save_message(user_id, "assistant", response)
    await backup_chat(context, user_id, "bot", response)

    # USER STATS
    if str(user_id) in USER_DATA:
        USER_DATA[str(user_id)]["count"] += 1

    # SEND REPLY
    await update.message.reply_text(response)
0