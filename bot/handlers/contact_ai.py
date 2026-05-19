import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.database.contacts import (
    add_contact,
    get_contact,
    get_all_contacts
)


ADMIN_ID = 7859072136


async def contact_ai(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text


    # =========================
    # ADD CONTACT
    # =========================

    add_pattern = (
        r"add contact (\d+)\s(.+)"
    )

    add_match = re.search(
        add_pattern,
        text,
        re.IGNORECASE
    )

    if add_match:

        telegram_id = int(
            add_match.group(1)
        )

        custom_name = add_match.group(2).strip()

        add_contact(
            telegram_id,
            custom_name
        )

        await update.message.reply_text(
            f"✅ Contact saved:\n\n"
            f"Name: {custom_name}\n"
            f"ID: {telegram_id}"
        )

        return


    # =========================
    # SHOW CONTACTS
    # =========================

    if text.lower() == "show contacts":

        contacts = get_all_contacts()

        if not contacts:

            await update.message.reply_text(
                "No contacts found."
            )

            return

        response = "📒 CONTACTS\n\n"

        for c in contacts:

            response += (
                f"Name: {c[1]}\n"
                f"ID: {c[0]}\n\n"
            )

        await update.message.reply_text(
            response
        )

        return


    # =========================
    # SEND MESSAGE
    # =========================

    send_pattern = (
        r"(.+?)\sko\s(bhejo|bolo)\s(.+)"
    )

    send_match = re.search(
        send_pattern,
        text,
        re.IGNORECASE
    )

    if send_match:

        custom_name = send_match.group(1).strip()

        message = send_match.group(3)

        result = get_contact(
            custom_name
        )

        if not result:

            await update.message.reply_text(
                "❌ Contact not found"
            )

            return

        telegram_id = result[0]

        try:

            await context.bot.send_message(
                chat_id=telegram_id,
                text=message
            )

            await update.message.reply_text(
                "✅ Message sent"
            )

        except Exception as e:

            await update.message.reply_text(
                f"❌ Error:\n{e}"
            )
