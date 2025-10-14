import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

LOG_FILE = "commands_log.json"


def log_command(user: str, command: str) -> None:
    """Registra un comando con usuario y hora en un archivo JSON."""
    # Future: limpiar command para distinguir entre comando y comando@bot
    command = command.split("@")[0].strip()
    record = {
        "timestamp": datetime.now().isoformat(),
        "user": user,
        "command": command,
    }

    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        data.append(record)

        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Error writing to %s: %s", LOG_FILE, e)
