import time, re
from telegram import Update
from telegram.ext import ContextTypes

busy_state = {"active": False, "message": "RJ abhi busy hai, thodi der baad message karo!", "until": None, "owner_id": None}

async def set_busy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.config import OWNER_ID
    user_id = update.effective_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("Sirf owner busy mode set kar sakta hai!")
        return
    if not context.args:
        await update.message.reply_text("/busy on\n/busy on 2 hr\n/busy on 30 min\n/busy on Meeting chal raha hai\n/busy off\n/busy status")
        return
    action = context.args[0].lower()
    if action == "off":
        busy_state["active"] = False
        busy_state["until"] = None
        await update.message.reply_text("Busy mode OFF! Ab normal replies milenge.")
        return
    if action == "status":
        if busy_state["active"]:
            msg = f"Busy Mode ON\nMessage: {busy_state['message']}"
            if busy_state["until"]:
                remaining = int(busy_state["until"] - time.time())
                if remaining > 0:
                    msg += f"\nEnds in: {remaining//60}m {remaining%60}s"
                else:
                    busy_state["active"] = False
                    msg = "Busy mode expired - now OFF"
        else:
            msg = "Busy Mode OFF - Bot responding normally"
        await update.message.reply_text(msg)
        return
    if action == "on":
        busy_state["active"] = True
        busy_state["owner_id"] = user_id
        busy_state["until"] = None
        remaining_args = context.args[1:] if len(context.args) > 1 else []
        if remaining_args:
            time_match = re.match(r'^(\d+)\s*(sec|min|minute|hr|hour|hours|minutes)$', " ".join(remaining_args[:2]), re.IGNORECASE)
            if time_match:
                amount = int(time_match.group(1))
                unit = time_match.group(2).lower()
                unit_map = {"sec":1,"min":60,"minute":60,"minutes":60,"hr":3600,"hour":3600,"hours":3600}
                busy_state["until"] = time.time() + amount * unit_map[unit]
                custom_msg = " ".join(remaining_args[2:])
                busy_state["message"] = custom_msg if custom_msg else f"RJ abhi {amount} {unit} ke liye busy hai!"
                end_time = time.strftime("%I:%M %p", time.localtime(busy_state["until"]))
                await update.message.reply_text(f"Busy Mode ON!\nDuration: {amount} {unit}\nAuto OFF at: {end_time}\nMessage: {busy_state['message']}")
            else:
                busy_state["message"] = " ".join(remaining_args)
                await update.message.reply_text(f"Busy Mode ON!\nMessage: {busy_state['message']}\n/busy off likhne par band hoga")
        else:
            busy_state["message"] = "RJ abhi busy hai, thodi der baad message karo!"
            await update.message.reply_text(f"Busy Mode ON!\nMessage: {busy_state['message']}\n/busy off likhne par band hoga")

def is_busy(user_id=None):
    if not busy_state["active"]:
        return False, None
    if busy_state["until"] and time.time() > busy_state["until"]:
        busy_state["active"] = False
        busy_state["until"] = None
        return False, None
    if user_id and user_id == busy_state.get("owner_id"):
        return False, None
    return True, busy_state["message"]
