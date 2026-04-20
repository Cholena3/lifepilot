"""Cache utility functions for Redis-based caching.

Implements caching utilities as per Requirement 37.3.
Supports JSON serialization for complex objects and function result caching.
"""

import functools
import json
import logging
from typing import Any, Callable, Optional, TypeVar, ParamSpec

from app.core.config import get_settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


async def get_cached(key: str) -> Optional[Any]:
    """Get a value from the cache.
    
    Args:
        key: The cache key to retrieve.
        
    Returns:
        The cached value (deserialized from JSON if applicable), or None if not found.
    """
    redis = get_redis()
    
    try:
        value = await redis.get(key)
        if value is None:
            logger.debug(f"Cache miss for key: {key}")
            return None
        
        logger.debug(f"Cache hit for key: {key}")
        
        # Try to deserialize JSON, return raw value if not JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
            
    except Exception as e:
        logger.error(f"Error getting cached value for key {key}: {e}")
        return None


async def set_cached(
    key: str,
    value: Any,
    ttl: Optional[int] = None,
) -> bool:
    """Set a value in the cache with optional TTL.
    
    Args:
        key: The cache key.
        value: The value to cache (will be JSON serialized if not a string).
        ttl: Time-to-live in seconds. Uses default from settings if not provided.
        
    Returns:
        True if the value was set successfully, False otherwise.
    """
    redis = get_redis()
    settings = get_settings()
    
    # Use default TTL if not provided
    if ttl is None:
        ttl = settings.redis_cache_ttl
    
    try:
        # Serialize complex objects to JSON
        if isinstance(value, str):
            serialized_value = value
        else:
            serialized_value = json.dumps(value, default=str)
        
        await redis.set(key, serialized_value, ex=ttl)
        logger.debug(f"Cached value for key: {key} with TTL: {ttl}s")
        return True
        
    except Exception as e:
        logger.error(f"Error setting cached value for key {key}: {e}")
        return False


async def delete_cached(key: str) -> bool:
    """Delete a value from the cache.
    
    Args:
        key: The cache key to delete.
        
    Returns:
        True if the key was deleted, False otherwise.
    """
    redis = get_redis()
    
    try:
        result = await redis.delete(key)
        if result > 0:
            logger.debug(f"Deleted cache key: {key}")
            return True
        else:
            logger.debug(f"Cache key not found for deletion: {key}")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting cached value for key {key}: {e}")
        return False


async def delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern.
    
    Args:
        pattern: The pattern to match (e.g., "user:*:profile").
        
    Returns:
        The number of keys deleted.
    """
    redis = get_redis()
    
    try:
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            deleted = await redis.delete(*keys)
            logger.debug(f"Deleted {deleted} keys matching pattern: {pattern}")
            return deleted
        return 0
        
    except Exception as e:
        logger.error(f"Error deleting keys matching pattern {pattern}: {e}")
        return 0


def cache_key(*args: Any, prefix: str = "") -> str:
    """Generate a cache key from arguments.
    
    Args:
        *args: Arguments to include in the key.
        prefix: Optional prefix for the key.
        
    Returns:
        A colon-separated cache key string.
    """
    parts = [prefix] if prefix else []
    parts.extend(str(arg) for arg in args)
    return ":".join(parts)


def cached(
    prefix: str = "",
    ttl: Optional[int] = None,
    key_builder: Optional[Callable[..., str]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for caching async function results.
    
    Args:
        prefix: Prefix for the cache key.
        ttl: Time-to-live in seconds. Uses default from settings if not provided.
        key_builder: Optional custom function to build the cache key from arguments.
        
    Returns:
        Decorated function with caching behavior.
        
    Example:
        @cached(prefix="user", ttl=300)
        async def get_user(user_id: str) -> dict:
            # Expensive operation
            return {"id": user_id, "name": "John"}
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                # Default key builder: prefix:func_name:args:kwargs
                key_parts = [prefix or func.__module__, func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = await get_cached(key)
            if cached_value is not None:
                return cached_value
            
            # Call the function and cache the result
            result = await func(*args, **kwargs)
            await set_cached(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
