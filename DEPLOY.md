# 🚀 RJ Bot — Render + UptimeRobot Deployment Guide

## What was fixed
| Fix | Before | After |
|-----|--------|-------|
| Memory (chat history) | 10 messages | 50 messages |
| AI response length | 300 tokens | 1000 tokens |
| Cooldown between messages | 5 seconds | 1 second |
| Fake typing delay | 5 seconds | Removed |
| Procfile type | `worker` | `web` (required for Render) |
| Health endpoint | None | `/health` added for UptimeRobot |

---

## STEP 1 — Push to GitHub

```bash
cd rj-bot-fixed
git init
git add .
git commit -m "fix: render deploy + memory + speed improvements"
git remote add origin https://github.com/YOUR_USERNAME/rj-bot.git
git push -u origin main
```

---

## STEP 2 — Deploy on Render

1. Go to https://render.com and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Fill in settings:
   - **Name:** rj-assistant-bot
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m bot.main`
   - **Instance Type:** Free
5. Add **Environment Variables** (click "Add Environment Variable"):
   ```
   BOT_TOKEN        = your telegram bot token
   OWNER_ID         = your telegram user id
   GROQ_API_KEY     = your groq api key
   DATABASE_CHANNEL_ID   = your channel id
   IMAGE_DB_CHANNEL_ID   = your channel id
   MEMORY_CHANNEL_ID     = your channel id
   ```
6. Click **"Create Web Service"**
7. Wait for the build to finish ✅
8. Copy your Render URL (e.g. `https://rj-assistant-bot.onrender.com`)

---

## STEP 3 — Setup UptimeRobot (keeps bot alive 24/7)

Render free tier sleeps after 15 minutes of no traffic.
UptimeRobot pings your bot every 5 minutes to keep it awake.

1. Go to https://uptimerobot.com and create a free account
2. Click **"Add New Monitor"**
3. Fill in:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** RJ Bot
   - **URL:** `https://rj-assistant-bot.onrender.com/health`
   - **Monitoring Interval:** Every 5 minutes
4. Click **"Create Monitor"** ✅

Your bot is now online 24/7 for free! 🎉

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Check all env variables are set |
| Bot not responding | Check Render logs for errors |
| Bot goes offline | Make sure UptimeRobot monitor is active |
| DB errors | SQLite resets on Render free tier restarts — this is normal |
