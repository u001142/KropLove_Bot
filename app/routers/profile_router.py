from fastapi import APIRouter, Request
from app.database import SessionLocal
from app.models.user import User
from app.config import BOT_TOKEN
import httpx

router = APIRouter()

# Проміжне сховище для заповнення анкети (можна замінити на кеш або БД)
user_states = {}

@router.post("/profile")
async def handle_profile(request: Request):
    data = await request.json()
    message = data.get("message")

    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    photo = message.get("photo")

    state = user_states.get(chat_id, {}).get("state", "name")

    if photo:
        user_states[chat_id]["photo_file_id"] = photo[-1]["file_id"]
        # Зберігаємо в базу
        session = SessionLocal()
        save_profile(chat_id, session)
        session.close()
        del user_states[chat_id]
        await send_message(chat_id, "Анкету збережено!")
        return {"ok": True}

    if state == "name":
        user_states[chat_id] = {"name": text, "state": "age"}
        await send_message(chat_id, "Скільки тобі років?")
    elif state == "age":
        user_states[chat_id]["age"] = text
        user_states[chat_id]["state"] = "gender"
        await send_message(chat_id, "Оберіть стать (ч/ж):")
    elif state == "gender":
        user_states[chat_id]["gender"] = text
        user_states[chat_id]["state"] = "city"
        await send_message(chat_id, "З якого ти міста?")
    elif state == "city":
        user_states[chat_id]["city"] = text
        user_states[chat_id]["state"] = "bio"
        await send_message(chat_id, "Напиши кілька слів про себе:")
    elif state == "bio":
        user_states[chat_id]["bio"] = text
        user_states[chat_id]["state"] = "photo"
        await send_message(chat_id, "Надішли своє фото:")
    else:
        await send_message(chat_id, "Я чекаю фото для завершення анкети.")

    return {"ok": True}


def save_profile(user_id: int, db):
    data = user_states[user_id]
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        user = User(telegram_id=user_id)

    user.name = data["name"]
    user.age = int(data["age"])
    user.gender = data["gender"]
    user.city = data["city"]
    user.bio = data["bio"]
    user.photo_file_id = data["photo_file_id"]

    db.add(user)
    db.commit()


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
