from fastapi import APIRouter, Request
from app.database import SessionLocal
from app.models.premium import Premium
from app.config import BOT_TOKEN
import httpx
from datetime import datetime

router = APIRouter()


@router.post("/premium")
async def check_premium(request: Request):
    data = await request.json()
    message = data.get("message")

    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]

    session = SessionLocal()
    premium = session.query(Premium).filter(Premium.user_id == chat_id).first()

    if premium and premium.expiration_date > datetime.utcnow():
        await send_message(chat_id, "Ваш преміум активний до: " + premium.expiration_date.strftime("%Y-%m-%d %H:%M"))
    else:
        await send_message(chat_id, "У вас немає активного преміуму.")
    session.close()
    return {"ok": True}


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
