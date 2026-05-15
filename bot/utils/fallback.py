async def fallback_reply(update):

    text = update.message.text.lower()

    # greetings

    if any(word in text for word in [
        "hi",
        "hello",
        "hey",
        "hlo"
    ]):

        await update.message.reply_text(
            "Hello bhai 😎"
        )

    # bye

    elif "bye" in text:

        await update.message.reply_text(
            "Bye bhai 👋"
        )

    # help

    elif "help" in text:

        await update.message.reply_text(
            """
Available Commands:

/start
/search
/remind
/connect
/sendlater
"""
        )

    # default

    else:

        await update.message.reply_text(
            """
⚠️ AI system temporary issue me hai.

Backup mode active ✅
"""
        )
