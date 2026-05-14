import time
import asyncio

from bot.reminders.db import conn, cursor


async def reminder_checker(app):

    while True:

        current_time = time.time()

        cursor.execute(
            "SELECT * FROM reminders WHERE remind_time <= ?",
            (current_time,)
        )

        reminders = cursor.fetchall()

        for reminder in reminders:

            reminder_id = reminder[0]
            chat_id = reminder[1]
            message = reminder[2]

            try:

                await app.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ Reminder:\n{message}"
                )

            except Exception as e:

                print(e)

            cursor.execute(
                "DELETE FROM reminders WHERE id=?",
                (reminder_id,)
            )

            conn.commit()

        await asyncio.sleep(5)
