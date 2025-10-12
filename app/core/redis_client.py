"""Redis client for state management"""
import json
import redis
from typing import Optional, Any
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis client for conversation state management"""

    def __init__(self):
        self._client = None
        self._connect()

    def _connect(self):
        """Connect to Redis with retry logic"""
        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self._client.ping()
            logger.info(f"✓ Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {str(e)}")
            raise

    @property
    def client(self):
        """Get Redis client with connection check"""
        try:
            self._client.ping()
            return self._client
        except:
            logger.warning("Redis connection lost, reconnecting...")
            self._connect()
            return self._client

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        try:
            ttl = ttl or settings.REDIS_TTL
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {str(e)}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {str(e)}")
            return False

    def set_conversation(self, session_id: str, conversation_data: dict) -> bool:
        """Store conversation data"""
        key = f"quotebot:conversation:{session_id}"
        return self.set(key, conversation_data)

    def get_conversation(self, session_id: str) -> Optional[dict]:
        """Get conversation data"""
        key = f"quotebot:conversation:{session_id}"
        return self.get(key)

    def delete_conversation(self, session_id: str) -> bool:
        """Delete conversation"""
        key = f"quotebot:conversation:{session_id}"
        return self.delete(key)


# Singleton instance
redis_client = RedisClient()
