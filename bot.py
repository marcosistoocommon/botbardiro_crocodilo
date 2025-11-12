import asyncio
import logging
import os
import datetime

from config import load_config

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Job
from bday import birthday_job
from handlers import register_handlers

from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters




logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
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


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Received /ping from %s", update.effective_user and update.effective_user.id)
    await update.message.reply_text("pong")


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


    # lightweight ping for testing
    app.add_handler(CommandHandler("ping", ping_command))

    # Debug: log any update received (low priority group so it doesn't interfere)
    async def _debug_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("[debug_any] update: type=%s chat=%s user=%s text=%s", type(update), getattr(update, 'effective_chat', None), getattr(update, 'effective_user', None), getattr(update.message, 'text', None) if getattr(update, 'message', None) else None)

    app.add_handler(MessageHandler(filters.ALL, _debug_any), group=99)



    # determine local tz if available (debe ir antes de cualquier uso de local_tz)
    try:
        local_tz = datetime.datetime.now().astimezone().tzinfo
    except Exception:
        local_tz = None


    job_queue = app.job_queue

    # --- BIRTHDAY JOB ---
    async def _job_wrapper(context: ContextTypes.DEFAULT_TYPE):
        # Call the birthday_job which expects (application, config)
        await birthday_job(app, config)

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
    logger.info("Scheduled birthday job at %s:%s (first run: %s, tz=%s)", 
                desired_hour, desired_minute, first_run, local_tz)

    # Manual test command for birthday job
    async def test_birthday_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger the birthday job for testing."""
        logger.info("Manual birthday job triggered by %s", update.effective_user.full_name if update.effective_user else "Unknown")
        await birthday_job(app, config)
        await update.message.reply_text("✅ Birthday job executed. Check logs for details.")
    
    app.add_handler(CommandHandler("testBirthday", test_birthday_command))
    
    app.run_polling()


if __name__ == "__main__":
    main()
