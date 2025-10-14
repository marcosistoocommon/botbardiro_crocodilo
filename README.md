# EuriBot — Minimal Telegram Bot Skeleton

This repository contains a minimal Python skeleton for a Telegram bot using python-telegram-bot v20+ (async API).

Files:
- `bot.py` — entrypoint and handlers for /start and /help
- `config.py` — loads environment variables (uses python-dotenv)
- `requirements.txt` — required Python packages
- `.env.example` — example environment file

Quick start:
1. Create a virtual environment and activate it.
2. pip install -r requirements.txt
3. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN`.
4. Run `python bot.py`.
