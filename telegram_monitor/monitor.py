from telethon import TelegramClient, events, utils
from telethon.tl.types import PeerChannel
import logging
from models.auth import TelegramChatID
from datetime import datetime
from utils.message_processor import MessageProcessor
from queue_tasks import process_token_alert


class ChatMonitor:
    """
    ChatMonitor class to monitor a specific Telegram channel for new messages.
    """
    def __init__(self, api_id, api_hash, phone_number:int=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.chat_ids: list[TelegramChatID] = []
        self.monitored_channels = []
        self.message_processor = MessageProcessor()
        self.client = TelegramClient('session-' + str(phone_number), api_id, api_hash)
        self.logger = logging.getLogger(__name__)

    async def start(self):
        # Start the TG client
        await self.client.start(phone=self.phone_number)

        # Get the user's chat IDs and let them pick which to monitor
        await self.get_user_chat_ids()
        await self.pick_monitored_channels()

        # Set up event handlers
        self.setup_handlers()

        # Run the client until disconnected and start monitoring
        print("Starting to monitor channels...")
        await self.client.run_until_disconnected()

    def setup_handlers(self):
        """ Set up event handlers for new messages in monitored channels """
        print("Setting up handlers...")
        @self.client.on(events.NewMessage(chats=self.monitored_channels))
        async def handle_new_message(event):
            # For debugging purposes, print the message
            self.logger.info(f"New message in {event.chat.title or event.chat_id}: {event.message.text[:100]}...")
            try:
                # Extract potential contract address from the message
                alert = self.message_processor.extract_contract_address(event.message.text, event.chat_id)

                if alert:
                    alert.source_chat = event.chat.title or str(event.chat_id)
                    alert.message_text = event.message.text[:500]
                    alert.timestamp = alert.timestamp.isoformat()
                    alert.confidence_score = self.calculate_confidence(event.message.text)

                    # Send alert to Celery for processing
                    self.process_alert(alert)
            except ValueError as e:
                self.logger.error(f"Failed to register handler: {e}")
            except Exception as e:
                self.logger.exception("Error processing message")
                self.message_processor.logger.error(f"Error processing message: {e}",
                    message_text=event.message.text[:500],
                    timestamp=datetime.now(),
                    confidence_score=self.calculate_confidence(event.message.text)
                )

    async def get_user_chat_ids(self):
        """ Fetch chat IDs for the channels that the user is a member of """
        try:
            dialogs = await self.client.get_dialogs()
            for dialog in dialogs:
                if dialog.is_channel and not dialog.is_group:
                    # TODO: Change the user_id to actual user ID from your auth system once integrated
                    real_chat_id, peer_type = utils.resolve_id(dialog.id)
                    chat_id = TelegramChatID(user_id=self.phone_number, chat_name=dialog.title, chat_id=real_chat_id)
                    self.chat_ids.append(chat_id)
            return self.chat_ids
        except Exception as e:
            logging.error(f"Error fetching user chat IDs: {e}")
            return []
    
    async def pick_monitored_channels(self):
        """ Allow user to pick which channels to monitor """
        print("Available Channels:")
        for idx, chat in enumerate(self.chat_ids):
            print(f"{idx + 1}. {chat.chat_name} (ID: {chat.chat_id})")
        
        # TODO: Clean this up for the backend. The selection should be done via the frontend.
        selected = input("Enter the id of the channel you want to monitor: ")
        # For debugging
        name_of_selected = input("Enter the name of the channel you want to monitor: ")
        self.logger.info(await self.client.get_peer_id(name_of_selected))
        self.monitored_channels.append(PeerChannel(int(selected)))

        print(f"Monitoring channels (ID only): {self.monitored_channels}")

    def calculate_confidence(self, message_text: str) -> float:
        # TODO: Implement a more sophisticated confidence scoring mechanism using data from dexscreener once the contract address is obtained. So something for the background task to handle.
        """Calculate confidence score based on keywords"""
        keywords = {
            'launch': 0.2, 'launching': 0.2, 'live': 0.15,
            'contract': 0.15, 'ca': 0.1, 'stealth': 0.15,
            'fair launch': 0.2, 'liquidity': 0.1, 'locked': 0.1,
            'renounced': 0.1, 'mint': 0.1, 'authority': 0.1
        }
        
        score = 0.0
        text_lower = message_text.lower()

        for keyword, weight in keywords.items():
            if keyword in text_lower:
                score += weight
        
        return min(score, 1.0)
    
    def process_alert(self, alert):
        try:
            # Convert alert to dict and queue the Celery task (fire-and-forget)
            task = process_token_alert.delay(alert.__dict__)
            
            # Log the queuing (with task ID for debugging/tracking)
            self.logger.info(f"Queued alert for processing: {alert.contract_address} (Task ID: {task.id})")
        except Exception as e:
            self.logger.exception(f"Failed to queue alert: {alert.contract_address}")
    
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_id = int(os.getenv("TELEGRAM_API_ID"))
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")

    monitor = ChatMonitor(api_id, api_hash, phone_number)
    import asyncio
    asyncio.run(monitor.start())