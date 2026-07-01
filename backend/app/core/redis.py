import logging
from typing import Optional, Set
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        # In-memory fallback if Redis is unavailable (useful for local development without Redis running)
        self._in_memory_blacklist: Set[str] = set()
        self._client: Optional[aioredis.Redis] = None
        self._connected = False
        
        # Replace hostname 'redis' with 'localhost' if running locally outside docker and 'redis' is not resolvable
        if "redis://redis:" in self.redis_url:
            # We will attempt to connect to redis, but we will catch connection errors and handle fallback
            pass

    def get_client(self) -> Optional[aioredis.Redis]:
        if not self._client and not self._connected:
            try:
                url = self.redis_url
                self._client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
                self._connected = True
                logger.info("Connected to Redis successfully.")
            except Exception as e:
                if settings.ENVIRONMENT.lower() == "production":
                    logger.error(f"Failed to connect to Redis in production: {e}")
                    raise e
                logger.warning(f"Failed to connect to Redis at {self.redis_url}: {e}. Using in-memory fallback.")
                self._client = None
                self._connected = False
        return self._client

    async def is_blacklisted(self, token_jti: str) -> bool:
        """Check if a token JTI is in the blacklist"""
        client = self.get_client()
        if client:
            try:
                exists = await client.exists(f"blacklist:{token_jti}")
                return exists > 0
            except Exception as e:
                if settings.ENVIRONMENT.lower() == "production":
                    logger.error(f"Redis operation failed (is_blacklisted) in production: {e}")
                    raise e
                logger.error(f"Redis operation failed (is_blacklisted): {e}. Falling back to in-memory.")
        else:
            if settings.ENVIRONMENT.lower() == "production":
                raise RuntimeError("Redis client is unavailable in production")
        return token_jti in self._in_memory_blacklist

    async def blacklist_token(self, token_jti: str, expire_seconds: int) -> None:
        """Blacklist a token JTI for a specific duration"""
        client = self.get_client()
        if client:
            try:
                await client.setex(f"blacklist:{token_jti}", expire_seconds, "1")
                return
            except Exception as e:
                if settings.ENVIRONMENT.lower() == "production":
                    logger.error(f"Redis operation failed (blacklist_token) in production: {e}")
                    raise e
                logger.error(f"Redis operation failed (blacklist_token): {e}. Falling back to in-memory.")
        else:
            if settings.ENVIRONMENT.lower() == "production":
                raise RuntimeError("Redis client is unavailable in production")
        self._in_memory_blacklist.add(token_jti)

    async def set_token_data(self, key: str, value: str, expire_seconds: int) -> None:
        """Set custom token data (e.g. for email verification or password reset)"""
        client = self.get_client()
        if client:
            try:
                await client.setex(key, expire_seconds, value)
                return
            except Exception as e:
                if settings.ENVIRONMENT.lower() == "production":
                    logger.error(f"Redis operation failed (set_token_data) in production: {e}")
                    raise e
                logger.error(f"Redis operation failed (set_token_data): {e}.")
        else:
            if settings.ENVIRONMENT.lower() == "production":
                raise RuntimeError("Redis client is unavailable in production")
        
        if not hasattr(self, "_in_memory_kv"):
            self._in_memory_kv = {}
        self._in_memory_kv[key] = value

    async def get_token_data(self, key: str) -> Optional[str]:
        """Get custom token data"""
        client = self.get_client()
        if client:
            try:
                val = await client.get(key)
                return val
            except Exception as e:
                if settings.ENVIRONMENT.lower() == "production":
                    logger.error(f"Redis operation failed (get_token_data) in production: {e}")
                    raise e
                logger.error(f"Redis operation failed (get_token_data): {e}.")
        else:
            if settings.ENVIRONMENT.lower() == "production":
                raise RuntimeError("Redis client is unavailable in production")
                
        if hasattr(self, "_in_memory_kv"):
            return self._in_memory_kv.get(key)
        return None

    async def delete_token_data(self, key: str) -> None:
        """Delete custom token data"""
        client = self.get_client()
        if client:
            try:
                await client.delete(key)
                return
            except Exception as e:
                if settings.ENVIRONMENT.lower() == "production":
                    logger.error(f"Redis operation failed (delete_token_data) in production: {e}")
                    raise e
                logger.error(f"Redis operation failed (delete_token_data): {e}.")
        else:
            if settings.ENVIRONMENT.lower() == "production":
                raise RuntimeError("Redis client is unavailable in production")
                
        if hasattr(self, "_in_memory_kv") and key in self._in_memory_kv:
            del self._in_memory_kv[key]

redis_service = RedisService()
