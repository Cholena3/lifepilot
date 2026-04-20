"""Redis client configuration with async support and connection pool management.

Implements caching and session management as per Requirement 37.3.
"""

import logging
from typing import Optional

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global Redis client and connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def init_redis() -> Redis:
    """Initialize Redis connection pool and client.
    
    Returns:
        Redis: Async Redis client instance.
    """
    global _redis_pool, _redis_client
    
    settings = get_settings()
    redis_url = str(settings.redis_url)
    
    logger.info(f"Initializing Redis connection to {redis_url}")
    
    # Create connection pool for efficient connection management
    _redis_pool = ConnectionPool.from_url(
        redis_url,
        max_connections=10,
        decode_responses=True,
    )
    
    # Create Redis client with the connection pool
    _redis_client = Redis(connection_pool=_redis_pool)
    
    # Verify connection
    try:
        await _redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection pool and client gracefully."""
    global _redis_pool, _redis_client
    
    if _redis_client is not None:
        logger.info("Closing Redis connection")
        await _redis_client.close()
        _redis_client = None
    
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("Redis connection pool closed")


def get_redis() -> Redis:
    """Get the Redis client instance.
    
    Returns:
        Redis: The initialized Redis client.
        
    Raises:
        RuntimeError: If Redis has not been initialized.
    """
    if _redis_client is None:
        raise RuntimeError(
            "Redis client not initialized. Call init_redis() first."
        )
    return _redis_client
