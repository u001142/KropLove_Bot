import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from dotenv import load_dotenv
import database
import openai_api

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
application = Application.builder().token(TOKEN).build()

BRANDS = [
    "Lada", "Daewoo", "ZAZ", "Renault", "Chevrolet", "Volkswagen",
    "Opel", "Peugeot", "Ford", "Fiat", "Hyundai", "Kia",
    "Chery", "Geely", "Mazda", "Nissan", "Toyota", "BMW", "Mercedes", "Audi"
]

USER_STATE = {}

@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{WEBHOOK_SECRET}")

@app.post("/{secret}")
async def webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return {"status": "forbidden"}
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Українська", callback_data="lang_uk")],
        [InlineKeyboardButton("English", callback_data="lang_en")]
    ]
    await update.message.reply_text("Оберіть мову / Choose language:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    database.set_user_language(user_id, lang)
    USER_STATE[user_id] = {"lang": lang, "step": "brand"}
    
    buttons = []
    row = []
    for i, brand in enumerate(BRANDS, 1):
        row.append(InlineKeyboardButton(brand, callback_data=f"brand_{brand}"))
        if i % 3 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await query.message.reply_text(
        "Оберіть марку авто:" if lang == "uk" else "Select your car brand:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    brand = query.data.split("_")[1]
    USER_STATE[user_id] = {"brand": brand, "step": "model", "lang": database.get_user_language(user_id)}
    await query.message.reply_text("Введіть модель авто:" if USER_STATE[user_id]["lang"] == "uk" else "Enter car model:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    lang = database.get_user_language(user_id) or "uk"

    if user_id not in USER_STATE:
        await update.message.reply_text("Натисніть /start." if lang == "uk" else "Please press /start.")
        return

    state = USER_STATE[user_id]

    if state["step"] == "model":
        state["model"] = text
        state["step"] = "year"
        await update.message.reply_text("Введіть рік випуску:" if lang == "uk" else "Enter year of production:")

    elif state["step"] == "year":
        state["year"] = text
        state["step"] = "engine"
        await update.message.reply_text("Введіть обʼєм двигуна (наприклад: 1.6):" if lang == "uk" else "Enter engine volume (e.g. 1.6):")

    elif state["step"] == "engine":
        state["engine"] = text
        full_car = f"{state['brand']} {state['model']} {state['year']} {state['engine']}L"
        database.set_user_car(user_id, full_car)
        USER_STATE.pop(user_id)

        await update.message.reply_text(
            f"Ваше авто збережено: {full_car}" if lang == "uk"
            else f"Your car has been saved: {full_car}"
        )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id) or "uk"
    car = database.get_user_car(user_id)
    if not car:
        await update.message.reply_text("Будь ласка, спочатку оберіть авто через /start." if lang == "uk" else "Please choose your car first with /start.")
        return

    if not database.is_premium(user_id):
        count = database.increment_and_get_ask_count(user_id)
        if count > 3:
            await update.message.reply_text("Ви вичерпали безкоштовний ліміт. Активуйте /premium." if lang == "uk" else "You reached your free limit. Use /premium.")
            return

    question = update.message.text.replace("/ask", "").strip()
    if not question:
        await update.message.reply_text("Введіть запит після /ask." if lang == "uk" else "Enter your question after /ask.")
        return

    if lang == "uk":
        prompt = f"Користувач задає питання про авто: {car}\nПитання: {question}\nДай докладну відповідь українською."
    else:
        prompt = f"User is asking about: {car}\nQuestion: {question}\nReply in English."

    answer = openai_api.ask_ai(prompt)
    await update.message.reply_text(answer)

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id) or "uk"
    database.set_premium(user_id)
    await update.message.reply_text("Преміум активовано! Без обмежень." if lang == "uk" else "Premium activated! Unlimited access.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ask", ask))
application.add_handler(CommandHandler("premium", premium))
application.add_handler(CallbackQueryHandler(handle_language, pattern="^lang_"))
application.add_handler(CallbackQueryHandler(handle_brand, pattern="^brand_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
