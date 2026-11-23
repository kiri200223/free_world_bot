import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID", "")

# Время отправки раз в сутки (часы и минуты)
SEND_HOUR = int(os.getenv("SEND_HOUR", "23"))
SEND_MINUTE = int(os.getenv("SEND_MINUTE", "0"))

DATABASE_PATH = "giveaways.db"
