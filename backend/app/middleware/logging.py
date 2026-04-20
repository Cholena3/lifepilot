"""Request logging middleware."""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and response times."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = time.perf_counter() - start_time
        process_time_ms = process_time * 1000

        # Log performance warning if response time exceeds 2 seconds (Requirement 37.6)
        if process_time > 2.0:
            logger.warning(
                f"Slow response: {request.method} {request.url.path} "
                f"took {process_time_ms:.2f}ms"
            )
        elif settings.debug:
            logger.debug(
                f"{request.method} {request.url.path} "
                f"completed in {process_time_ms:.2f}ms"
            )

        response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"
        return response
