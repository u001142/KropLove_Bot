from fastapi import APIRouter, Request
from app.database import SessionLocal
from app.models.match import Match
from app.config import BOT_TOKEN
import httpx

router = APIRouter()

# Зберігаємо чат-сесії у памʼяті (можна замінити на БД, якщо потрібно)
active_chats = {}

@router.post("/chat")
async def handle_chat(request: Request):
    data = await request.json()
    message = data.get("message")

    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Команда зупинки чату
    if text.lower() == "/stop":
        if chat_id in active_chats:
            partner_id = active_chats.pop(chat_id)
            active_chats.pop(partner_id, None)

            await send_message(chat_id, "Чат завершено.")
            await send_message(partner_id, "Співрозмовник завершив чат.")
        else:
            await send_message(chat_id, "У вас немає активного чату.")
        return {"ok": True}

    # Якщо чат активний — надсилаємо партнеру
    if chat_id in active_chats:
        partner_id = active_chats[chat_id]
        await send_message(partner_id, f"Від співрозмовника: {text}")
    else:
        await send_message(chat_id, "Наразі у вас немає активного чату.")

    return {"ok": True}


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )


# Функція для запуску чату (викликається при взаємній симпатії)
def start_chat(user1_id: int, user2_id: int):
    active_chats[user1_id] = user2_id
    active_chats[user2_id] = user1_id
