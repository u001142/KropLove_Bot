from fastapi import FastAPI, Request
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET_PATH = "/webhook"

LANGUAGES = {
    "Українська 🇺🇦": "uk",
    "Русский 🇷🇺": "ru",
    "English 🇬🇧": "en"
}

@app.get("/")
def read_root():
    return {"message": "KropLove_Bot is running!"}


@app.post(WEBHOOK_SECRET_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    message = data.get("message")
    
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Якщо це /start
    if text == "/start":
        keyboard = {
            "keyboard": [[{"text": lang}] for lang in LANGUAGES.keys()],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await send_message(chat_id, "Привіт! Обери мову:", keyboard)
        return {"ok": True}

    # Якщо це вибір мови
    if text in LANGUAGES:
        lang_code = LANGUAGES[text]
        await send_message(chat_id, f"Ти обрав {text} ({lang_code})")
        # Тут можна зберегти мову в БД
        return {"ok": True}

    # Повідомлення за замовчуванням
    await send_message(chat_id, "Натисни /start, щоб обрати мову.")
    return {"ok": True}


async def send_message(chat_id: int, text: str, reply_markup: dict = None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=payload
        ) 
