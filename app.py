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

# Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Telegram Social Downloader Bot is Running!"

@flask_app.route('/health')
def health():
    return {"status": "healthy"}, 200

@flask_app.route('/ping')
def ping():
    return "pong", 200

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "https://socialdownloder2.anshapi.workers.dev/"

# Initialize Telegram Bot
application = Application.builder().token(TOKEN).build()

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
👋 Welcome *{user.first_name}*!

🤖 *Social Media Downloader Bot*

Send me any social media URL to download content!
Supported: YouTube, Instagram, Facebook, Twitter/X, TikTok, etc.
"""
    
    keyboard = [
        [InlineKeyboardButton("📸 Instagram", callback_data='help_instagram'),
         InlineKeyboardButton("🎬 YouTube", callback_data='help_youtube')],
        [InlineKeyboardButton("📘 Facebook", callback_data='help_facebook'),
         InlineKeyboardButton("🐦 Twitter/X", callback_data='help_twitter')],
        [InlineKeyboardButton("🎵 TikTok", callback_data='help_tiktok')]
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
            "Please send a valid social media URL to download.\nExample: https://www.youtube.com/watch?v=..."
        )

async def process_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    processing_msg = await update.message.reply_text(
        f"🔄 Processing your URL...",
        parse_mode='Markdown'
    )
    
    try:
        # Call the API
        params = {'url': url}
        response = requests.get(API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            await processing_msg.edit_text(
                f"✅ Download link ready!\n\n"
                f"Click here: {response.text[:200]}...\n\n"
                f"Or visit: {API_URL}?url={url}"
            )
        else:
            await processing_msg.edit_text(
                f"❌ Could not download. Status: {response.status_code}\n\n"
                f"Try another URL or try again later."
            )
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text(
            f"❌ Error: {str(e)[:100]}..."
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
            'twitter': '🐦 Twitter/X',
            'tiktok': '🎵 TikTok'
        }
        await query.edit_message_text(
            f"Send any {platform_names.get(platform, platform)} URL to download!"
        )

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(button_callback))

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def main():
    # Check token
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    # Start Flask in background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
