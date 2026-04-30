import os
import re
iort mpjson
import sqlite3
import datetime as dt
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])
TZ = ZoneInfo("Asia/Kolkata")

client = OpenAI(
    api_key=os.environ["AI_INTEGRATIONS_OPENAI_API_KEY"],
    base_url=os.environ["AI_INTEGRATIONS_OPENAI_BASE_URL"],
)

DB_PATH = "rj_assistant.db"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER NOT NULL,
                item TEXT NOT NULL,
                user_id INTEGER,
                user_name TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                done INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_name TEXT,
                caption TEXT,
                user_id INTEGER,
                user_name TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                text TEXT,
                category TEXT,
                urgency TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pending_replies (
                msg_id INTEGER PRIMARY KEY,
                target_user_id INTEGER NOT NULL
            );
            """
        )


init_db()


SYSTEM_PROMPT = """
Tum RJ ke personal assistant ho. Naam: RJ Assistant.

Tumhari job: Jo bhi user message bheje, usko samjho aur 4 cheezein return karo (JSON format me):
1. category: "info" | "question" | "request" | "casual" | "spam"
2. reply: User ko jo reply bhejna hai (jis language me user ne likha — Hinglish/Hindi/English auto-detect karke usi me, friendly, 1-2 line max)
3. summary: RJ ke liye chhota summary (1 line, English/Hinglish)
4. urgency: "low" | "medium" | "high"

CATEGORY RULES:
- "info" → User koi baat bata raha hai → Reply: friendly acknowledge → Urgency: low/medium
- "question" → Sawaal → Reply: politely batao RJ se confirm karke batayenge → Urgency: low/medium
- "request" → Kuch maang/kaam → Reply: confirm karke batane wala reply → Urgency: medium/high
- "casual" → Greeting/chit-chat → Reply: friendly chhota reply → Urgency: low
- "spam" → Bakwas → Reply: politely sahi msg maango → Urgency: low

GENERAL:
- LANGUAGE: User ne jis language me likha (Hindi/English/Hinglish) usi me reply karo
- Friendly, short, 1-2 line max. Lecture mat dena.
- Jhooth mat bolo. Pata na ho to "RJ se pooch ke batata hun".
- Sirf valid JSON return karo.

JSON FORMAT EXACTLY:
{"category": "...", "reply": "...", "summary": "...", "urgency": "..."}
"""


def urgency_emoji(u): return {"high": "🚨", "medium": "⚡", "low": "💬"}.get(u, "💬")
def category_emoji(c):
    return {"info": "📢", "question": "❓", "request": "🙏",
            "casual": "👋", "spam": "🚫"}.get(c, "📩")


def now_str():
    return dt.datetime.now(TZ).isoformat()


def parse_when(s: str):
    """Parse '5m', '2h', '1d', 'HH:MM' (today/tomorrow). Returns datetime or None."""
    s = s.strip().lower()
    now = dt.datetime.now(TZ)

    m = re.fullmatch(r"(\d+)\s*(m|min|mins|minute|minutes)", s)
    if m:
        return now + dt.timedelta(minutes=int(m.group(1)))
    m = re.fullmatch(r"(\d+)\s*(h|hr|hrs|hour|hours)", s)
    if m:
        return now + dt.timedelta(hours=int(m.group(1)))
    m = re.fullmatch(r"(\d+)\s*(d|day|days)", s)
    if m:
        return now + dt.timedelta(days=int(m.group(1)))
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            target += dt.timedelta(days=1)
        return target
    return None


# ---------------- COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id == OWNER_ID:
        await update.message.reply_text(
            "RJ Assistant ON ✅ Smart mode ✨\n\n"
            "Type /help to see all commands."
        )
    else:
        await update.message.reply_text(
            f"Hi {user.first_name}! Main RJ ka Assistant hun 👋\nKya kaam hai?"
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_owner = update.message.from_user.id == OWNER_ID
    if is_owner:
        msg = (
            "🤖 *RJ Assistant — Owner Commands*\n\n"
            "💰 *Kharcha*\n"
            "/kharcha 500 chai — add\n"
            "/total — total kharcha\n"
            "/list — last 10 kharche\n"
            "/clear — sab clear\n\n"
            "📝 *Notes*\n"
            "/note kal meeting hai — save note\n"
            "/notes — saare notes dekho\n"
            "/delnote 3 — note id 3 delete\n\n"
            "⏰ *Reminders*\n"
            "/remind 5m call mom\n"
            "/remind 2h meeting\n"
            "/remind 17:30 dinner\n"
            "/reminders — pending list\n"
            "/delremind 2 — id 2 cancel\n\n"
            "📁 *Files* — Just send photo/PDF/doc, auto save\n"
            "/files — saved files list\n\n"
            "📊 *Stats & Summary*\n"
            "/stats — week stats\n"
            "/summary — aaj ka summary (auto raat 10 baje bhi)\n\n"
            "💬 Reply to forwarded msg → user ko jaayega"
        )
    else:
        msg = (
            "🤖 RJ Assistant\n\n"
            "Bas message likho, main RJ tak pahuncha dunga.\n"
            "Kharcha share karna hai? `kharcha 500 chai` likho."
        )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ---------- KHARCHA ----------

async def kharcha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/kharcha", "", 1).strip()
    user = update.message.from_user
    try:
        parts = text.split(" ", 1)
        amount = int(parts[0])
        item = parts[1] if len(parts) > 1 else "Misc"
        with db() as c:
            c.execute(
                "INSERT INTO expenses (amount, item, user_id, user_name, created_at) VALUES (?,?,?,?,?)",
                (amount, item, user.id, user.first_name, now_str()),
            )
        await update.message.reply_text(f"Note kar liya ✅\n₹{amount} - {item}")
        if user.id != OWNER_ID:
            await context.bot.send_message(
                OWNER_ID,
                f"💸 Kharcha: ₹{amount} - {item}\nFrom: {user.first_name}",
            )
    except Exception:
        await update.message.reply_text("Format: /kharcha 500 chai")


async def total_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as c:
        row = c.execute("SELECT COALESCE(SUM(amount),0) AS t FROM expenses").fetchone()
    await update.message.reply_text(f"💰 Total Kharcha: ₹{row['t']}")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as c:
        rows = c.execute(
            "SELECT amount, item, created_at FROM expenses ORDER BY id DESC LIMIT 10"
        ).fetchall()
    if not rows:
        await update.message.reply_text("Koi kharcha nahi hai")
        return
    lines = [f"₹{r['amount']} - {r['item']}  ({r['created_at'][:10]})" for r in rows]
    await update.message.reply_text("📝 Last 10:\n\n" + "\n".join(lines))


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    with db() as c:
        c.execute("DELETE FROM expenses")
    await update.message.reply_text("Sab kharche clear ✅")


# ---------- NOTES ----------

async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("Sirf RJ ke liye hai bhai")
        return
    text = update.message.text.replace("/note", "", 1).strip()
    if not text:
        await update.message.reply_text("Format: /note kal meeting hai")
        return
    with db() as c:
        c.execute(
            "INSERT INTO notes (text, created_at) VALUES (?,?)", (text, now_str())
        )
    await update.message.reply_text(f"📝 Note save ✅\n_{text}_", parse_mode="Markdown")


async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    with db() as c:
        rows = c.execute(
            "SELECT id, text, created_at FROM notes ORDER BY id DESC LIMIT 20"
        ).fetchall()
    if not rows:
        await update.message.reply_text("Koi note nahi hai")
        return
    lines = [f"#{r['id']} — {r['text']}  ({r['created_at'][:10]})" for r in rows]
    await update.message.reply_text("📝 *Your Notes:*\n\n" + "\n".join(lines), parse_mode="Markdown")


async def delnote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    parts = update.message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await update.message.reply_text("Format: /delnote 3")
        return
    nid = int(parts[1])
    with db() as c:
        cur = c.execute("DELETE FROM notes WHERE id=?", (nid,))
    msg = f"Note #{nid} delete ✅" if cur.rowcount else "Aisa koi note nahi mila"
    await update.message.reply_text(msg)


# ---------- REMINDERS ----------

async def reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    rid = job.data["id"]
    text = job.data["text"]
    uid = job.data["user_id"]
    await context.bot.send_message(uid, f"⏰ *Reminder:* {text}", parse_mode="Markdown")
    with db() as c:
        c.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))


async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("Sirf RJ ke liye hai bhai")
        return
    raw = update.message.text.replace("/remind", "", 1).strip()
    parts = raw.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Format:\n/remind 5m call mom\n/remind 2h meeting\n/remind 17:30 dinner"
        )
        return
    when_str, text = parts[0], parts[1]
    when = parse_when(when_str)
    if not when:
        await update.message.reply_text(
            "Time samjha nahi 😅 Try: 5m, 30m, 2h, 1d, ya 17:30"
        )
        return
    with db() as c:
        cur = c.execute(
            "INSERT INTO reminders (text, remind_at, user_id) VALUES (?,?,?)",
            (text, when.isoformat(), update.message.from_user.id),
        )
        rid = cur.lastrowid
    delay = (when - dt.datetime.now(TZ)).total_seconds()
    context.job_queue.run_once(
        reminder_callback,
        when=delay,
        data={"id": rid, "text": text, "user_id": update.message.from_user.id},
        name=f"rem_{rid}",
    )
    await update.message.reply_text(
        f"⏰ Reminder set ✅\n_{text}_\nKab: {when.strftime('%d %b %I:%M %p')}",
        parse_mode="Markdown",
    )


async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    with db() as c:
        rows = c.execute(
            "SELECT id, text, remind_at FROM reminders WHERE done=0 ORDER BY remind_at"
        ).fetchall()
    if not rows:
        await update.message.reply_text("Koi pending reminder nahi hai")
        return
    lines = []
    for r in rows:
        when = dt.datetime.fromisoformat(r["remind_at"])
        lines.append(f"#{r['id']} — {r['text']}  ⏰ {when.strftime('%d %b %I:%M %p')}")
    await update.message.reply_text("⏰ *Pending Reminders:*\n\n" + "\n".join(lines), parse_mode="Markdown")


async def delremind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    parts = update.message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await update.message.reply_text("Format: /delremind 2")
        return
    rid = int(parts[1])
    for j in context.job_queue.get_jobs_by_name(f"rem_{rid}"):
        j.schedule_removal()
    with db() as c:
        cur = c.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))
    msg = f"Reminder #{rid} cancel ✅" if cur.rowcount else "Aisa koi reminder nahi mila"
    await update.message.reply_text(msg)


# ---------- FILES ----------

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user
    file_id, ftype, fname = None, None, None
    if msg.photo:
        file_id, ftype, fname = msg.photo[-1].file_id, "photo", "photo.jpg"
    elif msg.document:
        file_id = msg.document.file_id
        ftype = "document"
        fname = msg.document.file_name or "file"
    elif msg.video:
        file_id, ftype, fname = msg.video.file_id, "video", "video.mp4"
    elif msg.voice:
        file_id, ftype, fname = msg.voice.file_id, "voice", "voice.ogg"
    elif msg.audio:
        file_id = msg.audio.file_id
        ftype = "audio"
        fname = msg.audio.file_name or "audio"
    if not file_id:
        return
    caption = msg.caption or ""
    with db() as c:
        cur = c.execute(
            "INSERT INTO files (file_id, file_type, file_name, caption, user_id, user_name, created_at) VALUES (?,?,?,?,?,?,?)",
            (file_id, ftype, fname, caption, user.id, user.first_name, now_str()),
        )
        fid = cur.lastrowid
    await msg.reply_text(f"📁 Save ho gaya ✅ (#{fid} - {ftype})")
    if user.id != OWNER_ID:
        await context.bot.send_message(
            OWNER_ID,
            f"📁 *New File from {user.first_name}*\nType: {ftype}\nName: {fname}\nCaption: {caption or '(none)'}",
            parse_mode="Markdown",
        )
        await context.bot.forward_message(OWNER_ID, msg.chat.id, msg.message_id)


async def files_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    with db() as c:
        rows = c.execute(
            "SELECT id, file_type, file_name, caption, user_name, created_at FROM files ORDER BY id DESC LIMIT 15"
        ).fetchall()
    if not rows:
        await update.message.reply_text("Koi file save nahi hai")
        return
    lines = [
        f"#{r['id']} {r['file_type']}: {r['file_name'] or ''} — {r['user_name']} ({r['created_at'][:10]})"
        for r in rows
    ]
    await update.message.reply_text("📁 *Saved Files:*\n\n" + "\n".join(lines), parse_mode="Markdown")


# ---------- STATS & SUMMARY ----------

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    week_ago = (dt.datetime.now(TZ) - dt.timedelta(days=7)).isoformat()
    with db() as c:
        msgs = c.execute(
            "SELECT category, COUNT(*) as n FROM messages_log WHERE created_at >= ? GROUP BY category",
            (week_ago,),
        ).fetchall()
        total_msgs = c.execute(
            "SELECT COUNT(*) as n FROM messages_log WHERE created_at >= ?", (week_ago,)
        ).fetchone()["n"]
        total_kharcha = c.execute(
            "SELECT COALESCE(SUM(amount),0) as s FROM expenses WHERE created_at >= ?",
            (week_ago,),
        ).fetchone()["s"]
        n_files = c.execute(
            "SELECT COUNT(*) as n FROM files WHERE created_at >= ?", (week_ago,)
        ).fetchone()["n"]
        n_notes = c.execute(
            "SELECT COUNT(*) as n FROM notes WHERE created_at >= ?", (week_ago,)
        ).fetchone()["n"]

    cats = "\n".join([f"  {category_emoji(m['category'])} {m['category']}: {m['n']}" for m in msgs]) or "  (none)"
    text = (
        "📊 *Last 7 Days Stats*\n\n"
        f"💬 Total Messages: {total_msgs}\n{cats}\n\n"
        f"💰 Kharcha: ₹{total_kharcha}\n"
        f"📁 Files: {n_files}\n"
        f"📝 Notes: {n_notes}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def build_daily_summary():
    today = dt.datetime.now(TZ).date().isoformat()
    with db() as c:
        msgs = c.execute(
            "SELECT user_name, text, category, urgency FROM messages_log WHERE created_at LIKE ? ORDER BY id DESC",
            (f"{today}%",),
        ).fetchall()
        kharcha = c.execute(
            "SELECT COALESCE(SUM(amount),0) as s FROM expenses WHERE created_at LIKE ?",
            (f"{today}%",),
        ).fetchone()["s"]
        pending_rems = c.execute(
            "SELECT text, remind_at FROM reminders WHERE done=0 AND remind_at >= ? ORDER BY remind_at LIMIT 5",
            (dt.datetime.now(TZ).isoformat(),),
        ).fetchall()

    lines = [f"📅 *Daily Summary — {today}*", ""]
    lines.append(f"💬 Total Messages: {len(msgs)}")
    high = [m for m in msgs if m["urgency"] == "high"]
    if high:
        lines.append(f"🚨 *Urgent ({len(high)}):*")
        for m in high[:5]:
            lines.append(f"  • {m['user_name']}: {m['text'][:60]}")
    lines.append(f"\n💰 Aaj ka Kharcha: ₹{kharcha}")
    if pending_rems:
        lines.append(f"\n⏰ *Upcoming Reminders:*")
        for r in pending_rems:
            when = dt.datetime.fromisoformat(r["remind_at"])
            lines.append(f"  • {r['text']} — {when.strftime('%d %b %I:%M %p')}")
    return "\n".join(lines)


async def summary_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    text = await build_daily_summary()
    await update.message.reply_text(text, parse_mode="Markdown")


async def daily_summary_job(context: ContextTypes.DEFAULT_TYPE):
    text = await build_daily_summary()
    await context.bot.send_message(OWNER_ID, text, parse_mode="Markdown")


# ---------- MAIN MESSAGE HANDLER ----------

async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    user = msg.from_user
    text = msg.text
    chat = msg.chat

    # In groups, ignore unless mentioned/replied to bot
    if chat.type in ("group", "supergroup"):
        bot_username = (await context.bot.get_me()).username
        mentioned = f"@{bot_username}".lower() in text.lower()
        replied_to_bot = (
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.id == context.bot.id
        )
        if not (mentioned or replied_to_bot):
            return
        text = re.sub(rf"@{bot_username}", "", text, flags=re.IGNORECASE).strip()

    # Owner reply to forwarded msg
    if (
        user.id == OWNER_ID
        and msg.reply_to_message
    ):
        with db() as c:
            row = c.execute(
                "SELECT target_user_id FROM pending_replies WHERE msg_id=?",
                (msg.reply_to_message.message_id,),
            ).fetchone()
        if row:
            await context.bot.send_message(
                row["target_user_id"], f"RJ ka Reply: {text}"
            )
            await msg.reply_text("User ko bhej diya ✅")
            with db() as c:
                c.execute(
                    "DELETE FROM pending_replies WHERE msg_id=?",
                    (msg.reply_to_message.message_id,),
                )
            return

    # GPT smart reply
    try:
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User '{user.first_name}' ne ye bheja: \"{text}\""},
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
        )
        data = json.loads(response.choices[0].message.content)
        reply = data.get("reply", "Theek hai bhai, RJ ko bata dunga.")
        category = data.get("category", "casual")
        summary = data.get("summary", text)
        urgency = data.get("urgency", "low")
    except Exception as e:
        print(f"GPT error: {e}")
        reply = "Message mil gaya bhai ✅ RJ ko bata dunga."
        category, summary, urgency = "info", text, "low"

    # Log message
    with db() as c:
        c.execute(
            "INSERT INTO messages_log (user_id, user_name, text, category, urgency, created_at) VALUES (?,?,?,?,?,?)",
            (user.id, user.first_name, text, category, urgency, now_str()),
        )

    await msg.reply_text(reply)

    if user.id != OWNER_ID:
        forward = (
            f"{urgency_emoji(urgency)} {category_emoji(category)} "
            f"*{category.upper()}* | Urgency: *{urgency.upper()}*\n\n"
            f"👤 From: {user.first_name} (@{user.username or 'N/A'})\n"
            f"🆔 ID: {user.id}\n\n"
            f"💬 Original: {text}\n\n"
            f"📝 Summary: {summary}\n\n"
            f"🤖 Maine reply diya: {reply}\n\n"
            f"👆 Reply karo to user tak pahuncha dunga"
        )
        try:
            sent = await context.bot.send_message(OWNER_ID, forward, parse_mode="Markdown")
        except Exception:
            sent = await context.bot.send_message(OWNER_ID, forward)
        with db() as c:
            c.execute(
                "INSERT OR REPLACE INTO pending_replies (msg_id, target_user_id) VALUES (?,?)",
                (sent.message_id, user.id),
            )


# ---------- STARTUP: reload pending reminders ----------

async def reload_reminders(app):
    with db() as c:
        rows = c.execute(
            "SELECT id, text, remind_at, user_id FROM reminders WHERE done=0"
        ).fetchall()
    now = dt.datetime.now(TZ)
    for r in rows:
        when = dt.datetime.fromisoformat(r["remind_at"])
        delay = (when - now).total_seconds()
        if delay <= 0:
            await app.bot.send_message(
                r["user_id"], f"⏰ *Reminder (missed):* {r['text']}", parse_mode="Markdown"
            )
            with db() as c:
                c.execute("UPDATE reminders SET done=1 WHERE id=?", (r["id"],))
        else:
            app.job_queue.run_once(
                reminder_callback,
                when=delay,
                data={"id": r["id"], "text": r["text"], "user_id": r["user_id"]},
                name=f"rem_{r['id']}",
            )

    # Schedule daily summary at 10 PM IST
    app.job_queue.run_daily(
        daily_summary_job,
        time=dt.time(hour=22, minute=0, tzinfo=TZ),
        name="daily_summary",
    )


print("Bot start ho raha hai...")
app = ApplicationBuilder().token(TOKEN).post_init(reload_reminders).build()

# Commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("kharcha", kharcha_cmd))
app.add_handler(CommandHandler("total", total_cmd))
app.add_handler(CommandHandler("list", list_cmd))
app.add_handler(CommandHandler("clear", clear_cmd))
app.add_handler(CommandHandler("note", note_cmd))
app.add_handler(CommandHandler("notes", notes_cmd))
app.add_handler(CommandHandler("delnote", delnote_cmd))
app.add_handler(CommandHandler("remind", remind_cmd))
app.add_handler(CommandHandler("reminders", reminders_cmd))
app.add_handler(CommandHandler("delremind", delremind_cmd))
app.add_handler(CommandHandler("files", files_cmd))
app.add_handler(CommandHandler("stats", stats_cmd))
app.add_handler(CommandHandler("summary", summary_cmd))

# Files (photo/doc/video/voice/audio)
app.add_handler(MessageHandler(
    filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.VOICE | filters.AUDIO,
    handle_file,
))

# Text fallback
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_handler))

print("Bot start ho gaya... Smart mode ON ✨ (Notes, Reminders, Files, Stats, Daily Summary, Groups)")
app.run_polling()
