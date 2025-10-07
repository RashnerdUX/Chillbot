from okx.websocket.WsPublicAsync import WsPublicAsync
import logging
from services.chillbot_redis import redis_manager, RedisManager
from redis import Redis
import websockets
import json
from decimal import Decimal

logger = logging.getLogger(__name__)

# Initialize the Redis client
redis_client: Redis = redis_manager


def extract_token_price_from_okx_stream(data: dict):
    """
    Analyze and get the actual price from what produced. Save that to the redis cache for the program to access

    Args:
        data (dict): _description_
    """
    try:

        if "data" in data and len(data["data"]) > 0:
            logger.error(f"The data obtained from OKX doesn't have any price data.\n Here's the preview: {data}")

            # For now, it is for just solana so there's no need to check the token
            ticker_data = data.get("data")
            price = ticker_data["last"]

            # Once the data is gotten, store in the Global Redis cache
            redis_client.setex(
                RedisManager.SOL_PRICE_KEY,
                RedisManager.SOL_PRICE_EXPIRY,
                str(price)
            )
            logger.info(f"Updated SOL/USD price in Redis: ${price}")

        elif "event" in data and data["event"] == "subscribe":
            logger.info(f"The OKX stream for {data["arg"]["instId"]} is active and we can now get the price")
        
        elif "event" in data and data["event"] == "error":
            logger.error(f"The OKX stream couldn't be started because of {data["msg"]}")
        
        else:
            logger.info(f"Something unexpected as occured. Inspect the data for more info {data}")

    except Exception as e:
        logger.error(f"Failed to update Redis: {e}")

async def access_okx_stream(token_ticker:str):
    """
    This takes a token ticker and activates the okx websocket helper

    Args:
        token_ticker (str): _description_

    Returns:
        Decimal: _description_
    """

    uri = "wss://wspap.okx.com:8443/ws/v5/public"
    
    while True:
        websocket = None
        try:
            logger.info(f"Connecting to OKX WebSocket for {token_ticker}...")
            
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                
                logger.info("WebSocket connected successfully")
                
                subscribe_message = {
                    "op": "subscribe",
                    "args": [{
                        "channel": "tickers",
                        "instId": f"{token_ticker}-USDT"
                    }]
                }
                
                await websocket.send(json.dumps(subscribe_message))
                logger.info(f"Subscribed to {token_ticker}-USDT ticker")
                
                # Listen for the messages
                async for message in websocket:
                    try:
                        # For debugging
                        print(f"Here's the message - {message}")
                        data = json.loads(message)
                        extract_token_price_from_okx_stream(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e.code} - {e.reason}")
        
        except websockets.exceptions.WebSocketException as e:
            logger.exception(f"WebSocket exception: {e}")

        except Exception as e:
            logger.exception(f"An unexpected error occured. {e}")

async def get_current_sol_price() -> Decimal:
    """
    Get the current SOL/USD price from Redis cache.
    
    Returns:
        Decimal: Current SOL price in USD
        
    Raises:
        ValueError: If price is not available in cache
    """
    price = await redis_client.get(RedisManager.SOL_PRICE_KEY)
    if price is None:
        raise ValueError("SOL/USD price not available in cache")
    return Decimal(price)
