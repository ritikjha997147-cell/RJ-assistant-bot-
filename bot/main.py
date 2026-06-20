import logging
import asyncio
import sys
import os

from flask import Flask  # FIX: Corrected Flask casing to avoid internal module crash
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from bot.config import BOT_TOKEN, OWNER_ID

from bot.handlers.code_manager import handle_code_management, handle_replacement_callback
from bot.handlers.start import start, help_command
from bot.handlers.mood import set_mood
from bot.handlers.message import handle_message
from bot.handlers.image import handle_image
from bot.handlers.showlast import show_last_image
from bot.handlers.reminder import remind
from bot.handlers.connect import connect
from bot.handlers.sendlater import sendlater
from bot.handlers.userinfo import userinfo
from bot.handlers.today import today

# नए और मर्ज किए गए दोनों फंक्शंस का इम्पोर्ट
from bot.handlers.send import send_command, handle_owner_confirmation

from bot.handlers.hello import hello_command
from bot.handlers.natural_scheduler import natural_scheduler
from bot.handlers.admin_ai import admin_ai_control
from bot.handlers.contact_ai import contact_ai

from bot.reminders.checker import reminder_checker
from bot.reminders.message_scheduler import message_scheduler

from bot.search.ddgs_engine import search_web
from bot.utils.fallback import fallback_reply
from bot.utils.error_auditor import analyze_and_fix_error  # FIX: Corrected import path syntax

logging.basicConfig(level=logging.INFO)

# =========================
# UPGRADED GLOBAL ERROR HANDLER (Automated Error Fixer Hooked)
# =========================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    # एरर लॉग्स टर्मिनल और रेंडर कंसोल पर भी दिखते रहेंगे
    print(f"[GLOBAL ERROR]: {error}", file=sys.stderr)
    
    try:
        # जेमिनी इंजन से फिक्स कोड बैकग्राउंड में मांगना
        fixed_code = analyze_and_fix_error(error, file_context="Runtime Execution Traceback")
        
        # ओनर को सीधे अलर्ट भेजने के लिए टेक्स्ट
        alert_text = (
            "🚨 **🚨 SYSTEM ERROR DETECTED 🚨**\n\n"
            f"❌ **Error:** `{str(error)}`\n\n"
            "🤖 **Gemini Engine Status:** मैंने इस एरर का फिक्स कोड बैकएंड में तैयार कर लिया है। क्या आप इसे लाइव देखना चाहते हैं?"
        )
        
        # इनलाइन बटनों का सेटअप
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Apply Fix", callback_data="apply_ai_fix"),
                InlineKeyboardButton("❌ No, Ignore", callback_data="ignore_ai_fix")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # बोट ओनर को बिना किसी को डिस्टर्ब किए डायरेक्ट मैसेज भेजेगा
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=alert_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # फिक्स कोड को बोट_डेटा में सेफ़ रख रहे हैं ताकि बटन दबाने पर फैच हो सके
        context.bot_data["last_ai_fix"] = fixed_code
    except Exception as auditor_fail:
        print(f"[CRITICAL AUDITOR EXCEPTION]: {auditor_fail}", file=sys.stderr)

# =========================
# AI FIX CALLBACK HANDLER (बटन एक्शन इंजन)
# =========================
async def ai_fix_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("🚫 Access Denied: Only the Owner can deploy AI fixes.")
        return
        
    if query.data == "apply_ai_fix":
        fixed_code = context.bot_data.get("last_ai_fix")
        if not fixed_code or "Failed" in fixed_code:
            await query.edit_message_text("⚠️ कोई वैध फिक्स कोड नहीं मिला या जेमिनी फ़ेल हो गया था।")
            return
            
        try:
            await query.edit_message_text("⚙️ **Analyzing Fix Details...**")
            
            # सेफ्टी रूल्स के कारण कोड सीधा फाइल में लिखने के बजाय प्रीव्यू मोड में ओनर को ट्रांसफर होगा
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"📂 **Generated Code by AI:**\n\n```python\n{fixed_code}\n```\n\n💡 आप इसे कॉकटेल स्लैश `/code` कमांड के ज़रिए सीधे संबंधित फाइल में रिप्लेस कर सकते हैं!",
                parse_mode="Markdown"
            )
        except Exception as e:
            await context.bot.send_message(chat_id=OWNER_ID, text=f"❌ कोड डिलीवर करने में एरर आया: {str(e)}")
            
    elif query.data == "ignore_ai_fix":
        await query.edit_message_text("🗑️ एआई फिक्स को इग्नोर कर दिया गया है।")

# =========================
# SAFE MESSAGE HANDLER
# =========================
async def safe_handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if context.user_data.get("handled"):
        context.user_data["handled"] = False
        return

    try:
        await handle_message(
            update,
            context
        )
    except Exception as e:
        print(f"[MESSAGE ERROR]: {e}")
        await fallback_reply(update)

# =========================
# SEARCH COMMAND
# =========================
async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "Bhai kya search karna hai?"
        )
        return

    query = " ".join(context.args)
    results = search_web(query)

    if not results:
        await update.message.reply_text(
            "ye kya bak rhe ho muje kuch nhi mila web pe."
        )
        return

    formatted = []
    for r in results:
        formatted.append(
            f"🔹 {r['title']}\n{r['url']}"
        )

    response = "\n\n".join(formatted)
    await update.message.reply_text(
        response
    )

# =========================
# BACKGROUND TASKS
# =========================
async def post_init(app):
    asyncio.create_task(
        reminder_checker(app)
    )
    asyncio.create_task(
        message_scheduler(app)
    )

# =========================
# MAIN BOT ENGINE
# =========================
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # REPLACED: अपग्रेड किया हुआ एरर हैंडलर यहाँ रजिस्टर कर दिया गया है
    app.add_error_handler(
        error_handler
    )

    # ---------------------------------------------------------
    # 1. ALL COMMAND HANDLERS REGISTERED FIRST (No Group - Default Group 0)
    # ---------------------------------------------------------
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("mood", set_mood))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("showlast", show_last_image))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("sendlater", sendlater))
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler(["send", "msg"], send_command))
    
    app.add_handler(CommandHandler("code", handle_code_management)) 
    app.add_handler(CallbackQueryHandler(handle_replacement_callback, pattern="^(replace_yes|replace_no)$"))

    # न्यूली ऐडेड एआई फिक्स बटन कॉलबैक हैंडलर (पैटर्न लॉक के साथ सुरक्षित)
    app.add_handler(CallbackQueryHandler(ai_fix_callback_handler, pattern="^(apply_ai_fix|ignore_ai_fix)$"))

    # ---------------------------------------------------------
    # 2. IMAGE HANDLER (Default Group 0)
    # ---------------------------------------------------------
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_image
        )
    )

    # ---------------------------------------------------------
    # 3. MESSAGE HANDLERS (Sequential Group Allocation)
    # ---------------------------------------------------------
    
    # OWNER CONFIRMATION: Priority Group 1
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_owner_confirmation
        ),
        group=1
    )

    # All Core AI Handlers preserved strictly with their original multi-agent routing numbers
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            natural_scheduler
        ),
        group=2
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            contact_ai
        ),
        group=3
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_ai_control
        ),
        group=4
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            safe_handle_message
        ),
        group=5
    )

    print("✅ RJ BOT ASSISTANT is running smoothly with multi-agent routing...")

    app.run_polling(
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()