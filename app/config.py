
import os
from dotenv import load_dotenv

# Завантаження змінних з .env файлу
load_dotenv()

# Основні змінні конфігурації
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# Параметри бота
DEFAULT_LANGUAGE = "uk"
WEBHOOK_PATH = "/webhook" 
