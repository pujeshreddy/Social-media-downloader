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
import asyncio

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for health checks
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

# Initialize Telegram Bot
application = None
if TOKEN:
    application = Application.builder().token(TOKEN).build()
    logger.info("Telegram bot application initialized")
else:
    logger.warning("TELEGRAM_BOT_TOKEN not set!")

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
👋 Welcome *{user.first_name}*!

🤖 *Social Media Downloader Bot*

Send me any social media URL to download content!
Supported platforms: YouTube, Instagram, Facebook, Twitter/X, TikTok, etc.

📌 *How to use:*
1. Send me a URL from any social media
2. I'll process it
3. Get your download link!

Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = """
🤖 *Social Media Downloader Bot*

*Supported Platforms:*
• YouTube (Videos, Shorts, Playlists)
• Instagram (Reels, Posts, Stories)
• Facebook (Videos, Reels)
• Twitter/X (Videos, GIFs)
• TikTok Videos
• Snapchat Spotlight
• And many more...

*How to use:*
Simply send me any social media URL!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages containing URLs."""
    message_text = update.message.text
    
    # Check if message contains URL
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, message_text)
    
    if urls:
        url = urls[0]
        await process_url(update, context, url)
    else:
        await update.message.reply_text(
            "Please send a valid social media URL to download.\n\n"
            "Example: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`",
            parse_mode='Markdown'
        )

async def process_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Process the URL and download content."""
    # Show processing message
    processing_msg = await update.message.reply_text(
        "🔄 *Processing your request...*\n\n"
        f"URL: `{url[:50]}...`\n\n"
        "Please wait while I fetch the content...",
        parse_mode='Markdown'
    )
    
    try:
        # Call the API
        params = {'url': url}
        response = requests.get(API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            # Try to parse JSON response
            try:
                data = response.json()
                if 'url' in data:
                    download_url = data['url']
                elif 'downloadUrl' in data:
                    download_url = data['downloadUrl']
                elif 'video_url' in data:
                    download_url = data['video_url']
                else:
                    download_url = response.text[:200]
            except:
                download_url = response.text[:200]
            
            # Create inline keyboard with download button
            keyboard = [[InlineKeyboardButton("⬇️ Download Now", url=download_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                f"✅ *Download Ready!*\n\n"
                f"Click the button below to download:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await processing_msg.edit_text(
                f"❌ *Error*\n\n"
                f"Could not download this content.\n"
                f"Status Code: {response.status_code}\n\n"
                f"Try another URL or try again later."
            )
            
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        await processing_msg.edit_text(
            f"❌ *Error*\n\n"
            f"Could not process this URL.\n"
            f"Error: {str(e)[:100]}\n\n"
            f"Please try another URL."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
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
        platform_name = platform_names.get(platform, platform.title())
        await query.edit_message_text(
            f"ℹ️ *{platform_name} Support*\n\n"
            f"Send any {platform_name} URL to download content!\n\n"
            f"Examples:\n"
            f"• Videos\n"
            f"• Reels/Shorts\n"
            f"• Posts\n"
            f"• Stories\n\n"
            f"Just copy and paste the URL!",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def run_flask():
    """Run Flask web server."""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_bot():
    """Run Telegram bot in separate thread."""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set! Bot cannot start.")
        return
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("Starting Telegram bot polling...")
    application.run_polling()

def main():
    """Main function to start both services."""
    logger.info("Starting Social Media Downloader Bot...")
    
    # Check if token is set
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        logger.info("Please set it in Render environment variables")
        logger.info("Flask will still run for health checks, but bot won't start.")
    
    # Start Flask in main thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info(f"Flask server started on port {os.environ.get('PORT', 10000)}")
    
    # Start Telegram bot in current thread
    if TOKEN:
        run_bot()
    else:
        # If no token, just keep Flask running
        flask_thread.join()

if __name__ == '__main__':
    main()
