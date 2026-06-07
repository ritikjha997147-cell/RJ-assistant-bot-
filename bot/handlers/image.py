import base64
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import IMAGE_DB_CHANNEL_ID, GEMINI_API_KEYS
from bot.memory.user_memory import LAST_IMAGE

pending_images = {}

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        user = update.effective_user
        LAST_IMAGE[user.id] = file_id

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        file = await context.bot.get_file(file_id)
        file_bytes = await file.download_as_bytearray()

        ai_description = None
        extracted_text = None
        suggested_title = "My Image"

        if GEMINI_API_KEYS:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=GEMINI_API_KEYS[0])
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        types.Part.from_bytes(data=bytes(file_bytes), mime_type="image/jpeg"),
                        types.Part.from_text(text="Analyze this image and provide:\n1. EXTRACTED TEXT: Any text visible in image. If none write None\n2. DESCRIPTION: Clear description in 2-3 sentences\n3. TITLE: Short creative title 5 words max\n\nFormat exactly like:\nTEXT: [text or None]\nDESCRIPTION: [description]\nTITLE: [title]")
                    ]
                )
                for line in response.text.strip().split('\n'):
                    if line.startswith("TEXT:"):
                        t = line.replace("TEXT:", "").strip()
                        if t.lower() != "none":
                            extracted_text = t
                    elif line.startswith("DESCRIPTION:"):
                        ai_description = line.replace("DESCRIPTION:", "").strip()
                    elif line.startswith("TITLE:"):
                        suggested_title = line.replace("TITLE:", "").strip()
            except Exception as e:
                print(f"[GEMINI VISION ERROR]: {e}")

        pending_images[user.id] = {"file_id": file_id, "description": ai_description, "extracted_text": extracted_text}
        context.user_data["waiting_for_image_title"] = True
        context.user_data["image_file_id"] = file_id

        reply = "🖼 *Image received!*\n\n"
        if extracted_text:
            reply += f"📝 *Text found:*\n`{extracted_text}`\n\n"
        if ai_description:
            reply += f"🤖 *AI Description:*\n{ai_description}\n\n"
        if suggested_title:
            reply += f"💡 *Suggested title:* _{suggested_title}_\n\n"
        reply += "💬 *Is image ka title batao!*\n_(Skip: /skip)_"

        await update.message.reply_text(reply, parse_mode="Markdown")

        try:
            caption = f"📸 Image\nUser: {user.first_name} | ID: {user.id}"
            if ai_description:
                caption += f"\nAI: {ai_description[:100]}"
            await context.bot.send_photo(chat_id=IMAGE_DB_CHANNEL_ID, photo=file_id, caption=caption)
        except Exception as e:
            print(f"[DB CHANNEL ERROR]: {e}")

    except Exception as e:
        print(f"[IMAGE HANDLER ERROR]: {e}")
        await update.message.reply_text("Image save ho gaya!")


async def handle_image_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.user_data.get("waiting_for_image_title"):
        return False

    title = update.message.text
    context.user_data["waiting_for_image_title"] = False

    if title.startswith("/skip"):
        await update.message.reply_text("Ok, image bina title ke save ho gaya!")
        return True

    pending = pending_images.get(user.id, {})
    reply = f"✅ *Image saved!*\n\n🏷 *Title:* {title}\n"
    if pending.get("extracted_text"):
        reply += f"📝 *Text:* {pending['extracted_text']}\n"
    if pending.get("description"):
        reply += f"🤖 *AI:* {pending['description']}\n"
    reply += "\n_Shukriya! Image tag ho gaya_ 🎉"

    await update.message.reply_text(reply, parse_mode="Markdown")
    if user.id in pending_images:
        del pending_images[user.id]
    return True