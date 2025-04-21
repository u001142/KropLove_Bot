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

user_states = {}

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
    photo = message.get("photo")

    # /start
    if text == "/start":
        keyboard = {
            "keyboard": [[{"text": lang}] for lang in LANGUAGES.keys()],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await send_message(chat_id, "Привіт! Обери мову:", keyboard)
        return {"ok": True}

    # Вибір мови
    if text in LANGUAGES:
        lang_code = LANGUAGES[text]
        user_states[chat_id] = {"lang": lang_code, "state": "awaiting_name"}

        await send_message(chat_id, f"Ти обрав {text}.", {"remove_keyboard": True})
        await send_message(chat_id, "Як тебе звати?")
        return {"ok": True}

    # Крок 1: Ім'я
    if chat_id in user_states and user_states[chat_id]["state"] == "awaiting_name":
        user_states[chat_id]["name"] = text
        user_states[chat_id]["state"] = "awaiting_age"
        await send_message(chat_id, f"Дякую, {text}! Твоє ім’я збережено.")
        await send_message(chat_id, "Скільки тобі років?")
        return {"ok": True}

    # Крок 2: Вік
    if chat_id in user_states and user_states[chat_id]["state"] == "awaiting_age":
        if not text.isdigit():
            await send_message(chat_id, "Будь ласка, введи число — скільки тобі років.")
            return {"ok": True}
        user_states[chat_id]["age"] = int(text)
        user_states[chat_id]["state"] = "awaiting_gender"
        keyboard = {
            "keyboard": [[{"text": "ч"}, {"text": "ж"}]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await send_message(chat_id, "Обери свою стать:", keyboard)
        return {"ok": True}

    # Крок 3: Стать
    if chat_id in user_states and user_states[chat_id]["state"] == "awaiting_gender":
        if text.lower() not in ["ч", "ж"]:
            await send_message(chat_id, "Оберіть стать: ч або ж")
            return {"ok": True}
        user_states[chat_id]["gender"] = text.lower()
        user_states[chat_id]["state"] = "awaiting_city"
        await send_message(chat_id, "З якого ти міста?", {"remove_keyboard": True})
        return {"ok": True}

    # Крок 4: Місто
    if chat_id in user_states and user_states[chat_id]["state"] == "awaiting_city":
        user_states[chat_id]["city"] = text
        user_states[chat_id]["state"] = "awaiting_bio"
        await send_message(chat_id, "Напиши коротко про себе:")
        return {"ok": True}

    # Крок 5: Опис
    if chat_id in user_states and user_states[chat_id]["state"] == "awaiting_bio":
        user_states[chat_id]["bio"] = text
        user_states[chat_id]["state"] = "awaiting_photo"
        await send_message(chat_id, "Надішли своє фото:")
        return {"ok": True}

    # Крок 6: Фото
    if chat_id in user_states and user_states[chat_id]["state"] == "awaiting_photo":
        if not photo:
            await send_message(chat_id, "Будь ласка, надішли фото.")
            return {"ok": True}
        user_states[chat_id]["photo_file_id"] = photo[-1]["file_id"]
        user_states[chat_id]["state"] = "done"

        await send_message(chat_id, "Дякую! Твоя анкета збережена.")
        return {"ok": True}

    await send_message(chat_id, "Натисни /start, щоб почати знову.")
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
