from telegram import Update
from telegram.ext import ContextTypes

from bot.memory.user_memory import LAST_IMAGE


async def show_last_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id not in LAST_IMAGE:

        await update.message.reply_text(
            "Koi image saved nahi hai."
        )

        return

    file_id = LAST_IMAGE[user_id]

    await update.message.reply_photo(
        photo=file_id,
        caption="Ye tumhari last image hai ✅"
    )
