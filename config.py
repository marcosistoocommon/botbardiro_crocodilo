import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


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
