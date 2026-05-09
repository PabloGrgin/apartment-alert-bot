import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "apartments.db"))

FILTERS_PATH = BASE_DIR / "config" / "filters.yaml"


def load_filters() -> dict:
    with open(FILTERS_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)