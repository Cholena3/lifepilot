"""FastAPI application entry point with CORS, middleware, and error handling."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.middleware import (
    AuditLogMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    error_handler_middleware,
)
from app.routers import api_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if get_settings().debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Startup: Initialize connections, warm caches, etc.
    # Initialize Redis connection pool (Requirement 37.3)
    try:
        from app.core.redis import init_redis
        await init_redis()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis: {e}. Caching will be unavailable.")

    # TODO: Verify database connectivity

    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down application")
    
    # Close Redis connections
    try:
        from app.core.redis import close_redis
        await close_redis()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Error closing Redis connection: {e}")
    
    # TODO: Close database connections


def create_app() -> FastAPI:
    """Application factory for creating the FastAPI app."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="LifePilot - Comprehensive Life Management Platform API",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Configure CORS (Requirement 36.2 - HTTPS/TLS handled at infrastructure level)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time", "Retry-After"],
    )

    # Add custom middleware
    # Note: Middleware is executed in reverse order (last added = first executed)
    app.add_middleware(error_handler_middleware)
    app.add_middleware(AuditLogMiddleware)  # Audit logging (Requirement 36.7)
    app.add_middleware(RateLimitMiddleware)  # Rate limiting (Requirements 36.4, 37.1, 37.2)
    app.add_middleware(LoggingMiddleware)

    # Include API routers
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
        }

    return app


# Create the application instance
app = create_app()
