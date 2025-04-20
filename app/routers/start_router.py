from fastapi import APIRouter, Request
from app.database import SessionLocal
from app.models.user import User
from app.config import BOT_TOKEN
import httpx

router = APIRouter()

LANGUAGES = {
    "Українська 🇺🇦": "uk",
    "Русский 🇷🇺": "ru",
    "English 🇬🇧": "en"
}


@router.post("/start")
async def start_handler(request: Request):
    data = await request.json()
    message = data.get("message")

    if not message or message.get("text") != "/start":
        return {"ok": True}

    chat_id = message["chat"]["id"]

    # Створення або оновлення користувача
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == chat_id).first()
    if not user:
        user = User(telegram_id=chat_id)
        session.add(user)
    user.language = None  # скидаємо мову для повторного вибору
    session.commit()
    session.close()

    # Надсилання кнопок для вибору мови
    keyboard = {
        "keyboard": [[{"text": lang}] for lang in LANGUAGES.keys()],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

    await send_message(chat_id, "Ласкаво просимо! Будь ласка, обери мову:", keyboard)
    return {"ok": True}


@router.post("/language")
async def language_handler(request: Request):
    data = await request.json()
    message = data.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text")

    if text not in LANGUAGES:
        return {"ok": True}

    selected_lang = LANGUAGES[text]

    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == chat_id).first()
    if user:
        user.language = selected_lang
        session.commit()
    session.close()

    await send_message(chat_id, f"Ти обрав {text}. Тепер можна створити анкету.")
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
