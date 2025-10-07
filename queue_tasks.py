from celery import Celery
from typing import Dict
from decimal import Decimal
from utils.token_validator import TokenValidator
import asyncio
import logging
from redis import Redis

from utils.okx_helper import access_okx_stream

# TODO: Replace with the Global logging class
logger = logging.getLogger(__name__)

# Initialize the Redis client and use the same
# TODO: Use the global Redis manager
redis_client = Redis()
# The key for solana's price in cache is SOLANA_PRICE


app = Celery('queue_tasks', broker='redis://localhost:6379/0')

# TODO: Set appropriate threshold values based on user's preferences and risk appetite
RISK_THRESHOLD = 0.7  # Example threshold for risk score

@app.task(bind=True, max_retries=3)
def process_token_alert(self, alert_data: Dict):
    """Process token alert through validation pipeline"""
    try:
        # Validate token
        validation_result = validate_token.delay(alert_data['contract_address'])
        
        if validation_result.get():
            # Check risk score
            risk_score = calculate_risk_score.delay(alert_data)
            
            if risk_score.get() < RISK_THRESHOLD:
                # Queue for trading
                execute_trade.delay(alert_data)
        
        logger.info("Successfully processed the alert")
        return {"status": "processed", "contract": alert_data['contract_address']}
    
    except Exception as exc:
        # Retry with exponential backoff
        logger.warning("Failed to process the data. Trying to process again")
        # TODO: Check this functionality and work it well
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@app.task
def execute_trade(contract_address: str):
    # Placeholder for logic to create a position on the given contract address
    print(f"Creating a position for contract address: {contract_address}")

@app.task
def validate_token(contract_address: str) -> bool:
    """Validate a token contract address.

    Args:
        contract_address (str): The contract address of the token to validate.

    Returns:
        bool: True if the token is valid, False otherwise.
    """
    try:
        validator = TokenValidator()
        validation_result = validator.validate_token(contract_address)
        is_valid = validation_result['is_valid']
        logger.info(f"Token {contract_address} validation result: {is_valid}")
        return is_valid
    except Exception as e:
        logger.warning(f"Failed to validate token {contract_address}")
        return False

@app.task
def calculate_risk_score(alert_data: Dict) -> float:
    """Calculate risk score for a token based on alert data.

    Args:
        alert_data (Dict): The alert data containing message text and other metadata.

    Returns:
        float: Risk score between 0 (low risk) and 1 (high risk).
    """
    validator = TokenValidator()
    risk_score = validator.calculate_risk_score(alert_data)
    return risk_score

@app.task
def save_sol_price():
    """
    The Solana Price Service
    Maintain the current price of Solana in Redis cache and make it available to all parts of the program at all times
    """
    logger.info("Starting the price stream from OKX which will update the Redis cache")
    
    try:
        asyncio.run(access_okx_stream(token_ticker="SOL"))
    except KeyboardInterrupt:
        logger.info("Shutting down SOL price stream...")
    except Exception as e:
        logger.exception(f"Fatal error in when saving the sol price: {e}")
        raise


