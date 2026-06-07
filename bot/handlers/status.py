import re, time
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

afk_state = {"active": False, "message": "", "until": None, "set_at": None, "duration_text": ""}

MENTION_TRIGGERS = ["rj", "ritik", "kidhar hai", "kahan hai", "kaha hai", "kab aayega", "kab free", "busy hai", "available hai", "kab milega", "baat karni hai"]

DURATION_PATTERNS = [(r'(\d+\.?\d*)\s*(?:ghante|ghanta|hour|hours|hr|hrs)', 3600), (r'(\d+\.?\d*)\s*(?:minute|minutes|min|mins)', 60), (r'(\d+\.?\d*)\s*(?:din|day|days)', 86400)]

def parse_duration(text):
    text_lower = text.lower()
    total_seconds = 0
    found = False
    for pattern, multiplier in DURATION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            total_seconds += int(float(match.group(1)) * multiplier)
            found = True
    return total_seconds if found else None

def parse_status_message(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["busy", "busy hun"]):
        return "busy hai"
    elif any(w in text_lower for w in ["bahar", "bahar hun"]):
        return "bahar gaya hai"
    elif any(w in text_lower for w in ["so raha", "neend"]):
        return "so raha hai"
    elif any(w in text_lower for w in ["khana", "lunch", "dinner"]):
        return "khana kha raha hai"
    elif any(w in text_lower for w in ["meeting", "call pe"]):
        return "meeting mein hai"
    else:
        return "abhi available nahi hai"

def format_duration(seconds):
    if seconds >= 86400:
        return f"{seconds//86400} din"
    elif seconds >= 3600:
        h = seconds/3600
        return f"{h:.1f} ghante" if h != int(h) else f"{int(h)} ghante"
    else:
        return f"{seconds//60} minute"

async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.config import OWNER_ID
    user_id = update.effective_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("Sirf owner status set kar sakta hai!")
        return
    if not context.args:
        await update.message.reply_text("/status set Main agale 2 ghante busy hun\n/status set 30 min meeting hai\n/status off\n/status check")
        return
    action = context.args[0].lower()
    if action == "off":
        afk_state["active"] = False
        afk_state["until"] = None
        await update.message.reply_text("Status clear! Ab available hoon.")
        return
    if action == "check":
        if afk_state["active"] and afk_state["until"]:
            remaining = int(afk_state["until"] - time.time())
            if remaining > 0:
                await update.message.reply_text(f"Status: {afk_state['message']}\nBacha time: {format_duration(remaining)}\nFree at: {datetime.fromtimestamp(afk_state['until']).strftime('%I:%M %p')}")
            else:
                afk_state["active"] = False
                await update.message.reply_text("Status expire ho gaya - free hoon!")
        else:
            await update.message.reply_text("Koi active status nahi - available hoon!")
        return
    if action == "set":
        full_text = " ".join(context.args[1:])
        duration_secs = parse_duration(full_text)
        if not duration_secs:
            await update.message.reply_text("Duration samajh nahi aaya!\nTry: /status set Main agale 2 ghante busy hun")
            return
        afk_state["active"] = True
        afk_state["message"] = parse_status_message(full_text)
        afk_state["until"] = time.time() + duration_secs
        afk_state["set_at"] = time.time()
        afk_state["duration_text"] = format_duration(duration_secs)
        free_at = datetime.fromtimestamp(afk_state["until"]).strftime("%I:%M %p")
        await update.message.reply_text(f"Status set!\nStatus: {afk_state['message']}\nDuration: {afk_state['duration_text']}\nFree at: {free_at}")

def check_afk_mention(text):
    text_lower = text.lower()
    if not any(t in text_lower for t in MENTION_TRIGGERS):
        return False, None
    if not afk_state["active"]:
        return False, None
    if afk_state["until"] and time.time() > afk_state["until"]:
        afk_state["active"] = False
        return False, None
    remaining = int(afk_state["until"] - time.time())
    reply = f"Ritik abhi {afk_state['message']}!\n\nUsne bataya tha ki woh {afk_state['duration_text']} ke liye available nahi hoga. Abhi lagbhag {format_duration(remaining)} baaki hai.\n\nThodi der baad try karo ya message chhod do!"
    return True, reply
