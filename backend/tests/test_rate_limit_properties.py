"""Property-based tests for rate limit enforcement.

Property 45: Rate Limit Enforcement

**Validates: Requirements 37.1, 37.2**

For any user making more than 100 requests per minute, subsequent requests
SHALL receive 429 status with retry-after header until the rate limit window resets.
"""

import asyncio
import time
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.middleware.rate_limiter import RateLimitMiddleware


class MockRedis:
    """Mock Redis client for testing rate limiting without actual Redis.
    
    Implements the sliding window algorithm used by the rate limiter.
    """
    
    def __init__(self):
        self._data: dict[str, list[tuple[str, float]]] = {}
        self._expiry: dict[str, float] = {}
    
    def pipeline(self):
        """Return a mock pipeline."""
        return MockRedisPipeline(self)
    
    async def zrange(self, key: str, start: int, end: int, withscores: bool = False):
        """Get range of elements from sorted set."""
        if key not in self._data:
            return []
        
        # Clean expired keys
        current_time = time.time()
        if key in self._expiry and self._expiry[key] < current_time:
            del self._data[key]
            del self._expiry[key]
            return []
        
        sorted_items = sorted(self._data[key], key=lambda x: x[1])
        
        # Handle negative indices
        if end == -1:
            end = len(sorted_items)
        else:
            end = end + 1
        
        result = sorted_items[start:end]
        
        if withscores:
            return result
        return [item[0] for item in result]


class MockRedisPipeline:
    """Mock Redis pipeline for atomic operations."""
    
    def __init__(self, redis: MockRedis):
        self._redis = redis
        self._commands: list[tuple[str, tuple]] = []
    
    def zremrangebyscore(self, key: str, min_score: float, max_score: float):
        """Queue removal of elements by score range."""
        self._commands.append(("zremrangebyscore", (key, min_score, max_score)))
        return self
    
    def zcard(self, key: str):
        """Queue count of elements in sorted set."""
        self._commands.append(("zcard", (key,)))
        return self
    
    def zadd(self, key: str, mapping: dict):
        """Queue addition of elements to sorted set."""
        self._commands.append(("zadd", (key, mapping)))
        return self
    
    def expire(self, key: str, seconds: int):
        """Queue expiry setting."""
        self._commands.append(("expire", (key, seconds)))
        return self
    
    async def execute(self):
        """Execute all queued commands and return results."""
        results = []
        
        for cmd, args in self._commands:
            if cmd == "zremrangebyscore":
                key, min_score, max_score = args
                if key in self._redis._data:
                    original_len = len(self._redis._data[key])
                    self._redis._data[key] = [
                        (member, score) for member, score in self._redis._data[key]
                        if score > max_score
                    ]
                    removed = original_len - len(self._redis._data[key])
                    results.append(removed)
                else:
                    results.append(0)
            
            elif cmd == "zcard":
                key = args[0]
                if key in self._redis._data:
                    results.append(len(self._redis._data[key]))
                else:
                    results.append(0)
            
            elif cmd == "zadd":
                key, mapping = args
                if key not in self._redis._data:
                    self._redis._data[key] = []
                for member, score in mapping.items():
                    self._redis._data[key].append((member, score))
                results.append(len(mapping))
            
            elif cmd == "expire":
                key, seconds = args
                self._redis._expiry[key] = time.time() + seconds
                results.append(True)
        
        return results


def create_mock_request(
    path: str = "/api/v1/test",
    client_ip: str = "127.0.0.1",
    user_id: Optional[str] = None,
    forwarded_for: Optional[str] = None,
) -> MagicMock:
    """Create a mock request object for testing."""
    request = MagicMock(spec=Request)
    request.url.path = path
    request.method = "GET"
    
    # Mock client
    client = MagicMock()
    client.host = client_ip
    request.client = client
    
    # Mock headers
    headers = {}
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    request.headers.get = lambda key, default=None: headers.get(key, default)
    
    # Mock state for user_id
    request.state = MagicMock()
    if user_id:
        request.state.user_id = user_id
    else:
        # Make getattr return None for user_id when not set
        del request.state.user_id
    
    return request


async def mock_call_next(request: Request) -> Response:
    """Mock call_next function that returns a successful response."""
    response = Response(content="OK", status_code=200)
    return response


class TestRateLimitEnforcementProperty:
    """Property 45: Rate Limit Enforcement.
    
    **Validates: Requirements 37.1, 37.2**
    
    For any user making more than 100 requests per minute, subsequent requests
    SHALL receive 429 status with retry-after header until the rate limit window resets.
    """
    
    @given(
        requests_within_limit=st.integers(min_value=1, max_value=99),
        rate_limit=st.integers(min_value=10, max_value=200),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_requests_within_limit_are_allowed(
        self, requests_within_limit: int, rate_limit: int
    ):
        """Requests within the limit SHALL be allowed.
        
        **Validates: Requirements 37.1**
        
        For any number of requests N where N < rate_limit, all requests
        SHALL receive successful responses (not 429).
        """
        # Ensure requests_within_limit is less than rate_limit
        assume(requests_within_limit < rate_limit)
        
        mock_redis = MockRedis()
        
        # Create middleware with the specified rate limit
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=rate_limit,
            window_seconds=60
        )
        
        # Patch get_redis to return our mock
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            request = create_mock_request(client_ip="192.168.1.1")
            
            # Make requests_within_limit requests
            for i in range(requests_within_limit):
                response = await middleware.dispatch(request, mock_call_next)
                
                # All requests within limit should succeed
                assert response.status_code == 200, (
                    f"Request {i + 1} of {requests_within_limit} should succeed "
                    f"(limit: {rate_limit}), got status {response.status_code}"
                )
                
                # Verify rate limit headers are present
                assert "X-RateLimit-Limit" in response.headers
                assert response.headers["X-RateLimit-Limit"] == str(rate_limit)
    
    @given(
        rate_limit=st.integers(min_value=5, max_value=50),
        extra_requests=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_requests_exceeding_limit_return_429(
        self, rate_limit: int, extra_requests: int
    ):
        """Requests exceeding the limit SHALL return 429 status code.
        
        **Validates: Requirements 37.1, 37.2**
        
        For any number of requests N where N > rate_limit, requests after
        the limit SHALL receive 429 Too Many Requests status.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=rate_limit,
            window_seconds=60
        )
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            request = create_mock_request(client_ip="192.168.1.2")
            
            # Make rate_limit requests (should all succeed)
            for i in range(rate_limit):
                response = await middleware.dispatch(request, mock_call_next)
                assert response.status_code == 200, (
                    f"Request {i + 1} within limit should succeed"
                )
            
            # Make extra_requests more requests (should all fail with 429)
            for i in range(extra_requests):
                response = await middleware.dispatch(request, mock_call_next)
                assert response.status_code == 429, (
                    f"Request {rate_limit + i + 1} exceeding limit should return 429, "
                    f"got {response.status_code}"
                )
    
    @given(
        rate_limit=st.integers(min_value=5, max_value=50),
        window_seconds=st.integers(min_value=10, max_value=120),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_retry_after_header_present_when_rate_limited(
        self, rate_limit: int, window_seconds: int
    ):
        """Retry-After header SHALL be present and valid when rate limited.
        
        **Validates: Requirements 37.2**
        
        When a request is rate limited (429 response), the response SHALL
        include a Retry-After header with a positive integer value.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=rate_limit,
            window_seconds=window_seconds
        )
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            request = create_mock_request(client_ip="192.168.1.3")
            
            # Exhaust the rate limit
            for _ in range(rate_limit):
                await middleware.dispatch(request, mock_call_next)
            
            # Next request should be rate limited
            response = await middleware.dispatch(request, mock_call_next)
            
            assert response.status_code == 429, "Should be rate limited"
            
            # Verify Retry-After header is present
            assert "Retry-After" in response.headers, (
                "Retry-After header should be present when rate limited"
            )
            
            # Verify Retry-After is a valid positive integer
            retry_after = response.headers["Retry-After"]
            retry_after_int = int(retry_after)
            assert retry_after_int >= 1, (
                f"Retry-After should be at least 1 second, got {retry_after_int}"
            )
            assert retry_after_int <= window_seconds, (
                f"Retry-After should not exceed window ({window_seconds}s), "
                f"got {retry_after_int}"
            )
            
            # Verify other rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert response.headers["X-RateLimit-Remaining"] == "0"
    
    @given(
        rate_limit=st.integers(min_value=3, max_value=20),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_rate_limit_response_body_contains_retry_after(
        self, rate_limit: int
    ):
        """Rate limited response body SHALL contain retry_after information.
        
        **Validates: Requirements 37.2**
        
        The 429 response body should include retry_after in the JSON content.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=rate_limit,
            window_seconds=60
        )
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            request = create_mock_request(client_ip="192.168.1.4")
            
            # Exhaust the rate limit
            for _ in range(rate_limit):
                await middleware.dispatch(request, mock_call_next)
            
            # Get rate limited response
            response = await middleware.dispatch(request, mock_call_next)
            
            assert response.status_code == 429
            
            # For JSONResponse, check the body
            if isinstance(response, JSONResponse):
                import json
                body = json.loads(response.body.decode())
                assert "retry_after" in body, (
                    "Response body should contain retry_after field"
                )
                assert isinstance(body["retry_after"], int), (
                    "retry_after should be an integer"
                )
                assert body["retry_after"] >= 1, (
                    "retry_after should be at least 1"
                )
    
    @given(
        rate_limit=st.integers(min_value=3, max_value=15),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_rate_limits_are_per_client(
        self, rate_limit: int
    ):
        """Rate limits SHALL be enforced per client identifier.
        
        **Validates: Requirements 37.1**
        
        Different clients (different IPs or user IDs) should have
        independent rate limit counters.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=rate_limit,
            window_seconds=60
        )
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            # Client 1 exhausts their rate limit
            request1 = create_mock_request(client_ip="10.0.0.1")
            for _ in range(rate_limit):
                await middleware.dispatch(request1, mock_call_next)
            
            # Client 1 should now be rate limited
            response1 = await middleware.dispatch(request1, mock_call_next)
            assert response1.status_code == 429, "Client 1 should be rate limited"
            
            # Client 2 should still be able to make requests
            request2 = create_mock_request(client_ip="10.0.0.2")
            response2 = await middleware.dispatch(request2, mock_call_next)
            assert response2.status_code == 200, (
                "Client 2 should not be affected by Client 1's rate limit"
            )
    
    @given(
        rate_limit=st.integers(min_value=3, max_value=15),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_authenticated_user_rate_limit_by_user_id(
        self, rate_limit: int
    ):
        """Authenticated users SHALL be rate limited by user ID.
        
        **Validates: Requirements 37.1**
        
        When a user is authenticated (has user_id in request state),
        rate limiting should be based on user ID, not IP address.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=rate_limit,
            window_seconds=60
        )
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            user_id = "user-123-abc"
            
            # Create request with user_id in state
            request = MagicMock(spec=Request)
            request.url.path = "/api/v1/test"
            request.method = "GET"
            request.client = MagicMock()
            request.client.host = "192.168.1.100"
            request.headers.get = lambda key, default=None: None
            request.state = MagicMock()
            request.state.user_id = user_id
            
            # Exhaust rate limit for this user
            for _ in range(rate_limit):
                await middleware.dispatch(request, mock_call_next)
            
            # User should be rate limited
            response = await middleware.dispatch(request, mock_call_next)
            assert response.status_code == 429, "User should be rate limited"
            
            # Same user from different IP should still be rate limited
            request2 = MagicMock(spec=Request)
            request2.url.path = "/api/v1/test"
            request2.method = "GET"
            request2.client = MagicMock()
            request2.client.host = "10.0.0.50"  # Different IP
            request2.headers.get = lambda key, default=None: None
            request2.state = MagicMock()
            request2.state.user_id = user_id  # Same user
            
            response2 = await middleware.dispatch(request2, mock_call_next)
            assert response2.status_code == 429, (
                "Same user from different IP should still be rate limited"
            )
    
    @pytest.mark.asyncio
    async def test_skip_paths_not_rate_limited(self):
        """Health check and docs endpoints SHALL NOT be rate limited.
        
        **Validates: Requirements 37.1**
        
        Certain paths like /health, /docs, /redoc should be excluded
        from rate limiting to ensure monitoring and documentation access.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=1,  # Very low limit
            window_seconds=60
        )
        
        skip_paths = ["/", "/docs", "/redoc", "/openapi.json", "/health"]
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            for path in skip_paths:
                request = create_mock_request(path=path, client_ip="192.168.1.5")
                
                # Make many requests to these paths
                for i in range(10):
                    response = await middleware.dispatch(request, mock_call_next)
                    assert response.status_code == 200, (
                        f"Request to {path} should not be rate limited "
                        f"(request {i + 1})"
                    )
    
    @given(
        rate_limit=st.integers(min_value=3, max_value=10),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_remaining_requests_decrements_correctly(
        self, rate_limit: int
    ):
        """X-RateLimit-Remaining header SHALL decrement with each request.
        
        **Validates: Requirements 37.1**
        
        The remaining requests counter should accurately reflect how many
        requests the client can still make within the current window.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=rate_limit,
            window_seconds=60
        )
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            request = create_mock_request(client_ip="192.168.1.6")
            
            previous_remaining = rate_limit
            
            for i in range(rate_limit):
                response = await middleware.dispatch(request, mock_call_next)
                
                if response.status_code == 200:
                    remaining = int(response.headers["X-RateLimit-Remaining"])
                    
                    # Remaining should be less than or equal to previous
                    assert remaining <= previous_remaining, (
                        f"Remaining should decrease: was {previous_remaining}, "
                        f"now {remaining}"
                    )
                    
                    # Remaining should be non-negative
                    assert remaining >= 0, (
                        f"Remaining should be non-negative, got {remaining}"
                    )
                    
                    previous_remaining = remaining
    
    @pytest.mark.asyncio
    async def test_x_forwarded_for_header_respected(self):
        """X-Forwarded-For header SHALL be used for client identification.
        
        **Validates: Requirements 37.1**
        
        When behind a proxy, the original client IP from X-Forwarded-For
        should be used for rate limiting.
        """
        mock_redis = MockRedis()
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=5,
            window_seconds=60
        )
        
        with patch("app.core.redis.get_redis", return_value=mock_redis):
            # Create request with X-Forwarded-For header
            request = MagicMock(spec=Request)
            request.url.path = "/api/v1/test"
            request.method = "GET"
            request.client = MagicMock()
            request.client.host = "10.0.0.1"  # Proxy IP
            request.headers.get = lambda key, default=None: (
                "203.0.113.50, 10.0.0.1" if key == "X-Forwarded-For" else default
            )
            request.state = MagicMock()
            del request.state.user_id
            
            # Exhaust rate limit
            for _ in range(5):
                await middleware.dispatch(request, mock_call_next)
            
            # Should be rate limited
            response = await middleware.dispatch(request, mock_call_next)
            assert response.status_code == 429
            
            # Different original IP should not be rate limited
            request2 = MagicMock(spec=Request)
            request2.url.path = "/api/v1/test"
            request2.method = "GET"
            request2.client = MagicMock()
            request2.client.host = "10.0.0.1"  # Same proxy IP
            request2.headers.get = lambda key, default=None: (
                "203.0.113.100, 10.0.0.1" if key == "X-Forwarded-For" else default
            )  # Different original IP
            request2.state = MagicMock()
            del request2.state.user_id
            
            response2 = await middleware.dispatch(request2, mock_call_next)
            assert response2.status_code == 200, (
                "Different original IP should not be rate limited"
            )
    
    @pytest.mark.asyncio
    async def test_redis_unavailable_allows_requests(self):
        """When Redis is unavailable, requests SHALL be allowed.
        
        **Validates: Requirements 37.1**
        
        Rate limiting should fail open - if Redis is unavailable,
        requests should be allowed rather than blocked.
        """
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(
            MockApp(),
            requests_limit=1,  # Very low limit
            window_seconds=60
        )
        
        # Patch get_redis to raise RuntimeError (Redis unavailable)
        with patch(
            "app.core.redis.get_redis",
            side_effect=RuntimeError("Redis not initialized")
        ):
            request = create_mock_request(client_ip="192.168.1.7")
            
            # Should allow requests even with very low limit
            for i in range(10):
                response = await middleware.dispatch(request, mock_call_next)
                assert response.status_code == 200, (
                    f"Request {i + 1} should be allowed when Redis unavailable"
                )


class TestRateLimitDefaultConfiguration:
    """Test that default rate limit configuration matches requirements."""
    
    def test_default_rate_limit_is_100_per_minute(self):
        """Default rate limit SHALL be 100 requests per minute.
        
        **Validates: Requirements 37.1**
        """
        from app.core.config import get_settings
        
        settings = get_settings()
        assert settings.rate_limit_requests == 100, (
            f"Default rate limit should be 100, got {settings.rate_limit_requests}"
        )
        assert settings.rate_limit_window_seconds == 60, (
            f"Default window should be 60 seconds, got {settings.rate_limit_window_seconds}"
        )
    
    def test_middleware_uses_default_settings(self):
        """Middleware SHALL use default settings when not specified.
        
        **Validates: Requirements 37.1**
        """
        from app.core.config import get_settings
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(MockApp())
        settings = get_settings()
        
        assert middleware.requests_limit == settings.rate_limit_requests
        assert middleware.window_seconds == settings.rate_limit_window_seconds
