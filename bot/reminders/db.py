import sqlite3


conn = sqlite3.connect(
    "bot/database/reminders.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    message TEXT,
    remind_time REAL
)
""")

conn.commit()
