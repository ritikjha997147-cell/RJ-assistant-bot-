import os
import pathlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from bot import config
from bot.utils.code_auditor import analyze_submitted_code

async def handle_code_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 🔒 Strict Owner Verification Rule
    if user_id != config.OWNER_ID:
        # Log event internally
        print(f"[SECURITY ALERT]: User {user_id} attempted to access code-management features.")
        await update.message.reply_text("⛔ Access denied. This feature is restricted.")
        # Alert Owner
        try:
            await context.bot.send_message(
                chat_id=config.OWNER_ID,
                text=f"⚠️ Security Alert: User {user_id} (@{update.effective_user.username}) attempted to access `/code` command!"
            )
        except Exception:
            pass
        return

    # Parse Format: /code/[file_name]/[code]
    raw_text = update.message.text
    parts = raw_text.split('/', 3) # Expecting ['', 'code', 'file_name', 'actual_code']
    
    if len(parts) < 4 or not parts[2].strip() or not parts[3].strip():
        await update.message.reply_text(
            "ℹ️ **Usage Format Check:**\n"
            "Please use the exact format:\n"
            "`/code/filename.py/your_python_code_here`",
            parse_mode="Markdown"
        )
        return

    target_file = parts[2].strip()
    actual_code = parts[3].strip()

    await update.message.reply_text("🔍 *Auditing codebase changes under Safe Sandbox...*", parse_mode="Markdown")

    # Call Audit Report
    report = analyze_submitted_code(actual_code, target_file)

    # Store state cleanly in context for replacement approval
    context.user_data["pending_code"] = actual_code
    context.user_data["pending_file"] = target_file

    # Formatting Report Output according to Blueprint
    report_msg = (
        "📊 **CODE HEALTH REPORT**\n\n"
        f"🔹 **Target File:** `{target_file}`\n"
        f"❌ **Syntax Errors:** { report['syntax_errors'] if report['syntax_errors'] else 'None' }\n"
        f"🔄 **Duplicate Functions:** { report['duplicate_functions'] if report['duplicate_functions'] else 'None' }\n"
        f"🛡️ **Security Issues:** { report['security_issues'] if report['security_issues'] else 'None' }\n"
        f"🏗️ **Architecture Issues:** { report['architecture_issues'] if report['architecture_issues'] else 'None' }\n"
        f"💡 **Recommended Fixes:** { report['recommended_fixes'] if report['recommended_fixes'] else 'None' }\n\n"
        f"🏆 **Overall Score:** `{report['score']}/100`\n"
        f"🟢 **Evaluation Status:** `{report['status']}`\n"
        f"📉 **Runtime Risks:** { report['runtime_risks'] if report['runtime_risks'] else 'None' }\n"
    )

    if report["score"] >= 70 and report["status"] == "PASS":
        keyboard = [
            [
                InlineKeyboardButton("✅ YES (Replace File)", callback_query_data="confirm_replace"),
                InlineKeyboardButton("❌ NO (Abort)", callback_query_data="cancel_replace")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"{report_msg}\n✨ *Code review completed successfully.*\nWould you like to replace the current implementation?", 
            reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"{report_msg}\n⚠️ *Code Score is below approval threshold or contains severe runtime threats. Replacement aborted.*",
            parse_mode="Markdown"
        )

async def handle_replacement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != config.OWNER_ID:
        return

    action = query.data
    pending_code = context.user_data.get("pending_code")
    pending_file = context.user_data.get("pending_file")

    if not pending_code or not pending_file:
        await query.edit_message_text("❌ Session expired or empty data.")
        return

    if action == "confirm_replace":
        # Safe Resolution Path determination
        target_path = config.BASE_DIR / "bot" / pending_file
        
        # Backup Policy Enforcement
        if target_path.exists():
            backup_name = f"{target_path.stem}_backup_2026_06_19{target_path.suffix}"
            backup_path = target_path.parent / backup_name
            with open(backup_path, "w", encoding="utf-8") as bf:
                bf.write(target_path.read_text(encoding="utf-8"))
            backup_status = f"📂 Backup created: `{backup_name}`"
        else:
            backup_status = "📂 New file creation (No backup required)"

        # Safe Write File execution
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(pending_code)
            
            await query.edit_message_text(
                f"🚀 **Deployment Execution Successful!**\n\n"
                f"✅ File Written: `bot/{pending_file}`\n"
                f"{backup_status}\n\n"
                f"ℹ️ *Render will automatically restart the system with the new implementation.*",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Write Error Failed: {str(e)}")
            
    elif action == "cancel_replace":
        await query.edit_message_text("❌ *Operation Cancelled by Owner. File system unmodified.*", parse_mode="Markdown")

    # Clear memory state
    context.user_data.pop("pending_code", None)
    context.user_data.pop("pending_file", None)