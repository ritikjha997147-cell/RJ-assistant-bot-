import sqlite3


conn = sqlite3.connect(
    "bot/database/bot.db",
    check_same_thread=False
)

cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    message TEXT
)
""")

conn.commit()


def save_message(
    user_id,
    role,
    message
):

    cursor.execute(
        """
        INSERT INTO chat_memory
        (
            user_id,
            role,
            message
        )
        VALUES (?, ?, ?)
        """,
        (
            str(user_id),
            role,
            message
        )
    )

    conn.commit()


def get_last_messages(
    user_id,
    limit=10
):

    cursor.execute(
        """
        SELECT role, message
        FROM chat_memory
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            str(user_id),
            limit
        )
    )

    rows = cursor.fetchall()

    rows.reverse()

    return rows
