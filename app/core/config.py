from typing import Optional
from fastapi import Depends
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from functools import lru_cache
from typing import Any, Dict, List, Optional
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Blog Platform API"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # PostgreSQL Configuration
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    CACHE_EXPIRE_IN_SECONDS: int = 60 * 5  # 5 minutes default

    @field_validator("SQLALCHEMY_DATABASE_URI")
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            host=values.data.get("DB_HOST"),
            port=values.data.get("DB_PORT"),
            username=values.data.get("DB_USER"),
            password=values.data.get("DB_PASSWORD"),
            path=f"/{values.data.get('DB_NAME') or ''}",
        )

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()


async def setup_cache():
    """Initialize Redis cache"""
    redis = aioredis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        encoding="utf8",
        decode_responses=True
    )

    FastAPICache.init(
        RedisBackend(redis),
        prefix="fastapi-cache",
        expire=60 * 5  # Default cache expiration of 5 minutes
    )


def cache_key_builder(
    func,
    namespace: Optional[str] = None,
    *args,
    **kwargs,
):
    """Custom cache key builder that includes query parameters"""
    prefix = FastAPICache.get_prefix()
    cache_key = f"{prefix}:{namespace}:" if namespace else f"{prefix}:"

    # Add function module and name
    cache_key += f"{func.__module__}:{func.__name__}:"

    # Add args if any
    if args:
        cache_key += ":".join(str(arg) for arg in args)

    # Add kwargs if any, sorted by key for consistency
    if kwargs:
        cache_key += ":".join(
            f"{k}={v}" for k, v in sorted(kwargs.items())
            if k not in ["self", "cls"]  # Exclude self and cls
        )

    return cache_key


def cached(
    expire: Optional[int] = None,
    namespace: Optional[str] = None,
    *,
    skip_existing: bool = False,
):
    """Custom cache decorator that uses the custom key builder"""
    return cache(
        expire=expire,
        namespace=namespace,
        key_builder=cache_key_builder,
        skip_existing=skip_existing,
    )
