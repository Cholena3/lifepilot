"""Rate limiting middleware for API endpoints.

Validates: Requirements 36.4, 37.1, 37.2

Implements rate limiting using Redis to track request counts per user/IP.
Returns 429 Too Many Requests with Retry-After header when limit exceeded.
"""

import logging
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests.
    
    Validates: Requirements 36.4, 37.1, 37.2
    
    Uses Redis sliding window algorithm to track requests per user/IP.
    Enforces configurable rate limits (default: 100 requests per minute).
    """

    def __init__(self, app, requests_limit: int = None, window_seconds: int = None):
        """Initialize rate limiter with configurable limits.
        
        Args:
            app: The ASGI application
            requests_limit: Maximum requests per window (default from settings)
            window_seconds: Time window in seconds (default from settings)
        """
        super().__init__(app)
        self.requests_limit = requests_limit or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window_seconds

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client.
        
        Uses user ID from JWT token if authenticated, otherwise falls back to IP.
        
        Args:
            request: The incoming request
            
        Returns:
            Unique client identifier string
        """
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP in the chain (original client)
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"

    async def _check_rate_limit(self, identifier: str) -> tuple[bool, int, int]:
        """Check if the client has exceeded the rate limit.
        
        Uses Redis sliding window counter algorithm.
        
        Args:
            identifier: Unique client identifier
            
        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        try:
            from app.core.redis import get_redis
            redis = get_redis()
        except RuntimeError:
            # Redis not available, allow request but log warning
            logger.warning("Redis unavailable for rate limiting, allowing request")
            return True, self.requests_limit, 0

        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        key = f"rate_limit:{identifier}"

        try:
            # Use Redis pipeline for atomic operations
            pipe = redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request with timestamp as score
            pipe.zadd(key, {f"{current_time}:{time.time_ns()}": current_time})
            
            # Set expiry on the key
            pipe.expire(key, self.window_seconds + 1)
            
            results = await pipe.execute()
            
            # results[1] is the count before adding current request
            current_count = results[1]
            
            if current_count >= self.requests_limit:
                # Get the oldest request timestamp to calculate retry-after
                oldest = await redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = int(oldest[0][1])
                    retry_after = max(1, (oldest_time + self.window_seconds) - current_time)
                else:
                    retry_after = self.window_seconds
                
                remaining = 0
                return False, remaining, retry_after
            
            remaining = max(0, self.requests_limit - current_count - 1)
            return True, remaining, 0
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # On error, allow request but log
            return True, self.requests_limit, 0

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting.
        
        Validates: Requirements 37.1, 37.2
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            Response with rate limit headers, or 429 if limit exceeded
        """
        # Skip rate limiting for health check and docs endpoints
        skip_paths = ["/", "/docs", "/redoc", "/openapi.json", "/health"]
        if request.url.path in skip_paths:
            return await call_next(request)

        identifier = self._get_client_identifier(request)
        is_allowed, remaining, retry_after = await self._check_rate_limit(identifier)

        if not is_allowed:
            # Return 429 Too Many Requests (Requirement 37.2)
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"{request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + self.window_seconds
        )

        return response
