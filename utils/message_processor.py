import instructor
from datetime import datetime
from openai import OpenAI
import logging
from dotenv import load_dotenv
from models.tokens import TokenAlert

load_dotenv()

class MessageProcessor:
    """
    MessageProcessor class to handle processing of messages and generating TokenAlert instances.
    """
    def __init__(self):
        self.client = instructor.from_provider("google/gemini-2.5-flash")
        self.logger = logging.getLogger(__name__)

    def extract_contract_address(self, message_text: str, source_chat: str) -> TokenAlert | None:
        alert = self.client.chat.completions.create(
            response_model=TokenAlert,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at parsing chat messages to find token alerts. Extract the contract address and the message text. If no address is found, do not return a response.",
                },
                {
                    "role": "user",
                    "content": f"The raw chat message: '{message_text}' \nSource Chat ID: {source_chat}",
                },
            ],
        )
        if alert.contract_address:
            self.logger.info(alert)
            self.logger.info(f"Extracted contract address: {alert.contract_address}")
            # TODO: Add a background call to open a position on the contract address
            return alert
        else:
            self.logger.info("No contract address found in the message.")
            return None

if __name__ == "__main__":
    print("Testing MessageProcessor...")
    processor = MessageProcessor()
    test_message = "New token launch! Check out the contract at V5cCiSixPLAiEDX2zZquT5VuLm4prr5t35PWmjNpump. Gamble wisely!"
    print("Running extract_contract_address...")
    alert = processor.extract_contract_address(test_message, "TestChat")
    print("Result:")
    if alert:
        print(f"Extracted Alert: {alert}")
    else:
        print("No alert extracted.")