from bot.config import DATABASE_CHANNEL_ID


async def backup_chat(
    context,
    user_id,
    role,
    message
):

    try:

        await context.bot.send_message(
            chat_id=DATABASE_CHANNEL_ID,
            text=f"""
USER_ID:{user_id}

{role.upper()}:
{message}
"""
        )

    except Exception as e:

        print(f"[BACKUP ERROR]: {e}")
