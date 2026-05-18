import sqlite3
import time


conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()


# =========================
# CONTACTS TABLE
# =========================

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS contacts (

        telegram_id INTEGER PRIMARY KEY,

        custom_name TEXT,

        tag TEXT,

        notes TEXT,

        added_time REAL
    )
    """
)

conn.commit()


# =========================
# ADD CONTACT
# =========================

def add_contact(

    telegram_id,
    custom_name,
    tag="",
    notes=""

):

    cursor.execute(

        """
        INSERT OR REPLACE INTO contacts (

            telegram_id,
            custom_name,
            tag,
            notes,
            added_time

        )

        VALUES (?, ?, ?, ?, ?)
        """,

        (
            telegram_id,
            custom_name,
            tag,
            notes,
            time.time()
        )
    )

    conn.commit()


# =========================
# GET CONTACT
# =========================

def get_contact(
    custom_name
):

    cursor.execute(

        """
        SELECT telegram_id
        FROM contacts

        WHERE LOWER(custom_name)=LOWER(?)
        """,

        (custom_name,)
    )

    return cursor.fetchone()


# =========================
# GET ALL CONTACTS
# =========================

def get_all_contacts():

    cursor.execute(
        """
        SELECT *
        FROM contacts
        """
    )

    return cursor.fetchall()
