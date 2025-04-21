from fastapi import FastAPI, Request
import httpx
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

app = FastAPI()

# DB setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users_v2"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    city = Column(String)
    bio = Column(String)
    photo_file_id = Column(String)
    language = Column(String)

Base.metadata.create_all(bind=engine)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET_PATH = "/webhook"

user_states = {}

@app.get("/")
def root():
    return {"message": "KropLove_Bot is live!"}

@app.post(WEBHOOK_SECRET_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text")
    photo = message.get("photo")

    state = user_states.get(chat_id, {}).get("state")

    if text == "/start":
        user_states[chat_id] = {"lang": "uk", "state": "awaiting_name"}
        await send_message(chat_id, "Привіт! Давай створимо твою анкету.")
        await send_message(chat_id, "Як тебе звати?")
        return {"ok": True}

    if text == "/edit":
        with SessionLocal() as session:
            user = session.query(User).filter_by(telegram_id=chat_id).first()

        if not user:
            await send_message(chat_id, "Твоєї анкети ще немає. Спочатку створи її через /start.")
            return {"ok": True}

        user_states[chat_id] = {"lang": user.language, "state": "awaiting_name"}
        await send_message(chat_id, "Добре, почнемо редагування анкети.")
        await send_message(chat_id, "Як тебе звати?")
        return {"ok": True}

    if not text and state != "awaiting_photo":
        await send_message(chat_id, "Будь ласка, введи текст.")
        return {"ok": True}

    if state == "awaiting_name":
        user_states[chat_id]["name"] = text
        user_states[chat_id]["state"] = "awaiting_age"
        await send_message(chat_id, f"Дякую, {text}! Твоє ім’я збережено.")
        await send_message(chat_id, "Скільки тобі років?")
        return {"ok": True}

    if state == "awaiting_age":
        if not text.isdigit() or not (18 <= int(text) <= 99):
            await send_message(chat_id, "Введи, будь ласка, вік від 18 до 99.")
            return {"ok": True}
        user_states[chat_id]["age"] = int(text)
        user_states[chat_id]["state"] = "awaiting_gender"
        keyboard = {
            "keyboard": [[{"text": "ч"}, {"text": "ж"}]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await send_message(chat_id, "Обери стать:", keyboard)
        return {"ok": True}

    if state == "awaiting_gender":
        if text.lower() not in ["ч", "ж"]:
            await send_message(chat_id, "Оберіть стать: ч або ж")
            return {"ok": True}
        user_states[chat_id]["gender"] = text.lower()
        user_states[chat_id]["state"] = "awaiting_city"
        await send_message(chat_id, "З якого ти міста?", {"remove_keyboard": True})
        return {"ok": True}

    if state == "awaiting_city":
        user_states[chat_id]["city"] = text
        user_states[chat_id]["state"] = "awaiting_bio"
        await send_message(chat_id, "Напиши коротко про себе:")
        return {"ok": True}

    if state == "awaiting_bio":
        user_states[chat_id]["bio"] = text
        user_states[chat_id]["state"] = "awaiting_photo"
        await send_message(chat_id, "Надішли своє фото:")
        return {"ok": True}

    if state == "awaiting_photo":
        if not photo:
            await send_message(chat_id, "Будь ласка, надішли фото.")
            return {"ok": True}
        largest = max(photo, key=lambda x: x["file_size"])
        file_id = largest["file_id"]
        user_states[chat_id]["photo_file_id"] = file_id
        user_states[chat_id]["state"] = "done"

        data = user_states[chat_id]
        user = User(
            telegram_id=chat_id,
            name=data["name"],
            age=data["age"],
            gender=data["gender"],
            city=data["city"],
            bio=data["bio"],
            photo_file_id=data["photo_file_id"],
            language="uk"
        )
        with SessionLocal() as session:
            session.merge(user)
            session.commit()

        await send_message(chat_id, "Дякую! Твоя анкета збережена.")
        caption = f"{data['name']}, {data['age']} років\n{data['city']}\n{data['bio']}"
        await send_photo(chat_id, file_id, caption)
        return {"ok": True}

    await send_message(chat_id, "Натисни /start, щоб почати спочатку.")
    return {"ok": True}

async def send_message(chat_id: int, text: str, reply_markup: dict = None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)

async def send_photo(chat_id: int, file_id: str, caption: str):
    payload = {"chat_id": chat_id, "photo": file_id, "caption": caption}
    async with httpx.AsyncClient() as client:
        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json=payload)