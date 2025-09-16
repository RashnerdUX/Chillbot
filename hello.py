import os
import dotenv
from telethon import TelegramClient

dotenv.load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

print(f"Using API_ID: {API_ID}")
print(type(API_ID))

client = TelegramClient("session_name", API_ID, API_HASH)

with client:
    client.loop.run_until_complete(client.send_message("me", "Hello, Telegram! from Python"))