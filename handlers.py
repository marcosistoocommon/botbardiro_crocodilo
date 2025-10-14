import asyncio
import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bday import get_birthday_message_sync, get_next_birthday_sync

logger = logging.getLogger(__name__)


def register_handlers(app: Any, config) -> None:
    """Register command handlers onto the given Application instance.

    Handlers are defined as closures so they can capture the `config` object
    without making the module depend on application-global state.
    """

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        await update.message.reply_text(f"Hello {user.first_name or 'there'}! I'm alive.")

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Available commands: /start, /help, /getCumple")

    async def get_cumple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /getCumple: fetches nearest birthday from Supabase and replies."""
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, get_next_birthday_sync, config.SUPABASE_URL, config.SUPABASE_KEY
        )
        if not data.get("found"):
            await update.message.reply_text("No hay cumpleaños registrados.")
            return
        text = f"Próximo cumple: {data['name']} el {data['date']} (en {data['days_until']} días)"
        if data.get("others"):
            text += "\nTambién: " + ", ".join(data["others"])
        await update.message.reply_text(text)

    # Register handlers on the application
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("getCumple", get_cumple_cmd))
