import os
import requests
from flask import Flask
from threading import Thread
import logging

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

# Simple bot function
def run_bot():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("No token, bot not starting")
        return
    
    print(f"Bot would start with token: {TOKEN[:10]}...")
    # Bot code would go here

if __name__ == '__main__':
    # Start bot in background
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
