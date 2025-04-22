# Список Telegram ID, які мають адмін-доступ
ADMINS = [5347187083]  # ← Вкажи свій Telegram ID

# Команда /admin — перевірка доступу
if text == "/admin":
    if chat_id not in ADMINS:
        await send_message(chat_id, "⛔️ У вас немає доступу.")
        return {"ok": True}
    await send_message(chat_id, "✅ Вітаю, адміністраторе!")
    return {"ok": True}

# Команда /list — список останніх 10 юзерів
if text == "/list":
    if chat_id not in ADMINS:
        await send_message(chat_id, "⛔️ У вас немає доступу.")
        return {"ok": True}
    with SessionLocal() as session:
        users = session.query(User).order_by(User.id.desc()).limit(10).all()
        if not users:
            await send_message(chat_id, "База порожня.")
        else:
            for user in users:
                await send_message(
                    chat_id,
                    f"{user.name}, {user.age} років, {user.city}\nTelegram ID: {user.telegram_id}"
                )
    return {"ok": True}

# Команда /delete <telegram_id>
if text.startswith("/delete"):
    if chat_id not in ADMINS:
        await send_message(chat_id, "⛔️ У вас немає доступу.")
        return {"ok": True}
    parts = text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await send_message(chat_id, "⚠️ Використання: /delete <telegram_id>")
        return {"ok": True}
    target_id = int(parts[1])
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=target_id).first()
        if not user:
            await send_message(chat_id, "Користувача не знайдено.")
        else:
            session.delete(user)
            session.commit()
            await send_message(chat_id, f"✅ Користувача {target_id} видалено.")
    return {"ok": True}