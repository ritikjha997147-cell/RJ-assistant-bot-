from telegram import Update
from telegram.ext import ContextTypes

from bot.config import IMAGE_DB_CHANNEL_ID
from bot.memory.user_memory import LAST_IMAGE


async def handle_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    photo = update.message.photo[-1]

    file_id = photo.file_id

    user = update.effective_user

    # save last image

    LAST_IMAGE[user.id] = file_id

    caption = (
        f"📸 New Image\n\n"
        f"User: {user.first_name}\n"
        f"ID: {user.id}"
    )

    # save to DB channel

    await context.bot.send_photo(
        chat_id=IMAGE_DB_CHANNEL_ID,
        photo=file_id,
        caption=caption
    )

    await update.message.reply_text(
        "Image saved ✅"
    )
