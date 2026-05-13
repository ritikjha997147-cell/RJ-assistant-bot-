from telegram import Update
from telegram.ext import ContextTypes

from bot.config import IMAGE_DB_CHANNEL_ID


async def handle_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    photo = update.message.photo[-1]

    file_id = photo.file_id

    user = update.effective_user

    caption = (
        f"📸 New Image\n\n"
        f"User: {user.first_name}\n"
        f"ID: {user.id}"
    )

    await context.bot.send_photo(
        chat_id=IMAGE_DB_CHANNEL_ID,
        photo=file_id,
        caption=caption
    )

    await update.message.reply_text(
        "Image saved ✅"
    )
