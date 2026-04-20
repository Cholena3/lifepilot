"""Global error handling middleware."""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import LifePilotException, RateLimitError

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling exceptions globally."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        try:
            return await call_next(request)
        except RateLimitError as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.message, "retry_after": e.details["retry_after"]},
                headers={"Retry-After": str(e.details["retry_after"])},
            )
        except LifePilotException as e:
            logger.warning(f"Application error: {e.message}", extra={"details": e.details})
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.message, **e.details},
            )
        except Exception as e:
            logger.exception(f"Unhandled exception: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )


# Convenience function for adding middleware
error_handler_middleware = ErrorHandlerMiddleware
