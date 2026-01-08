web: gunicorn app:flask_app --bind 0.0.0.0:$PORT --worker-class gevent --timeout 120
worker: python -c "from app import application; import asyncio; asyncio.run(application.run_polling())"