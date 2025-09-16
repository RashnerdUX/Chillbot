import logging
import os
from dotenv import load_dotenv
load_dotenv()
from telethon import TelegramClient, events

logging.basicConfig(format='[%(levelname) %(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

client = TelegramClient('session_name', API_ID, API_HASH)

@client.on(events.NewMessage(chats="JoshuaForex Academy"))
async def handler(event):
    logger.info(f"New message in JoshuaForex Academy: {event.message.message}")

with client:
    client.start()
    logger.info("Client started. Listening for new messages...")
    client.run_until_disconnected()