import asyncio
import logging
import os
import datetime

from config import load_config

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Job
from bday import birthday_job
from handlers import register_handlers


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)
# Reduce verbosity of noisy third-party loggers
for noisy in ("httpx", "httpcore", "telegram", "apscheduler"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(f"Hello {user.first_name or 'there'}! I'm alive.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Available commands: /start, /help")


def main() -> None:
    config = load_config()
    token = config.TELEGRAM_BOT_TOKEN

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Set it in the environment or .env file.")
        raise SystemExit(1)

    app = ApplicationBuilder().token(token).build()


    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def handle_exception(loop, context):
        # Log uncaught exceptions at error level without verbose debug context
        logger.error("Uncaught exception in event loop: %s", context.get("message") or context)

    loop.set_exception_handler(handle_exception)




    # Register command handlers from handlers.py
    register_handlers(app, config)

    # Schedule birthday job every day at 9:00 local time
    # python-telegram-bot's JobQueue expects a callback with signature (context)

    async def _job_wrapper(context: ContextTypes.DEFAULT_TYPE):
        # Call the birthday_job which expects (application, config)
        await birthday_job(app, config)

    # Use run_repeating: compute next local target (e.g., 09:00) and repeat every 24h.
    job_queue = app.job_queue

    # determine local tz if available
    try:
        local_tz = datetime.datetime.now().astimezone().tzinfo
    except Exception:
        local_tz = None

    desired_hour = int(os.getenv("BIRTHDAY_HOUR", "9"))
    desired_minute = int(os.getenv("BIRTHDAY_MINUTE", "0"))

    now = datetime.datetime.now().astimezone() if local_tz else datetime.datetime.now()
    try:
        if local_tz:
            today_target = datetime.datetime(now.year, now.month, now.day, desired_hour, desired_minute, tzinfo=local_tz)
        else:
            today_target = datetime.datetime(now.year, now.month, now.day, desired_hour, desired_minute)
    except Exception:
        today_target = datetime.datetime(now.year, now.month, now.day, desired_hour, desired_minute)

    if today_target <= now:
        first_run = today_target + datetime.timedelta(days=1)
    else:
        first_run = today_target

    interval = datetime.timedelta(days=1)
    job_queue.run_repeating(_job_wrapper, interval=interval, first=first_run)
    app.run_polling()


if __name__ == "__main__":
    main()
