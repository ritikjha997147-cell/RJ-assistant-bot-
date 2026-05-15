from bot.config import MEMORY_CHANNEL_ID


async def save_cloud_memory(
    context,
    user_id,
    role,
    message
):

    if not MEMORY_CHANNEL_ID:
        return

    text = (
        f"USER:{user_id}\n"
        f"ROLE:{role}\n"
        f"MSG:{message}"
    )

    try:

        await context.bot.send_message(
            chat_id=MEMORY_CHANNEL_ID,
            text=text
        )

    except Exception as e:

        print(f"[MEMORY ERROR]: {e}")
