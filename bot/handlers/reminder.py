import re, time
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from bot.database.reminder_db import add_reminder, get_all_reminders_for_user, delete_reminder
from bot.reminders.natural_reminder import parse_hinglish_reminder
from bot.reminders.scheduler import schedule_reminder

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Reminder Usage:\n/remind kal subah 5:00 baje kaam\n/remind parson 3pm call papa\n/remind 10 min homework\n/remind tomorrow 9am meeting")
        return
    chat_id = update.effective_chat.id
    full_text = " ".join(context.args)
    unit_match = re.match(r'^(\d+)\s*(sec|second|seconds|min|minute|minutes|hr|hour|hours|day|days)\s+(.+)$', full_text, re.IGNORECASE)
    if unit_match:
        amount = int(unit_match.group(1))
        unit = unit_match.group(2).lower()
        message = unit_match.group(3).strip()
        unit_map = {"sec":1,"second":1,"seconds":1,"min":60,"minute":60,"minutes":60,"hr":3600,"hour":3600,"hours":3600,"day":86400,"days":86400}
        remind_at = time.time() + amount * unit_map[unit]
        rid = add_reminder(chat_id, message, remind_at)
        schedule_reminder(context.bot, rid, chat_id, message, remind_at)
        run_time = datetime.fromtimestamp(remind_at).strftime("%d %b %Y at %I:%M %p")
        await update.message.reply_text(f"Reminder Set!\nIn: {amount} {unit}\nAt: {run_time}\nTask: {message}")
        return
    remind_at, message = parse_hinglish_reminder(full_text)
    if remind_at and message:
        rid = add_reminder(chat_id, message, remind_at)
        schedule_reminder(context.bot, rid, chat_id, message, remind_at)
        run_time = datetime.fromtimestamp(remind_at).strftime("%d %b %Y at %I:%M %p")
        await update.message.reply_text(f"Reminder Set!\nDate & Time: {run_time}\nTask: {message}")
        return
    import dateparser
    words = full_text.split()
    parsed_dt = None
    message = ""
    for i in range(len(words), 0, -1):
        parsed = dateparser.parse(" ".join(words[:i]), settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata"})
        if parsed and parsed.timestamp() > time.time():
            parsed_dt = parsed
            message = " ".join(words[i:])
            break
    if parsed_dt and message:
        rid = add_reminder(chat_id, message, parsed_dt.timestamp())
        schedule_reminder(context.bot, rid, chat_id, message, parsed_dt.timestamp())
        await update.message.reply_text(f"Reminder Set!\nAt: {parsed_dt.strftime('%d %b %Y at %I:%M %p')}\nTask: {message}")
    else:
        await update.message.reply_text("Samajh nahi aaya!\nTry: /remind kal subah 5:00 baje kaam\nOr: /remind 10 min task")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = get_all_reminders_for_user(update.effective_chat.id)
    if not reminders:
        await update.message.reply_text("Koi reminder nahi hai abhi.")
        return
    text = "Your Reminders:\n\n"
    for r in reminders:
        rid, chat_id, message, remind_at = r
        t = datetime.fromtimestamp(remind_at).strftime("%d %b %Y %I:%M %p")
        text += f"#{rid} - {message}\n{t}\n\n"
    text += "Cancel: /cancelreminder ID"
    await update.message.reply_text(text)

async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /cancelreminder 1")
        return
    try:
        rid = int(context.args[0])
        from bot.reminders.scheduler import scheduler
        try:
            scheduler.remove_job(f"reminder_{rid}")
        except Exception:
            pass
        delete_reminder(rid)
        await update.message.reply_text(f"Reminder #{rid} cancel ho gaya!")
    except Exception:
        await update.message.reply_text("ID galat hai.")
