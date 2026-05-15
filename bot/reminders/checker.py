import asyncio
import time

from bot.database.reminder_db import (
get_due_reminders,
delete_reminder
)

async def reminder_checker(app):

```
while True:

    current_time = time.time()

    reminders = get_due_reminders(
        current_time
    )

    for reminder in reminders:

        reminder_id = reminder[0]
        chat_id = reminder[1]
        message = reminder[2]

        await app.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ Reminder:\n{message}"
        )

        delete_reminder(reminder_id)

    await asyncio.sleep(5)
```
