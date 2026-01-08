import os
import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from urllib.parse import urlparse
import re
from flask import Flask
from threading import Thread

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for health checks - MUST be named 'app' for gunicorn
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Social Downloader Bot is Running!"

@app.route('/health')
def health():
    return {"status": "healthy"}, 200

@app.route('/ping')
def ping():
    return "pong", 200

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "https://socialdownloder2.anshapi.workers.dev/"

# Initialize Telegram Bot (only if token exists)
if TOKEN:
    application = Application.builder().token(TOKEN).build()
else:
    application = None
    logger.warning("TELEGRAM_BOT_TOKEN not set!")

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
👋 Welcome *{user.first_name}*!

🤖 *Social Media Downloader Bot*

Send me any social media URL to download content!
"""
    
    keyboard = [
        [InlineKeyboardButton("📸 Instagram", callback_data='help_instagram'),
         InlineKeyboardButton("🎬 YouTube", callback_data='help_youtube')],
        [InlineKeyboardButton("📘 Facebook", callback_data='help_facebook'),
         InlineKeyboardButton("🐦 Twitter/X", callback_data='help_twitter')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    
    # Check if message contains URL
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, message_text)
    
    if urls:
        url = urls[0]
        await process_url(update, context, url)
    else:
        await update.message.reply_text(
            "Please send a valid social media URL.\nExample: https://www.youtube.com/watch?v=..."
        )

async def process_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    processing_msg = await update.message.reply_text(
        f"🔄 Processing...",
        parse_mode='Markdown'
    )
    
    try:
        # Call the API
        params = {'url': url}
        response = requests.get(API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            # Try to parse as JSON
            try:
                data = response.json()
                if 'url' in data:
                    download_url = data['url']
                else:
                    download_url = response.text[:200]  # First 200 chars
            except:
                download_url = response.text[:200]
            
            await processing_msg.edit_text(
                f"✅ *Download Ready!*\n\n"
                f"Click here: {download_url}\n\n"
                f"Or copy this link in your browser."
            )
        else:
            await processing_msg.edit_text(
                f"❌ Error: Status {response.status_code}\n\nTry another URL."
            )
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text(
            f"❌ Error downloading. Try again."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('help_'):
        platform = data[5:]
        platform_names = {
            'instagram': '📸 Instagram',
            'youtube': '🎬 YouTube', 
            'facebook': '📘 Facebook',
            'twitter': '🐦 Twitter/X'
        }
        await query.edit_message_text(
            f"Send any {platform_names.get(platform, platform)} URL to download!"
        )

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_bot():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set! Bot will not start.")
        return
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Starting Telegram bot...")
    application.run_polling()

def main():
    # Start Flask in main thread (required for Render)
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting Flask on port {port}")
    
    # Start bot in background thread
    if TOKEN:
        bot_thread = Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logger.info("Bot thread started")
    
    # Run Flask in main thread
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
