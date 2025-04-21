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

user_states = {}  # тимчасове збереження стану користувача

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

    # /start — вибір мови
    if text == "/start":
        keyboard = {
            "keyboard": [[{"text": lang}] for lang in LANGUAGES.keys()],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await send_message(chat_id, "Привіт! Обери мову:", keyboard)
        return {"ok": True}

    # Обробка вибору мови
    if text in LANGUAGES:
        lang_code = LANGUAGES[text]
        user_states[chat_id] = {"lang": lang_code, "state": "awaiting_name"}

        # Прибираємо клавіатуру
        remove_keyboard = { "remove_keyboard": True }

        await send_message(chat_id, f"Ти обрав {text}.", remove_keyboard)
        await send_message(chat_id, "Як тебе звати?")
        return {"ok": True}

    # Реєстрація: ім’я
    if chat_id in user_states and user_states[chat_id]["state"] == "awaiting_name":
        user_states[chat_id]["name"] = text
        user_states[chat_id]["state"] = "done"
        await send_message(chat_id, f"Дякую, {text}! Твоє ім’я збережено.")
        # Тут можна перейти до наступного кроку анкети (вік, стать і т.д.)
        return {"ok": True}

    # Повідомлення за замовчуванням
    await send_message(chat_id, "Натисни /start, щоб почати.")
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
