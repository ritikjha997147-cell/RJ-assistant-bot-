import re
import time
from datetime import datetime, timedelta
import dateparser

HINGLISH_DAYS = {
    "agale din": 1,
    "kal subah": 1,
    "kal shaam": 1,
    "kal raat": 1,
    "aaj": 0,
    "kal": 1,
    "parson": 2,
    "parso": 2,
}

TIME_OF_DAY = {
    "subah": 6,
    "dopahar": 12,
    "shaam": 17,
    "raat ko": 20,
    "raat": 20,
    "sawere": 6,
}

def parse_hinglish_reminder(text: str):
    text_lower = text.lower().strip()
    day_offset = 0
    for phrase, offset in sorted(HINGLISH_DAYS.items(), key=lambda x: -len(x[0])):
        if phrase in text_lower:
            day_offset = offset
            break
    time_pattern = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|baje|bajhe)?)', text_lower, re.IGNORECASE)
    parsed_time = None
    if time_pattern:
        raw_time = re.sub(r'\s*(baje|bajhe)', '', time_pattern.group(1)).strip()
        parsed_time = dateparser.parse(raw_time, settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata", "RETURN_AS_TIMEZONE_AWARE": False})
    now = datetime.now()
    target_date = now + timedelta(days=day_offset)
    if parsed_time:
        remind_dt = target_date.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
    else:
        default_hour = None
        for phrase, hour in TIME_OF_DAY.items():
            if phrase in text_lower:
                default_hour = hour
                break
        if default_hour:
            remind_dt = target_date.replace(hour=default_hour, minute=0, second=0, microsecond=0)
        else:
            return None, None
    if remind_dt.timestamp() <= time.time():
        remind_dt += timedelta(days=1)
    message = text_lower
    for phrase in HINGLISH_DAYS:
        message = message.replace(phrase, "")
    message = re.sub(r'\d{1,2}(?::\d{2})?\s*(?:am|pm|baje|bajhe)?', '', message)
    for filler in ["remind karna", "yaad dilana", "remind kar dena", "message kar dena", "bata dena", "mujhe", "muje", "ko", "pe", "par"]:
        message = message.replace(filler, "")
    message = re.sub(r'\s+', ' ', message).strip(" ,.-")
    if not message:
        message = "Reminder!"
    return remind_dt.timestamp(), message.capitalize()
