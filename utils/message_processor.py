from models import TokenAlert
import instructor
from datetime import datetime
from openai import OpenAI
import logging

class MessageProcessor:
    """
    MessageProcessor class to handle processing of messages and generating TokenAlert instances.
    """
    def __init__(self):
        self.client = instructor.from_openai(OpenAI())
        self.logger = logging.getLogger(__name__)

    def extract_contract_address(self, message_text: str, source_chat: str) -> TokenAlert | None:
        alert = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=TokenAlert,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at parsing chat messages to find token alerts. Extract the contract address and the message text. If no address is found, do not return a response.",
                },
                {
                    "role": "user",
                    "content": f"The raw chat message: '{message_text}' \nSource Chat ID: {source_chat} \nTimestamp: {datetime.now()} \n Confidence Score: 0.0",
                },
            ],
        )
        if alert.contract_address:
            self.logger.info(f"Extracted contract address: {alert.contract_address}")
            # TODO: Add a background call to open a position on the contract address
            return alert
        else:
            self.logger.info("No contract address found in the message.")
            return None

if __name__ == "__main__":
    processor = MessageProcessor()
    test_message = "New token launch! Check out the contract at 0x1234567890abcdef1234567890abcdef12345678"
    alert = processor.extract_contract_address(test_message, "TestChat")
    if alert:
        print(f"Extracted Alert: {alert}")
    else:
        print("No alert extracted.")