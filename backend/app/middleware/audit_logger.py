"""Audit logging middleware for tracking all data access.

Validates: Requirements 36.7

Logs all API requests for security audit purposes, including:
- User identification
- Request details (method, path, IP)
- Response status
- Entity access information
"""

import logging
import re
from typing import Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Patterns to extract entity information from URLs
ENTITY_PATTERNS = [
    # Pattern: /api/v1/{entity_type}/{entity_id}
    (r"/api/v1/(\w+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", 1, 2),
    # Pattern: /api/v1/{entity_type}
    (r"/api/v1/(\w+)(?:/|$)", 1, None),
]

# Map HTTP methods to action types
METHOD_TO_ACTION = {
    "GET": "READ",
    "POST": "CREATE",
    "PUT": "UPDATE",
    "PATCH": "UPDATE",
    "DELETE": "DELETE",
}

# Paths to skip audit logging
SKIP_PATHS = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/api/v1/auth/login",  # Login is logged separately
    "/api/v1/auth/register",  # Registration is logged separately
]


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all data access for audit purposes.
    
    Validates: Requirements 36.7
    
    Captures request details and logs them to the database for
    security compliance and audit trail.
    """

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.
        
        Args:
            request: The incoming request
            
        Returns:
            Client IP address string
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_user_id(self, request: Request) -> Optional[UUID]:
        """Extract user ID from request state.
        
        Args:
            request: The incoming request
            
        Returns:
            User UUID if authenticated, None otherwise
        """
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            try:
                return UUID(str(user_id))
            except (ValueError, TypeError):
                return None
        return None

    def _extract_entity_info(self, path: str) -> tuple[Optional[str], Optional[UUID]]:
        """Extract entity type and ID from request path.
        
        Args:
            path: Request URL path
            
        Returns:
            Tuple of (entity_type, entity_id)
        """
        for pattern, type_group, id_group in ENTITY_PATTERNS:
            match = re.match(pattern, path)
            if match:
                entity_type = match.group(type_group) if type_group else None
                entity_id = None
                if id_group:
                    try:
                        entity_id = UUID(match.group(id_group))
                    except (ValueError, IndexError):
                        pass
                return entity_type, entity_id
        return None, None

    def _get_action(self, method: str, path: str) -> str:
        """Determine the action type from HTTP method and path.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            Action type string
        """
        # Special cases for auth endpoints
        if "/auth/login" in path:
            return "LOGIN"
        if "/auth/logout" in path:
            return "LOGOUT"
        if "/auth/register" in path:
            return "REGISTER"
        
        return METHOD_TO_ACTION.get(method.upper(), "UNKNOWN")

    def _should_skip(self, path: str) -> bool:
        """Check if the path should skip audit logging.
        
        Args:
            path: Request URL path
            
        Returns:
            True if should skip, False otherwise
        """
        return path in SKIP_PATHS

    async def _log_to_database(
        self,
        user_id: Optional[UUID],
        action: str,
        entity_type: Optional[str],
        entity_id: Optional[UUID],
        http_method: str,
        request_path: str,
        ip_address: str,
        user_agent: Optional[str],
        status_code: int,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Log audit entry to database.
        
        Args:
            user_id: User performing the action
            action: Action type
            entity_type: Type of entity accessed
            entity_id: ID of entity accessed
            http_method: HTTP method
            request_path: Request URL path
            ip_address: Client IP address
            user_agent: Client user agent
            status_code: Response status code
            extra_data: Additional data
        """
        try:
            from app.core.database import async_session_maker
            from app.models.audit_log import AuditLog

            async with async_session_maker() as session:
                audit_log = AuditLog(
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    http_method=http_method,
                    request_path=request_path,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status_code=status_code,
                    extra_data=extra_data,
                )
                session.add(audit_log)
                await session.commit()
                
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Failed to write audit log: {e}")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log audit information.
        
        Validates: Requirements 36.7
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            Response from the handler
        """
        path = request.url.path
        
        # Skip certain paths
        if self._should_skip(path):
            return await call_next(request)

        # Extract request information
        http_method = request.method
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        
        # Process the request
        response = await call_next(request)
        
        # Extract user ID (may be set by auth middleware)
        user_id = self._get_user_id(request)
        
        # Extract entity information
        entity_type, entity_id = self._extract_entity_info(path)
        
        # Determine action
        action = self._get_action(http_method, path)
        
        # Log to database asynchronously
        # Only log data access operations (not static files, etc.)
        if entity_type or action in ["LOGIN", "LOGOUT", "REGISTER"]:
            await self._log_to_database(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                http_method=http_method,
                request_path=path,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=response.status_code,
            )
            
            if settings.debug:
                logger.debug(
                    f"Audit: {action} {entity_type or 'N/A'} "
                    f"by user={user_id} from {ip_address}"
                )

        return response
