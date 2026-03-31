from __future__ import annotations

import contextlib
import json
import logging
import os
from typing import Any

try:
    from redis.asyncio import ConnectionError, Redis
except ImportError:
    Redis = None
    ConnectionError = Exception

logger = logging.getLogger(__name__)

# Singleton Redis Client
redis_client: Redis | None = None


def init_redis():
    """Redis bağlantısını başlat."""
    global redis_client
    redis_url = os.getenv("REDIS_URL")

    if not redis_url:
        logger.warning("⚠️ REDIS_URL not found in env. Caching disabled.")
        return

    if not Redis:
        logger.error("❌ Redis library not installed. Install with 'pip install redis'")
        return

    try:
        redis_client = Redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0)
        logger.info("✅ Redis Initialized")
    except Exception as e:
        logger.error(f"❌ Redis Init Error: {e}")


async def get_cache(key: str) -> Any | None:
    """Get value from cache."""
    if not redis_client:
        return None
    try:
        raw_value = await redis_client.get(key)
        if raw_value is None:
            return None
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            # Return raw string if JSON parse fails (e.g. plain language code)
            logger.debug(f"Cache value for {key} is not valid JSON, returning raw value")
            return raw_value
    except ConnectionError:
        logger.error("❌ Redis Connection Error (GET)")
        return None
    except Exception as e:
        logger.debug(f"Cache get error for key {key}: {e}")
        return None


async def set_cache(key: str, value: Any, ttl: int = 3600):
    """Set value to cache with TTL."""
    if not redis_client:
        return
    try:
        serialized = json.dumps(value)
        await redis_client.setex(key, ttl, serialized)
    except ConnectionError:
        logger.error("❌ Redis Connection Error (SET)")
    except Exception as e:
        logger.error(f"Redis Set Error: {e}")


async def delete_cache(key: str):
    """Delete value from cache."""
    if not redis_client:
        return
    with contextlib.suppress(Exception):
        await redis_client.delete(key)
