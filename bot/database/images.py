import re
import sqlite3
import time

conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()

# =========================
# IMAGES TABLE
# =========================

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS images (

        file_id TEXT PRIMARY KEY,

        description TEXT,

        added_time REAL
    )
    """
)

conn.commit()


# =========================
# SAVE IMAGE DESCRIPTION
# =========================

def save_image(
    file_id,
    description=""
):
    cursor.execute(
        """
        INSERT OR REPLACE INTO images (

            file_id,
            description,
            added_time

        )
        VALUES (?, ?, ?)
        """,
        (
            file_id,
            description,
            time.time()
        )
    )
    conn.commit()


# =========================
# SEARCH IMAGE BY KEYWORD
# =========================

def search_image_by_keyword(text):
    if not text:
        return None

    normalized = text.lower().strip()
    if not normalized:
        return None

    # first try an exact phrase search against the full text
    phrase = f"%{normalized}%"
    cursor.execute(
        """
        SELECT file_id
        FROM images
        WHERE LOWER(description) LIKE ?
        ORDER BY LENGTH(description) ASC
        LIMIT 1
        """,
        (phrase,)
    )

    row = cursor.fetchone()
    if row:
        return row[0]

    # fallback to keyword matching if phrase search fails
    keywords = [
        word
        for word in re.findall(r"\w+", normalized)
        if len(word) > 2
    ]

    if not keywords:
        return None

    clauses = " OR ".join(
        ["LOWER(description) LIKE ?" for _ in keywords]
    )
    params = [f"%{keyword}%" for keyword in keywords]

    cursor.execute(
        f"""
        SELECT file_id
        FROM images
        WHERE {clauses}
        ORDER BY LENGTH(description) ASC
        LIMIT 1
        """,
        params,
    )

    row = cursor.fetchone()
    return row[0] if row else None
