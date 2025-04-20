from fastapi import APIRouter, Request
from app.database import SessionLocal
from app.models.like import Like
from app.models.match import Match
from app.models.user import User
from app.routers.chat_router import start_chat
from app.config import BOT_TOKEN
import httpx

router = APIRouter()

@router.post("/like")
async def handle_like(request: Request):
    data = await request.json()
    message = data.get("message")

    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if not text.isdigit():
        await send_message(chat_id, "Введіть ID користувача, якого хочете лайкнути.")
        return {"ok": True}

    liked_user_id = int(text)
    session = SessionLocal()

    # Перевірка чи користувач існує
    liked_user = session.query(User).filter(User.telegram_id == liked_user_id).first()
    if not liked_user:
        await send_message(chat_id, "Користувача не знайдено.")
        return {"ok": True}

    # Перевірка чи вже є лайк
    existing_like = session.query(Like).filter(
        Like.liker_id == chat_id,
        Like.liked_id == liked_user_id
    ).first()

    if existing_like:
        await send_message(chat_id, "Ви вже поставили лайк цьому користувачу.")
        return {"ok": True}

    # Зберігаємо лайк
    new_like = Like(liker_id=chat_id, liked_id=liked_user_id)
    session.add(new_like)
    session.commit()

    # Перевірка взаємності
    mutual_like = session.query(Like).filter(
        Like.liker_id == liked_user_id,
        Like.liked_id == chat_id
    ).first()

    if mutual_like:
        # Створення Match
        new_match = Match(user1_id=chat_id, user2_id=liked_user_id)
        session.add(new_match)
        session.commit()

        # Старт анонімного чату
        start_chat(chat_id, liked_user_id)
        await send_message(chat_id, "У вас взаємна симпатія! Чат розпочато.")
        await send_message(liked_user_id, "У вас взаємна симпатія! Чат розпочато.")
    else:
        await send_message(chat_id, "Лайк збережено.")

    session.close()
    return {"ok": True}


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
