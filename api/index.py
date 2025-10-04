import os
import requests
from flask import Flask, request, Response, jsonify
from dotenv import load_dotenv

from utils.process_html import process_html

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
VERCEL_URL = os.getenv('VERCEL_URL')

app = Flask(__name__)

# -------------------- Helper Functions --------------------

def send_telegram(chat_id, text):
    if not TELEGRAM_TOKEN:
        return False, "TELEGRAM_TOKEN not set"
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        resp.raise_for_status()
        return True, "Message sent"
    except Exception as e:
        return False, str(e)

def set_webhook():
    if not TELEGRAM_TOKEN or not VERCEL_URL:
        return False
    url = f"https://{VERCEL_URL}/api/webhook"
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": url}, timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("ok", False)
    except:
        return False
    
# -------------------- Routes --------------------

@app.route('/')
def home():
    if not TELEGRAM_TOKEN:
        return jsonify({"error": "TELEGRAM_TOKEN not set"}), 404
    if not VERCEL_URL:
        return jsonify({"error": "VERCEL_URL not set"}), 404
    return jsonify({"status": "ok"})

@app.route('/api/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update or 'message' not in update:
        return Response(status=200)

    msg = update.get('message', {})
    chat = msg.get('chat', {})
    chat_id = chat.get('id')

    if not chat_id:
        return Response(status=200)

    # Handle text messages
    if msg.get('text'):
        text = msg.get('text')
        # -------------------- DEVELOPMENT: text --------------------
        send_telegram(chat_id, f"💬 You said: {text}")
        # ------------------------------------------------------------

    # Handle HTML files sent as documents
    elif msg.get('document') and msg['document'].get('mime_type') == 'text/html':
        file_id = msg['document'].get('file_id')
        if file_id:
            # Get file path from Telegram
            resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}")
            file_path = resp.json().get('result', {}).get('file_path')
            if file_path:
                # Download file content
                file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                r = requests.get(file_url)
                html_content = r.text

                # -------------------- DEVELOPMENT: HTML --------------------
                length = process_html(html_content)  # Call your separate processor
                send_telegram(chat_id, f"HTML content length: {length}")
                # ------------------------------------------------------------

    else:
        send_telegram(chat_id, "❌ Unsupported message type.")

        return Response(status=200)

@app.route('/api/set_webhook', methods=['GET'])
def manual_webhook():
    return jsonify({"success": set_webhook()})

@app.route('/api/test', methods=['GET'])
def test():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({"error": "chat_id required"}), 400
    success, msg = send_telegram(chat_id, "🔄 Test message from bot")
    return jsonify({"success": success, "message": msg}) if success else (jsonify({"success": False, "message": msg}), 500)

# -------------------- Auto webhook setup --------------------
if os.getenv("VERCEL") == "1":
    set_webhook()

if __name__ == '__main__':
    app.run()
