import sqlite3, time

conn = sqlite3.connect("bot/database/bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, message TEXT, remind_at REAL)""")
conn.commit()

def add_reminder(chat_id, message, remind_at):
    cursor.execute("INSERT INTO reminders (chat_id, message, remind_at) VALUES (?, ?, ?)", (chat_id, message, remind_at))
    conn.commit()
    return cursor.lastrowid

def get_due_reminders(current_time):
    cursor.execute("SELECT id, chat_id, message FROM reminders WHERE remind_at <= ?", (current_time,))
    return cursor.fetchall()

def get_all_pending_reminders():
    cursor.execute("SELECT id, chat_id, message, remind_at FROM reminders WHERE remind_at > ?", (time.time(),))
    return cursor.fetchall()

def get_all_reminders_for_user(chat_id):
    cursor.execute("SELECT id, chat_id, message, remind_at FROM reminders WHERE chat_id = ? ORDER BY remind_at ASC", (chat_id,))
    return cursor.fetchall()

def delete_reminder(reminder_id):
    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
