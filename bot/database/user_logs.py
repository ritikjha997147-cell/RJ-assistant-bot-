import sqlite3, time
from datetime import datetime

conn = sqlite3.connect("bot/database/bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS user_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, message_text TEXT, timestamp REAL)""")
conn.commit()

def log_message(user_id, username, first_name, message_text):
    cursor.execute("INSERT INTO user_logs (user_id, username, first_name, message_text, timestamp) VALUES (?, ?, ?, ?, ?)", (user_id, username or "unknown", first_name or "unknown", message_text, time.time()))
    conn.commit()

def get_logs_today():
    today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    cursor.execute("SELECT user_id, username, first_name, message_text, timestamp FROM user_logs WHERE timestamp >= ? ORDER BY timestamp ASC", (today_start,))
    return cursor.fetchall()

def get_logs_by_user(username):
    today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    cursor.execute("SELECT user_id, username, first_name, message_text, timestamp FROM user_logs WHERE (username LIKE ? OR first_name LIKE ?) AND timestamp >= ? ORDER BY timestamp ASC", (f"%{username}%", f"%{username}%", today_start))
    return cursor.fetchall()

def get_logs_summary_text(logs):
    if not logs:
        return None
    lines = []
    for user_id, username, first_name, msg, ts in logs:
        name = first_name or username or str(user_id)
        t = datetime.fromtimestamp(ts).strftime("%I:%M %p")
        lines.append(f"[{t}] {name}: {msg}")
    return "\n".join(lines)
