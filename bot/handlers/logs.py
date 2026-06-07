import re
from telegram import Update
from telegram.ext import ContextTypes
from bot.database.user_logs import get_logs_today, get_logs_by_user, get_logs_summary_text

LOG_QUERY_TRIGGERS = ["aaj kis", "kisne chalaya", "kya poocha", "log dekho", "report do", "summary do", "aaj kya", "tell me what", "who used", "activity", "log batao", "kya pucha"]

def is_log_query(text):
    return any(t in text.lower() for t in LOG_QUERY_TRIGGERS)

def extract_username_from_query(text):
    for pattern in [r'(?:what did|tell me what)\s+(\w+)\s+(?:asked|said)', r'(\w+)\s+(?:ne kya|ka log|ki activity)']:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1)
    return None

async def handle_log_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.config import OWNER_ID, GEMINI_API_KEYS, GROQ_API_KEY
    user_id = update.effective_user.id
    if OWNER_ID and user_id != OWNER_ID:
        return False
    if not is_log_query(update.message.text):
        return False
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    specific_user = extract_username_from_query(update.message.text)
    if specific_user:
        logs = get_logs_by_user(specific_user)
        scope = f"{specific_user} ke messages"
    else:
        logs = get_logs_today()
        scope = "aaj ke saare messages"
    if not logs:
        await update.message.reply_text(f"{scope} mein koi activity nahi mili aaj!")
        return True
    log_text = get_logs_summary_text(logs)
    unique_users = len(set(row[0] for row in logs))
    prompt = f"You are RJ's personal assistant. Analyze these chat logs and give a friendly Hinglish summary (3-5 sentences). Mention who messaged, what topics came up, any patterns.\n\nLogs:\n{log_text}"
    summary = None
    if GEMINI_API_KEYS:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEYS[0])
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            summary = response.text
        except Exception as e:
            print(f"[LOGS ERROR]: {e}")
    if not summary and GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}], max_tokens=300)
            summary = completion.choices[0].message.content
        except Exception as e:
            print(f"[LOGS GROQ ERROR]: {e}")
    if not summary:
        summary = f"Aaj {unique_users} logo ne bot use kiya. {len(logs)} total messages aaye."
    await update.message.reply_text(f"Activity Report\n\nUnique users: {unique_users}\nTotal messages: {len(logs)}\n\n{summary}")
    return True
