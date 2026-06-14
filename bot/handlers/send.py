import traceback

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import OWNER_ID
from bot.database.contacts import get_contact
from bot.database.chat_memory import save_message
from bot.memory.chat_backup import backup_chat
from bot.memory.user_memory import USER_DATA


async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    args = context.args

    if not args or len(args) < 2:
        await update.message.reply_text(
            "❌ Usage: /send <registered_name> <your_message>\nExample: /send ritik bhai kya chal raha hai?"
        )
        return

    # Permission check: only allow OWNER_ID to use this command
    try:
        sender_id = update.effective_user.id
    except Exception:
        sender_id = None

    if OWNER_ID and sender_id != OWNER_ID:
        await update.message.reply_text("❌ Unauthorized access.")
        return

    target_name = args[0].strip().lower()
    message_to_send = " ".join(args[1:]).strip()

    if not message_to_send:
        await update.message.reply_text("❌ Message cannot be empty.")
        return

    # Lookup contact
    contact = get_contact(target_name)

    if not contact:
        await update.message.reply_text(
            f"❌ Contact not found: '{target_name}'. Please register using /connect."
        )
        return

    # Unpack telegram_id (get_contact returns a tuple or None)
    try:
        if isinstance(contact, (tuple, list)):
            telegram_id = contact[0]
        else:
            telegram_id = contact

        await context.bot.send_message(chat_id=telegram_id, text=message_to_send)

        # Feedback to RJ
        response = f"✅ Message successfully sent to {target_name} via direct command."
        await update.message.reply_text(response)

        # Log the assistant message and backup
        try:
            save_message(update.effective_user.id, "assistant", response)
            await backup_chat(context, update.effective_user.id, "bot", response)
            if str(update.effective_user.id) in USER_DATA:
                USER_DATA[str(update.effective_user.id)]["count"] += 1
        except Exception:
            traceback.print_exc()

    except Exception as exc:
        traceback.print_exc()
        await update.message.reply_text(f"❌ Failed to send: {exc}")
