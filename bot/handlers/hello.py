from telegram import Update
from telegram.ext import ContextTypes

# 1. Command Handler Function 
async def hello_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # यूजर का नाम निकालने के लिए
    user_name = update.effective_user.first_name
    
    # यूजर को रिप्लाई भेजने के लिए
    await update.message.reply_text(
        text=f"👋 नमस्ते {user_name}! मैं हूँ RJ ka assistance hu । आपकी कस्टम कमांड बिल्कुल परफेक्ट काम कर रही है।"
    )