"""
Configuration Management
All environment variables and settings
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API Authentication
    API_KEY: str = ""  # API key for start_conversation endpoint

    # Dify Configuration
    DIFY_API_URL: str = "http://quotebot.tablazat.hu/v1"
    DIFY_API_KEY: str
    DIFY_TIMEOUT: int = 30

    # Tablazat.hu Configuration
    TABLAZAT_CALLBACK_URL: str = "https://tablazat.hu/api/quotebot/result"
    TABLAZAT_CALLBACK_TIMEOUT: int = 10
    TABLAZAT_CALLBACK_MAX_RETRIES: int = 3

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_SOCKET_KEEPALIVE: bool = True

    # PostgreSQL Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/quotebot"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # CORS
    CORS_ORIGINS: List[str] = [
        "https://tablazat.hu",
        "http://localhost:3000",
        "http://localhost:8080"
    ]

    # Conversation Settings
    CONVERSATION_TTL: int = 86400  # 24 hours in seconds
    MAX_CONVERSATION_MESSAGES: int = 100

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_ENABLED: bool = True

    # Conversation Completion Detection
    COMPLETION_KEYWORDS: List[str] = [
        "thank you for providing all the information",
        "we'll send you a quote",
        "our team will contact you",
        "conversation complete",
        "ajánlatot küldünk",  # Hungarian: "we'll send a quote"
    ]

    # Required fields for conversation completion
    REQUIRED_FIELDS: List[str] = [
        "customer_name",
        "customer_email",
        "product_type"
    ]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    # Monitoring
    SENTRY_DSN: str = ""  # Optional Sentry integration

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
