import os
import json
import logging
import requests
from flask import Flask, request, Response
from dotenv import load_dotenv

# -------------------- Setup --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
VERCEL_URL = os.getenv('VERCEL_URL')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

app = Flask(__name__)

# -------------------- Helper Functions --------------------
def send_telegram_message(chat_id, text):
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False

def get_webhook_url():
    """Determine the URL for Telegram webhook."""
    return f"https://{VERCEL_URL}/api/webhook" if VERCEL_URL else None

def set_telegram_webhook():
    url = get_webhook_url()
    if not TELEGRAM_TOKEN or not url:
        logger.error("Cannot set webhook, missing TELEGRAM_TOKEN or VERCEL_URL")
        return False
    try:
        resp = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                             json={"url": url}, timeout=10)
        resp.raise_for_status()
        logger.info(f"Webhook set: {url}")
        return resp.json().get("ok", False)
    except Exception as e:
        logger.error(f"Webhook setup failed: {e}")
        return False

# -------------------- Routes --------------------
@app.route('/')
def home():
    return {"status": "ok", "telegram_set": bool(TELEGRAM_TOKEN), "webhook_url": WEBHOOK_URL}

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Main Telegram webhook handler."""
    try:
        update = request.get_json()
        if not update or 'message' not in update:
            return Response(status=200)

        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg.get('text')

        if not text:
            send_telegram_message(chat_id, "❌ Only text messages are supported.")
            return Response(status=200)

        # -------------------- BEGIN DEVELOPMENT HERE --------------------
        # Add your custom processing logic below
        # Example: echo back the received message
        send_telegram_message(chat_id, f"💬 You said: {text}")
        # -----------------------------------------------------------------

        # Forward to optional external webhook
        forward_url = WEBHOOK_URL or get_webhook_url()
        if forward_url:
            try:
                requests.post(forward_url, json=msg, timeout=10).raise_for_status()
            except Exception as e:
                logger.warning(f"Forwarding failed: {e}")

    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return Response(status=200)

@app.route('/api/set_webhook', methods=['GET'])
def manual_set_webhook():
    return {"success": set_telegram_webhook()}

@app.route('/api/test', methods=['GET'])
def test():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return {"error": "chat_id required"}, 400
    success = send_telegram_message(chat_id, "🔄 Test message from bot")
    return {"success": success}



# -------------------- Auto webhook setup --------------------
if os.getenv("VERCEL") == "1":
    set_telegram_webhook()

if __name__ == '__main__':
    app.run()
