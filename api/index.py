import os
import json
import logging
import requests
from flask import Flask, request, Response
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
VERCEL_URL = os.getenv('VERCEL_URL')  # Vercel deployment URL
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Optional custom forwarding URL

app = Flask(__name__)

def send_telegram_message(chat_id, text):
    """Send a message via Telegram bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set, cannot send message")
        return False

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(
            telegram_url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Message sent to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")
        return False

def get_final_webhook_url():
    """Return the webhook URL for Telegram."""
    if not VERCEL_URL:
        logger.error("VERCEL_URL not set, cannot determine webhook URL")
        return None
    return f"https://{VERCEL_URL}/api/webhook"

def set_telegram_webhook():
    """Set Telegram webhook to use the Vercel URL."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set")
        return False

    webhook_url = get_final_webhook_url()
    if not webhook_url:
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": webhook_url},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        if result.get("ok"):
            logger.info(f"Webhook set successfully: {webhook_url}")
            return True
        else:
            logger.error(f"Failed to set webhook: {result}")
            return False
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return False

@app.route('/')
def home():
    """Health check endpoint."""
    return {
        "status": "ok",
        "telegram_token_set": bool(TELEGRAM_TOKEN),
        "vercel_url_set": bool(VERCEL_URL)
    }

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    logger.info("Received webhook call")
    try:
        update = request.get_json()
        logger.info(f"Update: {json.dumps(update, indent=2)}")

        if not update or 'message' not in update:
            logger.warning("Update has no message")
            return Response(status=200)

        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text')

        if not text:
            send_telegram_message(chat_id, "❌ Sorry, I can only process text messages.")
            return Response(status=200)

        user = message.get('from', {})
        payload = {
            'message_id': message.get('message_id'),
            'chat_id': chat_id,
            'text': text,
            'date': message.get('date'),
            'from_user': {
                'id': user.get('id'),
                'username': user.get('username'),
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name')
            }
        }

        # Forward to optional custom webhook URL
        forward_url = WEBHOOK_URL or get_final_webhook_url()
        if forward_url:
            try:
                resp = requests.post(forward_url, json=payload, timeout=10)
                resp.raise_for_status()
                send_telegram_message(chat_id, "✅ Message successfully forwarded!")
            except requests.exceptions.RequestException as e:
                logger.error(f"Forwarding failed: {str(e)}")
                send_telegram_message(chat_id, "❌ Failed to forward your message.")
        else:
            logger.warning("No webhook URL available to forward message")

    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
        logger.exception("Full traceback:")
        try:
            chat_id = update.get('message', {}).get('chat', {}).get('id')
            if chat_id:
                send_telegram_message(chat_id, "❌ An unexpected error occurred.")
        except:
            pass

    return Response(status=200)

@app.route('/api/test', methods=['GET'])
def test():
    """Send a test message."""
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return {"error": "chat_id parameter required"}, 400

    success = send_telegram_message(chat_id, "🔄 Test message from bot")
    return {
        "success": success,
        "message": "Test message sent" if success else "Failed to send test message"
    }

@app.route('/api/set_webhook', methods=['GET'])
def api_set_webhook():
    """Manually trigger webhook setup."""
    success = set_telegram_webhook()
    return {"success": success}

# Automatically set webhook on Vercel
if os.getenv("VERCEL") == "1":
    set_telegram_webhook()

if __name__ == '__main__':
    app.run()
