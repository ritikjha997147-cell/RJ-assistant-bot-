import sqlite3
import time


conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()


# CREATE TABLE

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (

        telegram_id INTEGER PRIMARY KEY,

        username TEXT,

        first_name TEXT,

        last_name TEXT,

        message_count INTEGER DEFAULT 0,

        last_active REAL
    )
    """
)

conn.commit()


# CREATE USER

def create_user(

    telegram_id,
    username,
    first_name,
    last_name

):

    cursor.execute(

        """
        INSERT OR IGNORE INTO users (

            telegram_id,
            username,
            first_name,
            last_name,
            last_active

        )

        VALUES (?, ?, ?, ?, ?)
        """,

        (
            telegram_id,
            username,
            first_name,
            last_name,
            time.time()
        )
    )

    conn.commit()


# UPDATE USER ACTIVITY

def update_user_activity(
    telegram_id
):

    cursor.execute(

        """
        UPDATE users

        SET

            message_count =
            message_count + 1,

            last_active = ?

        WHERE telegram_id = ?
        """,

        (
            time.time(),
            telegram_id
        )
    )

    conn.commit()


# GET USER

def get_user(
    telegram_id
):

    cursor.execute(

        """
        SELECT * FROM users

        WHERE telegram_id = ?
        """,

        (telegram_id,)
    )

    return cursor.fetchone()
