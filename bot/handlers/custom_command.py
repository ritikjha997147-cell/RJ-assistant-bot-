from telegram import Update
from telegram.ext import ContextTypes

from bot.database.custom_commands import (
    add_command,
    get_command
)


async def create_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if len(context.args) < 2:

        await update.message.reply_text(
            "Use:\n/createcommand study Hello"
        )

        return

    command = context.args[0]

    response = " ".join(
        context.args[1:]
    )

    add_command(
        update.effective_user.id,
        command,
        response
    )

    await update.message.reply_text(
        f"✅ Command /{command} created"
    )


async def run_custom_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    if not text.startswith("/"):

        return

    command = text[1:]

    response = get_command(
        update.effective_user.id,
        command
    )

    if response:

        await update.message.reply_text(
            response
        )
