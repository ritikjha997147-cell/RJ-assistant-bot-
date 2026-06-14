from telegram import Update
from telegram.ext import ContextTypes
# अपनी फाइल का सही पाथ इम्पोर्ट करो (जैसे bot.database.contacts)
from bot.database.contacts import add_contact 

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    args = context.args

   
    if len(args) < 3 or args[1].lower() != "as":
        await update.message.reply_text("❌ Format galat hai bhai! Sahi format: /connect <telegram_id> as <name>")
        return

    try:
        telegram_id = int(args[0]) # ID को integer में बदलो
        custom_name = args[2].strip() # नाम के आस-पास की फालतू स्पेस हटाओ

        
        add_contact(telegram_id=telegram_id, custom_name=custom_name)

        await update.message.reply_text(
            f"""
✅ Connected Successfully

Target Name: {custom_name}
Target Chat ID: {telegram_id}

Is ID ko RJ use karega future messages bhejne ke liye.
"""
        )
    except ValueError:
        await update.message.reply_text("❌ ID hamesha ek number honi chahiye bhai!")