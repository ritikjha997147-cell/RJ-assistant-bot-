import asyncio
import time
import sqlite3


conn = sqlite3.connect(
    "bot/database/bot.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    target_id INTEGER,
    message TEXT,
    send_time REAL
)
""")

conn.commit()


async def message_scheduler(app):

    while True:

        current_time = time.time()

        cursor.execute(
            "SELECT * FROM scheduled_messages WHERE send_time <= ?",
            (current_time,)
        )

        messages = cursor.fetchall()

        for msg in messages:

            msg_id = msg[0]
            target_id = msg[2]
            message = msg[3]

            try:

                await app.bot.send_message(
                    chat_id=target_id,
                    text=f"""
🤖 HELLO MAI RJ KA ASSISTANT HU

RJ ne aapko ye message bhejne ko kaha hai:

{message}
"""
                )

            except Exception as e:

                print(e)

            cursor.execute(
                "DELETE FROM scheduled_messages WHERE id=?",
                (msg_id,)
            )

            conn.commit()

        await asyncio.sleep(5)
