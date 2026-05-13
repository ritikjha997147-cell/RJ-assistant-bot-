USER_COOLDOWN[user_id] = now

# search detection

search_needed = await asyncio.to_thread(
    needs_web_search,
    text
)

print("SEARCH NEEDED:", search_needed)

web_context = ""

# personality

if BOT_PERSONALITY == "savage":

    with open(
        "bot/personality/savage.txt",
        "r",
        encoding="utf-8"
    ) as file:

        system_prompt = file.read()

else:

    system_prompt = (
        "You are a professional AI consultant.\n\n"

        "RULES:\n"
        "- Explain clearly\n"
        "- Give structured answers\n"
        "- Use professional tone\n"
        "- Never invent facts\n"
        "- If unsure, say so clearly\n"
    )
