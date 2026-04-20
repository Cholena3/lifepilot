"""Tests for Redis and cache utilities."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core import cache


class TestCacheKey:
    """Tests for cache_key function."""

    def test_cache_key_with_prefix(self):
        """Test cache key generation with prefix."""
        key = cache.cache_key("user", "123", prefix="app")
        assert key == "app:user:123"

    def test_cache_key_without_prefix(self):
        """Test cache key generation without prefix."""
        key = cache.cache_key("user", "123")
        assert key == "user:123"

    def test_cache_key_single_arg(self):
        """Test cache key with single argument."""
        key = cache.cache_key("value", prefix="test")
        assert key == "test:value"


class TestCacheUtilities:
    """Tests for cache utility functions with mocked Redis."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_get_cached_hit(self, mock_redis):
        """Test cache hit returns deserialized value."""
        mock_redis.get.return_value = '{"name": "test"}'
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await cache.get_cached("test:key")
        
        assert result == {"name": "test"}
        mock_redis.get.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_get_cached_miss(self, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await cache.get_cached("test:key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_string_value(self, mock_redis):
        """Test cache returns raw string if not JSON."""
        mock_redis.get.return_value = "plain string"
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await cache.get_cached("test:key")
        
        assert result == "plain string"

    @pytest.mark.asyncio
    async def test_set_cached_with_default_ttl(self, mock_redis):
        """Test setting cache with default TTL."""
        mock_redis.set.return_value = True
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            with patch("app.core.cache.get_settings") as mock_settings:
                mock_settings.return_value.redis_cache_ttl = 3600
                result = await cache.set_cached("test:key", {"data": "value"})
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test:key"
        assert call_args[1]["ex"] == 3600

    @pytest.mark.asyncio
    async def test_set_cached_with_custom_ttl(self, mock_redis):
        """Test setting cache with custom TTL."""
        mock_redis.set.return_value = True
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await cache.set_cached("test:key", "value", ttl=600)
        
        assert result is True
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 600

    @pytest.mark.asyncio
    async def test_delete_cached_success(self, mock_redis):
        """Test successful cache deletion."""
        mock_redis.delete.return_value = 1
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await cache.delete_cached("test:key")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_delete_cached_not_found(self, mock_redis):
        """Test deletion of non-existent key."""
        mock_redis.delete.return_value = 0
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await cache.delete_cached("test:key")
        
        assert result is False


class TestCachedDecorator:
    """Tests for the @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_miss(self):
        """Test decorator calls function on cache miss."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        
        call_count = 0
        
        @cache.cached(prefix="test", ttl=300)
        async def expensive_function(arg: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": arg}
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await expensive_function("value")
        
        assert result == {"result": "value"}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_hit(self):
        """Test decorator returns cached value on hit."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = '{"result": "cached"}'
        
        call_count = 0
        
        @cache.cached(prefix="test", ttl=300)
        async def expensive_function(arg: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": arg}
        
        with patch("app.core.cache.get_redis", return_value=mock_redis):
            result = await expensive_function("value")
        
        assert result == {"result": "cached"}
        assert call_count == 0  # Function should not be called
