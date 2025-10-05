from decimal import Decimal
from redis import Redis
import logging

# TODO:Get the global logger and Redis client
logger = logging.getLogger(__name__)
redis_client = Redis()

def determine_usd_price(sol_price: Decimal) -> Decimal:
    """
    Convert the Sol price to a usd price. This helper function is useful for 

    Args:
        sol_price (Decimal): The price of a token in its sol format

    Returns:
        Decimal: The value in USD based on the current price of SOL
    """
    try:
        # First retrieve the solana price in cache
        current_solana_price = redis_client.get("SOLANA_PRICE")

        # Check if it is in cache
        if current_solana_price is None:
            logger.warning("SOL/USD price not found in cache")
            raise ValueError("SOL/USD price not available in cache. Check if the WebSocket is running")

        # Convert for calculation
        solana_price = Decimal(current_solana_price)
        usd_price = solana_price * sol_price

        return usd_price
    
    except Exception as e:
        logger.error(f"An unexpected error occured converting to sol. {e}")
        return 0