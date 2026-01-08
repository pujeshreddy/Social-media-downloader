import os
import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from urllib.parse import urlparse
import re
from flask import Flask, render_template
import threading
import asyncio

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
    return {"status": "healthy", "service": "telegram-bot"}, 200

@flask_app.route('/ping')
def ping():
    return "pong", 200

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "https://socialdownloder2.anshapi.workers.dev/"

# Supported platforms
PLATFORMS = {
    'youtube': '🎬 YouTube',
    'instagram': '📸 Instagram',
    'facebook': '📘 Facebook',
    'twitter': '🐦 Twitter/X',
    'tiktok': '🎵 TikTok',
    'snapchat': '👻 Snapchat',
    'pinterest': '📌 Pinterest',
    'linkedin': '💼 LinkedIn',
    'reddit': '📱 Reddit',
    'threads': '🧵 Threads',
    'rumble': '🎥 Rumble',
    'twitch': '🟣 Twitch',
    'dailymotion': '🎞️ Dailymotion',
    'vimeo': '🎥 Vimeo'
}

# Initialize Telegram Bot
application = Application.builder().token(TOKEN).build()

# Bot Handlers (same as before)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_text = f"""
👋 Welcome *{user.first_name}*!

🤖 *Social Media Downloader Bot*

I can download content from various social media platforms including:
• YouTube (Videos, Shorts, Playlists)
• Instagram (Reels, Posts, Stories)
• Facebook (Videos, Reels)
• Twitter/X (Videos, GIFs)
• TikTok Videos
• Snapchat Spotlight
• And many more...
"""
    
    keyboard = [
        [InlineKeyboardButton("🎬 YouTube", callback_data='help_youtube'),
         InlineKeyboardButton("📸 Instagram", callback_data='help_instagram')],
        [InlineKeyboardButton("📘 Facebook", callback_data='help_facebook'),
         InlineKeyboardButton("🐦 Twitter/X", callback_data='help_twitter')],
        [InlineKeyboardButton("🎵 TikTok", callback_data='help_tiktok'),
         InlineKeyboardButton("👻 Snapchat", callback_data='help_snapchat')],
        [InlineKeyboardButton("📌 How to Use", callback_data='usage_info')],
        [InlineKeyboardButton("📋 All Platforms", callback_data='all_platforms')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
📖 *Bot Commands*

/start - Start the bot
/help - Show help message
/download <url> - Download from URL
/platforms - List supported platforms

*Simply send any social media URL to download it!*
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def platforms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all supported platforms."""
    platforms_text = "📱 *Supported Platforms:*\n\n"
    for key, value in PLATFORMS.items():
        platforms_text += f"• {value}\n"
    
    await update.message.reply_text(platforms_text, parse_mode='Markdown')

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /download command."""
    if context.args:
        url = ' '.join(context.args)
        await process_url(update, context, url)
    else:
        await update.message.reply_text(
            "📥 *Send a URL to download*\n\nExample: `/download https://www.youtube.com/watch?v=...`",
            parse_mode='Markdown'
        )

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
            "Please send a valid social media URL to download.\nExample: https://www.youtube.com/watch?v=..."
        )

def extract_url_info(url):
    """Extract platform from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    domain_map = {
        'youtube.com': 'youtube',
        'youtu.be': 'youtube',
        'instagram.com': 'instagram',
        'fb.watch': 'facebook',
        'facebook.com': 'facebook',
        'twitter.com': 'twitter',
        'x.com': 'twitter',
        'tiktok.com': 'tiktok',
        'snapchat.com': 'snapchat',
        'pinterest.com': 'pinterest',
        'linkedin.com': 'linkedin',
        'reddit.com': 'reddit',
        'threads.net': 'threads',
        'rumble.com': 'rumble',
        'twitch.tv': 'twitch',
        'dailymotion.com': 'dailymotion',
        'vimeo.com': 'vimeo'
    }
    
    for key, platform in domain_map.items():
        if key in domain:
            return platform
    
    return 'unknown'

async def process_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Process the URL and download content."""
    processing_msg = await update.message.reply_text(
        f"🔄 *Processing...*\n\nURL: `{url[:50]}...`\n\nFetching content...",
        parse_mode='Markdown'
    )
    
    try:
        platform = extract_url_info(url)
        
        if platform == 'unknown':
            await processing_msg.edit_text(
                "❌ *Unsupported Platform*\n\nThis URL is not from a supported platform.\nUse /platforms to see all supported platforms."
            )
            return
        
        # Call the API
        params = {'url': url}
        response = requests.get(API_URL, params=params, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"API returned status {response.status_code}")
        
        # Try to parse response
        try:
            data = response.json()
            
            if 'url' in data or 'downloadUrl' in data or 'video_url' in data:
                download_url = data.get('url') or data.get('downloadUrl') or data.get('video_url')
                
                keyboard = [
                    [InlineKeyboardButton("⬇️ Download Now", url=download_url)],
                    [InlineKeyboardButton("🔄 Try Another", callback_data=f'retry_{url}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_msg.edit_text(
                    f"✅ *Download Ready!*\n\n"
                    f"*Platform:* {PLATFORMS.get(platform, platform.title())}\n"
                    f"Click the button below to download:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            else:
                # Direct download if response is a file
                await processing_msg.edit_text("✅ Content found! Sending to you...")
                # For simplicity, send the URL if no direct download
                await update.message.reply_text(
                    f"Download link: {response.text[:400]}..."
                )
                
        except json.JSONDecodeError:
            # If response is not JSON, might be direct URL
            await processing_msg.edit_text(f"Direct download: {response.text[:200]}...")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text(
            f"❌ *Error*\n\nCould not download this content.\nError: {str(e)[:100]}...\n\nTry another URL or try again later."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('help_'):
        platform = data[5:]
        platform_name = PLATFORMS.get(platform, platform.title())
        await query.edit_message_text(
            f"ℹ️ *{platform_name} Support*\n\nSend any {platform_name} URL to download content!\n\nExamples:\n• Videos\n• Reels/Shorts\n• Posts\n\nJust copy and paste the URL!"
        )
    elif data == 'usage_info':
        await query.edit_message_text(
            "📝 *How to Use*\n\n1. Find a video/reel/post on any social media\n2. Copy the URL\n3. Paste it here\n4. Get download link!\n\nThat's it! 🎉"
        )
    elif data == 'all_platforms':
        platforms_text = "📱 *All Supported Platforms:*\n\n"
        for key, value in PLATFORMS.items():
            platforms_text += f"• {value}\n"
        await query.edit_message_text(platforms_text)
    elif data.startswith('retry_'):
        url = data[6:]
        await process_url(update, context, url)

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("download", download_command))
application.add_handler(CommandHandler("platforms", platforms_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(button_callback))

def run_flask():
    """Run Flask web server."""
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

async def run_bot():
    """Run Telegram bot."""
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep running
    await asyncio.Event().wait()

def main():
    """Main function to start both services."""
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("Flask server started")
    
    # Run bot in main thread
    asyncio.run(run_bot())

if __name__ == '__main__':
    # Check if token is set
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        logger.info("Please set it in Render environment variables")
        exit(1)
    
    logger.info("Starting Social Media Downloader Bot...")
    main()