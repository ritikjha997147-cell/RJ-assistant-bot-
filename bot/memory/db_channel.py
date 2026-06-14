import json

from bot.memory.user_memory import USER_DATA
from bot.config import DATABASE_CHANNEL_ID


async def save_user_data(context):

    if not DATABASE_CHANNEL_ID:
        return

    try:

        data_string = json.dumps(
            USER_DATA,
            ensure_ascii=False
        )

        await context.bot.send_message(
            chat_id=DATABASE_CHANNEL_ID,
            text=f"☁️ CLOUD_SAVE:\n{data_string}"
        )

    except Exception as e:

        print(f"SAVE ERROR: {e}")
