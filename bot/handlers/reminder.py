async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 3:

        await update.message.reply_text(
            "Usage:\n/remind 10 min homework"
        )

        return

    try:

        amount = int(context.args[0])

    except:

        await update.message.reply_text(
            "Invalid time."
        )

        return

    unit = context.args[1].lower()

    if unit in ["min", "minute", "minutes"]:

        delay = amount * 60

    elif unit in ["sec", "second", "seconds"]:

        delay = amount

    elif unit in ["hour", "hours"]:

        delay = amount * 3600

    else:

        await update.message.reply_text(
            "Use sec/min/hour"
        )

        return

    reminder_text = " ".join(context.args[2:])

    run_time = datetime.now() + timedelta(
        seconds=delay
    )

    scheduler.add_job(
        send_reminder,
        "date",
        run_date=run_time,
        args=[
            update.effective_chat.id,
            reminder_text,
            context
        ]
    )

    await update.message.reply_text(
        f"✅ Reminder set for {amount} {unit}."
    )
