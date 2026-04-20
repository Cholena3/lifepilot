"""Custom exceptions and error handling for the application."""

from typing import Any


class LifePilotException(Exception):
    """Base exception for LifePilot application."""

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(LifePilotException):
    """Resource not found error."""

    def __init__(
        self,
        resource: str | None = None,
        identifier: str | None = None,
        message: str | None = None,
    ) -> None:
        if message:
            final_message = message
        elif resource:
            final_message = f"{resource} not found"
            if identifier:
                final_message = f"{resource} with id '{identifier}' not found"
        else:
            final_message = "Resource not found"
        super().__init__(message=final_message, status_code=404)


class ValidationError(LifePilotException):
    """Validation error with field details."""

    def __init__(self, message: str, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=422,
            details={"field_errors": field_errors or {}},
        )


class AuthenticationError(LifePilotException):
    """Authentication failed error."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, status_code=401)


class AuthorizationError(LifePilotException):
    """Authorization/permission denied error."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message=message, status_code=403)


class RateLimitError(LifePilotException):
    """Rate limit exceeded error (Requirement 37.2)."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            details={"retry_after": retry_after},
        )


class ConflictError(LifePilotException):
    """Resource conflict error."""

    def __init__(
        self,
        detail: str = "Resource conflict",
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=detail,
            status_code=409,
            details={"field_errors": field_errors or {}},
        )


class ServiceError(LifePilotException):
    """External service error."""

    def __init__(self, message: str = "External service error") -> None:
        super().__init__(message=message, status_code=502)
