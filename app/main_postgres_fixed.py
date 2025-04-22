from fastapi import FastAPI, Request
import httpx
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, ForeignKey
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
    referrer_id = Column(BigInteger, nullable=True)
    premium_until = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET_PATH = "/webhook"
ADMINS = [5347187083]  # ← Вкажи свій Telegram ID

user_states = {}
admin_states = {}

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

    # Referral tracking
    if "ref=" in str(data.get("message")) and chat_id not in user_states:
        entities = message.get("entities", [])
        for entity in entities:
            if entity.get("type") == "bot_command":
                offset = entity["offset"]
                length = entity["length"]
                command = text[offset:offset+length]
                if command.startswith("/start") and " " in text:
                    ref_id = text.split()[1].replace("ref=", "")
                    user_states[chat_id] = {"referrer_id": int(ref_id)}

    # Команда /refer
    if text == "/refer":
        with SessionLocal() as session:
            user = session.query(User).filter_by(telegram_id=chat_id).first()
            if not user:
                await send_message(chat_id, "Спочатку створи анкету через /start")
                return {"ok": True}

            referred = session.query(User).filter_by(referrer_id=chat_id).count()
            now = datetime.utcnow()
            premium_status = "Немає"
            if user.premium_until and user.premium_until > now:
                days_left = (user.premium_until - now).days
                premium_status = f"до {user.premium_until.date()} ({days_left} днів залишилось)"

            link = f"https://t.me/{os.getenv('BOT_USERNAME')}?start=ref={chat_id}"
            await send_message(chat_id, f"Запрошено: {referred} користувачів\nПреміум: {premium_status}\n\nТвоє реферальне посилання:\n{link}")
        return {"ok": True}

    # ======= СТВОРЕННЯ АНКЕТИ =======
    state = user_states.get(chat_id, {}).get("state")

    if text == "/start":
        user_states[chat_id] = {"lang": "uk", "state": "awaiting_name"}
        await send_message(chat_id, "Привіт! Давай створимо твою анкету.")
        await send_message(chat_id, "Як тебе звати?")
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
            "keyboard": [[{"text": "👨"}, {"text": "👩"}]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await send_message(chat_id, "Обери стать:", keyboard)
        return {"ok": True}

    if state == "awaiting_gender":
        if text not in ["👨", "👩"]:
            await send_message(chat_id, "Оберіть стать: 👨 або 👩")
            return {"ok": True}
        user_states[chat_id]["gender"] = "ч" if text == "👨" else "ж"
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

        data = user_states[chat_id]
        referrer_id = user_states.get(chat_id, {}).get("referrer_id")

        with SessionLocal() as session:
            user = User(
                telegram_id=chat_id,
                name=data["name"],
                age=data["age"],
                gender=data["gender"],
                city=data["city"],
                bio=data["bio"],
                photo_file_id=file_id,
                language="uk",
                referrer_id=referrer_id
            )
            session.merge(user)
            session.commit()

            # Нарахування преміуму рефереру
            if referrer_id:
                count = session.query(User).filter_by(referrer_id=referrer_id).count()
                if count % 10 == 0:
                    ref_user = session.query(User).filter_by(telegram_id=referrer_id).first()
                    if ref_user:
                        if ref_user.premium_until and ref_user.premium_until > datetime.utcnow():
                            ref_user.premium_until += timedelta(days=7)
                        else:
                            ref_user.premium_until = datetime.utcnow() + timedelta(days=7)
                        session.commit()

        await send_message(chat_id, "Дякую! Твоя анкета збережена.")
        caption = f"{data['name']}, {data['age']} років\n{data['city']}\n{data['bio']}"
        await send_photo(chat_id, file_id, caption)
        return {"ok": True}

    await send_message(chat_id, "Натисни /start або /refer.")
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
