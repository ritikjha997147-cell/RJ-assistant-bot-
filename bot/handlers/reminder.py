import time
import dateparser
from telegram import Update
from telegram.ext import ContextTypes
from bot.database.reminder_db import add_reminder, get_all_reminders_for_user, delete_reminder

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⏰ *Reminder Usage:*\n\n"
            "*By time unit:*\n"
            "/remind 10 min Homework\n"
            "/remind 2 hr Call doctor\n"
            "/remind 1 day Pay bills\n\n"
            "*By exact time:*\n"
            "/remind 5:30pm Meeting\n"
            "/remind tomorrow 9am Wake up\n"
            "/remind 25 june 8pm Party\n\n"
            "*View reminders:* /reminders\n"
            "*Cancel reminder:* /cancelreminder 1",
            parse_mode="Markdown"
        )
        return
    try:
        first = context.args[0]
        if first.isdigit() and len(context.args) >= 3:
            amount = int(first)
            unit = context.args[1].lower()
            message = " ".join(context.args[2:])
            if unit in ["sec", "second", "seconds"]:
                seconds = amount
            elif unit in ["min", "minute", "minutes"]:
                seconds = amount * 60
            elif unit in ["hr", "hour", "hours"]:
                seconds = amount * 3600
            elif unit in ["day", "days"]:
                seconds = amount * 86400
            else:
                seconds = None
            if seconds:
                remind_time = time.time() + seconds
                add_reminder(update.effective_chat.id, message, remind_time)
                await update.message.reply_text(
                    f"✅ *Reminder Set!*\n\n⏱ In: *{amount} {unit}*\n📝 Task: *{message}*",
                    parse_mode="Markdown"
                )
                return
        parsed_time = None
        message = ""
        for i in range(len(context.args), 0, -1):
            time_str = " ".join(context.args[:i])
            parsed = dateparser.parse(time_str, settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata"})
            if parsed and parsed.timestamp() > time.time():
                parsed_time = parsed
                message = " ".join(context.args[i:])
                break
        if parsed_time and message:
            remind_time = parsed_time.timestamp()
            add_reminder(update.effective_chat.id, message, remind_time)
            time_str = parsed_time.strftime("%d %b %Y at %I:%M %p")
            await update.message.reply_text(
                f"✅ *Reminder Set!*\n\n📅 On: *{time_str}*\n📝 Task: *{message}*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Samajh nahi aaya! Try:\n/remind 10 min Homework\n/remind tomorrow 9am Meeting",
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"[REMINDER ERROR]: {e}")
        await update.message.reply_text("❌ Error hua. Try: /remind 10 min task", parse_mode="Markdown")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = get_all_reminders_for_user(update.effective_chat.id)
    if not reminders:
        await update.message.reply_text("📭 Koi reminder nahi hai abhi.")
        return
    text = "⏰ *Your Reminders:*\n\n"
    for r in reminders:
        rid, chat_id, message, remind_at = r
        t = time.strftime("%d %b %Y %I:%M %p", time.localtime(remind_at))
        text += f"*#{rid}* - {message}\n📅 {t}\n\n"
    text += "_Cancel: /cancelreminder ID_"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /cancelreminder 1", parse_mode="Markdown")
        return
    try:
        rid = int(context.args[0])
        delete_reminder(rid)
        await update.message.reply_text(f"✅ Reminder #{rid} cancel ho gaya!")
    except Exception as e:
        await update.message.reply_text("❌ ID galat hai.")
