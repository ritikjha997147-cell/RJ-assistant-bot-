import sqlite3


conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()


cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS custom_commands (
        user_id INTEGER,
        command TEXT,
        response TEXT
    )
"""
)

conn.commit()


def add_command(
    user_id,
    command,
    response
):

    cursor.execute(
        """
        INSERT INTO custom_commands
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            command,
            response
        )
    )

    conn.commit()


def get_command(
    user_id,
    command
):

    cursor.execute(
        """
        SELECT response
        FROM custom_commands
        WHERE user_id = ?
        AND command = ?
        """,
        (
            user_id,
            command
        )
    )

    result = cursor.fetchone()

    if result:

        return result[0]

    return None
