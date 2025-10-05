import redis.asyncio as redis
from typing import Optional

class RedisManager:
    """Single Redis connection manager"""
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self, url: str = "redis://localhost:6379"):
        """Initialize Redis connection"""
        self.client = await redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True
        )
        print("✓ Redis connected")
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            print("✓ Redis disconnected")
    
    def get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        if not self.client:
            raise RuntimeError("Redis not initialized. Call connect() first.")
        return self.client

# Global instance
redis_manager = RedisManager()