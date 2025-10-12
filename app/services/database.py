"""
Database Services: Redis and PostgreSQL
High-performance async database connections with pooling
"""

import redis.asyncio as aioredis
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, Integer, JSON, Text, text
from sqlalchemy.dialects.postgresql import UUID
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# REDIS CLIENT
# ============================================================================

class RedisClient:
    """Redis client with connection pooling"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Initialize Redis connection pool"""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_keepalive=settings.REDIS_SOCKET_KEEPALIVE,
        )
        logger.info("Redis connection pool created")

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    async def ping(self):
        """Test Redis connection"""
        if self.redis:
            return await self.redis.ping()
        return False

    # Conversation operations
    async def save_conversation(self, conversation_id: str, data: Dict[str, Any], ttl: int = None):
        """Save conversation data to Redis"""
        key = f"conversation:{conversation_id}"
        ttl = ttl or settings.CONVERSATION_TTL

        await self.redis.setex(
            key,
            ttl,
            json.dumps(data, default=str)
        )

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation data from Redis"""
        key = f"conversation:{conversation_id}"
        data = await self.redis.get(key)

        if data:
            return json.loads(data)
        return None

    async def update_conversation(self, conversation_id: str, updates: Dict[str, Any]):
        """Update conversation data"""
        key = f"conversation:{conversation_id}"
        existing = await self.get_conversation(conversation_id)

        if existing:
            existing.update(updates)
            await self.save_conversation(conversation_id, existing)

    async def delete_conversation(self, conversation_id: str):
        """Delete conversation from Redis"""
        key = f"conversation:{conversation_id}"
        await self.redis.delete(key)

    # Message operations
    async def add_message(self, conversation_id: str, message: Dict[str, Any]):
        """Add message to conversation history"""
        key = f"messages:{conversation_id}"
        await self.redis.rpush(key, json.dumps(message, default=str))
        await self.redis.expire(key, settings.CONVERSATION_TTL)

    async def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation"""
        key = f"messages:{conversation_id}"
        messages = await self.redis.lrange(key, 0, -1)

        return [json.loads(msg) for msg in messages]

    # Rate limiting
    async def check_rate_limit(self, identifier: str, limit: int = None) -> bool:
        """Check if rate limit is exceeded"""
        limit = limit or settings.RATE_LIMIT_PER_MINUTE
        key = f"rate_limit:{identifier}"

        count = await self.redis.incr(key)

        if count == 1:
            await self.redis.expire(key, 60)

        return count <= limit


# Initialize Redis client
redis_client = RedisClient()

# ============================================================================
# POSTGRESQL DATABASE
# ============================================================================

# Create database instance
database = Database(
    settings.DATABASE_URL,
    min_size=5,
    max_size=settings.DATABASE_POOL_SIZE,
)

# SQLAlchemy metadata
metadata = MetaData()

# Conversations table
conversations_table = Table(
    "conversations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("conversation_id", String(100), unique=True, nullable=False, index=True),
    Column("session_id", String(100), nullable=False, index=True),
    Column("dify_conversation_id", String(100)),
    Column("status", String(20), nullable=False, default="active", index=True),
    Column("initial_context", JSON, nullable=False),
    Column("final_output", JSON),
    Column("message_count", Integer, default=0),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("completed_at", DateTime),
)

# Messages table
messages_table = Table(
    "messages",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("message_id", String(100), unique=True, nullable=False),
    Column("conversation_id", String(100), nullable=False, index=True),
    Column("role", String(20), nullable=False),
    Column("content", Text, nullable=False),
    Column("dify_message_id", String(100)),
    Column("metadata", JSON),
    Column("created_at", DateTime, nullable=False, index=True),
)


class DatabaseService:
    """PostgreSQL database service"""

    @staticmethod
    async def create_tables():
        """Create database tables"""
        engine = create_engine(settings.DATABASE_URL)
        metadata.create_all(engine)
        logger.info("Database tables created/verified")

    @staticmethod
    async def save_conversation(data: Dict[str, Any]):
        """Save conversation to database"""
        # Generate UUID if not present
        if 'id' not in data:
            data['id'] = uuid.uuid4()

        # Ensure datetime objects
        if 'created_at' not in data:
            data['created_at'] = datetime.utcnow()
        if 'updated_at' not in data:
            data['updated_at'] = datetime.utcnow()

        query = conversations_table.insert().values(**data)
        await database.execute(query)

    @staticmethod
    async def update_conversation(conversation_id: str, updates: Dict[str, Any]):
        """Update conversation in database"""
        updates["updated_at"] = datetime.utcnow()
        query = (
            conversations_table.update()
            .where(conversations_table.c.conversation_id == conversation_id)
            .values(**updates)
        )
        await database.execute(query)

    @staticmethod
    async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation from database"""
        query = conversations_table.select().where(
            conversations_table.c.conversation_id == conversation_id
        )
        result = await database.fetch_one(query)

        if result:
            return dict(result)
        return None

    @staticmethod
    async def save_message(data: Dict[str, Any]):
        """Save message to database"""
        # Generate UUID if not present
        if 'id' not in data:
            data['id'] = uuid.uuid4()

        # Ensure datetime object
        if 'created_at' not in data:
            data['created_at'] = datetime.utcnow()

        query = messages_table.insert().values(**data)
        await database.execute(query)

    @staticmethod
    async def get_messages(conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        query = (
            messages_table.select()
            .where(messages_table.c.conversation_id == conversation_id)
            .order_by(messages_table.c.created_at.asc())
            .limit(limit)
        )
        results = await database.fetch_all(query)

        return [dict(row) for row in results]


db_service = DatabaseService()
