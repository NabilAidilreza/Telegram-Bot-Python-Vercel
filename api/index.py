import os
import requests
from flask import Flask, request, Response, jsonify
from dotenv import load_dotenv

from .utils.process_html import process_html

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

    msg = update['message']
    chat_id = msg['chat']['id']  # needed to reply
    text = msg.get('text')       # text message (or None)

    if not chat_id:
        return Response(status=200)

    if 'text' in msg:
        # user sent a normal message
        send_telegram(chat_id, f"You said: {msg['text']}")
    elif 'document' in msg and msg['document']['mime_type'] == 'text/html':
        # user sent an HTML file
        file_id = msg['document']['file_id']
        # download and process file
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
