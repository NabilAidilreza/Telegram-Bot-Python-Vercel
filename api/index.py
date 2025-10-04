import os
import json
import requests
from flask import Flask, request, Response, jsonify
from dotenv import load_dotenv

# -------------------- Setup --------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
VERCEL_URL = os.getenv('VERCEL_URL')

app = Flask(__name__)

# -------------------- Helper Functions --------------------
def send_telegram_message(chat_id, text):
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

def get_webhook_url():
    if not VERCEL_URL:
        return None
    return f"https://{VERCEL_URL}/api/webhook"

def set_telegram_webhook():
    url = get_webhook_url()
    if not TELEGRAM_TOKEN or not url:
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": url},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("ok", False)
    except Exception:
        return False

# -------------------- Routes --------------------
@app.route('/')
def home():
    if not TELEGRAM_TOKEN:
        return jsonify({"error": "TELEGRAM_TOKEN not set"}), 404
    if not VERCEL_URL:
        return jsonify({"error": "VERCEL_URL not set"}), 404
    return jsonify({"status": "ok", "telegram_set": True})

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if not update or 'message' not in update:
            return Response(status=200)  # Telegram expects 200

        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg.get('text')

        if not text:
            send_telegram_message(chat_id, "❌ Only text messages are supported.")
            return Response(status=200)

        # -------------------- BEGIN DEVELOPMENT HERE --------------------
        # Example: echo message back
        send_telegram_message(chat_id, f"💬 You said: {text}")
        # -----------------------------------------------------------------

        return Response(status=200)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/set_webhook', methods=['GET'])
def manual_set_webhook():
    success = set_telegram_webhook()
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False}), 500

@app.route('/api/test', methods=['GET'])
def test():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({"error": "chat_id required"}), 400

    success, message = send_telegram_message(chat_id, "🔄 Test message from bot")
    if success:
        return jsonify({"success": True, "message": message})
    return jsonify({"success": False, "message": message}), 500

# -------------------- Auto webhook setup --------------------
if os.getenv("VERCEL") == "1":
    set_telegram_webhook()

if __name__ == '__main__':
    app.run()
