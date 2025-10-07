import redis.asyncio as redis
from typing import Optional
import logging


# Initialize logger
logger = logging.getLogger(__name__)

class RedisManager:
    """Single Redis connection manager"""

    # Here I'll store the global variable names for the data the global application needs
    SOL_PRICE_KEY = "SOLANA_PRICE" #This is for storing the current value of solana
    SOL_PRICE_EXPIRY = 30 #Clear the cache after 30 secs


    def __init__(self):
        self.client: redis.Redis = None
    
    async def connect(self, url: str = "redis://localhost:6379"):
        """Initialize Redis connection"""
        try:
            print("Connecting to Redis server...")
            self.client = await redis.from_url(
                url,
                encoding="utf-8",
                decode_responses=True
            )
            connected = await self.client.ping()
            if connected:
                logger.debug(f"Is Redis client connected? {connected}")
                logger.debug("Received a pong from Redis Manager")
            logger.info("✓ Redis connected")
        except Exception as e:
            print(f"An error occured {e}")
            logger.exception("Error connecting with Redis")
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("✓ Redis disconnected")
    
    def get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        if not self.client:
            logger.critical("Redis not initialized. Connect ASAP")
            raise RuntimeError("Redis not initialized. Call connect() first.")
        return self.client

# Global instance
redis_manager = RedisManager()

if __name__ == "__main__":
    import asyncio

    async def main():
        print("Starting up the Redis server...")
        await redis_manager.connect()
        r = redis_manager.get_client()

        # Testing the server
        print("Redis server is up and active.")
        print("Caching a variable...")
        await r.set("Back", "Milkshake", 30)
        var = await r.get("Back")
        print (f"Here's the cached variable - {var}")

        # Sleep past expiry
        await asyncio.sleep(35)

        # Try accessing the variable again
        print("The variable should be expired now and so should return none")
        var = await r.get("Back")
        print (f"Here's the cached variable again - {var}")

    asyncio.run(main())


    