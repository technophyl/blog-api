from typing import Optional
from fastapi import Depends
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from app.core.config import settings


async def setup_cache():
    """Initialize Redis cache"""
    redis = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
        decode_responses=True
    )

    FastAPICache.init(
        RedisBackend(redis),
        prefix="fastapi-cache",
        expire=settings.CACHE_EXPIRE_IN_SECONDS
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
):
    """Custom cache decorator that uses the custom key builder"""
    return cache(
        expire=expire,
        namespace=namespace,
        key_builder=cache_key_builder,
    )
