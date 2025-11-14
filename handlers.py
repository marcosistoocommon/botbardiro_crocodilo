import asyncio
import logging
from typing import Any
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bday import get_next_birthday_sync, join_names

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

        def ymd_to_dmy_simple(s: str) -> str:
            y, m, d = s.split("-")
            return f"{d.zfill(2)}-{m.zfill(2)}-{y}"
        """Handler for /getCumple: fetches nearest birthday from Supabase and replies."""
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, get_next_birthday_sync, config.SUPABASE_URL, config.SUPABASE_KEY
        )
        if not data.get("found"):
            await update.message.reply_text("No hay cumpleaños registrados.")
            return
        fecha = ymd_to_dmy_simple(data['date'])

        # Normalize base name and others, and join with commas and ' y ' before the last name.
        base_name = str(data.get('name') or data.get('id') or 'desconocido')
        raw_others = data.get('others') or []
        others = [str(o) for o in raw_others if str(o) and str(o) != base_name]

        name = join_names([base_name] + others)

        if data['days_until'] == 0:
            text = f"Hoy es el cumpleaños de {name}! 🎉🎂"
        elif data['days_until'] == 1:
            text = f"El siguiente cumpleaños es el de {name} el {fecha}, osea, mañana!"
        else:
            text = f"El siguiente cumpleaños es el de {name} el {fecha}, en solo {data['days_until']} días!"
        await update.message.reply_text(text)

    # Register handlers on the application
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("getCumple", get_cumple_cmd))
