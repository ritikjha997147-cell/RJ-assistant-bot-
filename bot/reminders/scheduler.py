from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from bot.database.reminder_db import delete_reminder

scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()}, job_defaults={"misfire_grace_time": 60})

def start_scheduler():
    pass  # scheduler starts in post_init instead

async def send_reminder(bot, chat_id, message, reminder_id):
    try:
        await bot.send_message(chat_id=chat_id, text=f"[REMINDER] {message}", parse_mode="Markdown")
        delete_reminder(reminder_id)
    except Exception as e:
        print(f"[REMINDER ERROR]: {e}")

def schedule_reminder(bot, reminder_id, chat_id, message, remind_at):
    run_time = datetime.fromtimestamp(remind_at)
    scheduler.add_job(send_reminder, trigger="date", run_date=run_time, args=[bot, chat_id, message, reminder_id], id=f"reminder_{reminder_id}", replace_existing=True)

def restore_reminders(bot):
    import time
    from bot.database.reminder_db import get_all_pending_reminders
    pending = get_all_pending_reminders()
    count = 0
    for rid, chat_id, message, remind_at in pending:
        if remind_at > time.time():
            schedule_reminder(bot, rid, chat_id, message, remind_at)
            count += 1
    print(f"[SCHEDULER] Restored {count} pending reminders")

