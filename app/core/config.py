"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation"""

    # Dify Configuration
    DIFY_API_BASE_URL: str
    DIFY_API_KEY: str

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TTL: int = 86400

    # Application Configuration
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_VERSION: str = "v1"

    # Security Configuration
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    API_KEY_HEADER: str = "X-API-Key"
    ALLOWED_ORIGINS: str = "*"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Timeout Configuration
    DIFY_REQUEST_TIMEOUT: int = 300
    DEFAULT_REQUEST_TIMEOUT: int = 30

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
