import os
from dataclasses import dataclass
from dotenv import load_dotenv
import pathlib
import logging

logger = logging.getLogger(__name__)

# Load .env from the project directory (next to this file). If missing, fall back to .env.example
base = pathlib.Path(__file__).parent
env_path = base / ".env"
example_path = base / ".env.example"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info("Loaded environment from %s", env_path)
elif example_path.exists():
    load_dotenv(dotenv_path=example_path)
    logger.info("Loaded environment from %s (fallback)", example_path)
else:
    # last resort: default behavior (current dir)
    load_dotenv()
    logger.warning("No .env or .env.example next to config.py; using default load_dotenv() behavior")


@dataclass
class Config:
    TELEGRAM_BOT_TOKEN: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    # Optional: chat id where birthday messages will be sent (as int). If empty, messages are logged but not sent.
    BIRTHDAY_CHAT_ID: str


def load_config() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    birthday_chat = os.getenv("BIRTHDAY_CHAT_ID", "")
    return Config(
        TELEGRAM_BOT_TOKEN=token,
        SUPABASE_URL=supabase_url,
        SUPABASE_KEY=supabase_key,
        BIRTHDAY_CHAT_ID=birthday_chat,
    )
