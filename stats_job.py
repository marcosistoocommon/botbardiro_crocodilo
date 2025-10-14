import json
import os
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
LOG_FILE = "commands_log.json"
STATS_IMAGE = "stats.png"


def generate_stats_image(data):
    """Genera un gráfico de barras (0–23 horas) con el volumen de comandos."""
    if not data:
        return None

    hours = [datetime.fromisoformat(d["timestamp"]).hour for d in data]
    hourly_counts = defaultdict(int)
    for h in hours:
        hourly_counts[h] += 1

    # Aseguramos las 24 horas en el eje X
    x = list(range(24))
    y = [hourly_counts.get(h, 0) for h in x]

    plt.figure(figsize=(10, 4))
    plt.bar(x, y)
    plt.xlabel("Hora del día")
    plt.ylabel("Comandos enviados")
    plt.title("Actividad diaria de comandos")
    plt.xticks(range(0, 24))
    plt.tight_layout()
    plt.savefig(STATS_IMAGE)
    plt.close()
    return STATS_IMAGE


async def stats_job(application, config, chat_id=None, clear_after=True):
    logger.warning(f"[stats_job] Llamado con chat_id={chat_id}, clear_after={clear_after} y config={config}")
    """Tarea diaria que envía las estadísticas y limpia el log.
    Si chat_id se pasa, envía ahí; si no, usa config.BIRTHDAY_CHAT_ID.
    clear_after: si True borra el log al final; si False lo mantiene (usado por /stats manual)."""
    if chat_id is None:
        chat_id = getattr(config, "BIRTHDAY_CHAT_ID", None)

    if not os.path.exists(LOG_FILE):
        logger.error("[stats_job] No command log file found — skipping stats job.")
        return

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.warning(f"[stats_job] Datos leídos: {data}")
    except Exception as e:
        logger.error(f"[stats_job] Failed to read command log: {e}")
        return

    if not data:
        message = "Hoy no se han usado comandos."
        if chat_id:
            await application.bot.send_message(chat_id=int(chat_id), text=message)
        logger.info(message)
        os.remove(LOG_FILE)
        return

    # --- Análisis ---
    users = [d["user"] for d in data]
    commands = [d["command"] for d in data]

    user_counts = Counter(users)
    command_counts = Counter(commands)

    top_user, top_count = user_counts.most_common(1)[0]

    # --- Generar imagen ---
    image_path = generate_stats_image(data)

    # --- Enviar mensajes ---
    if chat_id:
        try:
            if image_path:
                await application.bot.send_photo(chat_id=int(chat_id), photo=open(image_path, "rb"))

            top_msg = f"🏆 Usuario más activo hoy: {top_user} ({top_count} comandos)"
            await application.bot.send_message(chat_id=int(chat_id), text=top_msg)

            summary_lines = [f"{cmd}: {count}" for cmd, count in command_counts.items()]
            summary_msg = "📊 Resumen de comandos de hoy:\n" + "\n".join(summary_lines)
            await application.bot.send_message(chat_id=int(chat_id), text=summary_msg)
        except Exception as e:
            logger.exception("Failed to send stats messages: %s", e)
    else:
        logger.info("No chat_id configured, stats message not sent.")

    # --- Limpieza ---
    try:
        if clear_after:
            os.remove(LOG_FILE)
        if os.path.exists(image_path):
            os.remove(image_path)
    except Exception as e:
        logger.warning("Failed to remove log/image files: %s", e)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"[stats_command] Recibido comando /stats en chat_id={update.effective_chat.id}")
    chat_id = update.effective_chat.id
    app = context.application
    # Usa config global si está en bot_data, si no, usa el de config.py
    config = context.bot_data.get("config")
    if config is None:
        from config import load_config
        config = load_config()
    await stats_job(app, config, chat_id=chat_id, clear_after=False)
    logger.warning(f"[stats_command] stats_job ejecutado para chat_id={chat_id}")
    await update.message.reply_text("📊 Estadísticas generadas manualmente.")