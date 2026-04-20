# Pydantic schemas module
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.notification import (
    NotificationCreate,
    NotificationPreferencesCreate,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationSendRequest,
    NotificationSendResult,
    NotificationSendWithFallbackRequest,
)

__all__ = [
    "PaginatedResponse",
    "PaginationParams",
    "NotificationCreate",
    "NotificationResponse",
    "NotificationSendRequest",
    "NotificationSendWithFallbackRequest",
    "NotificationSendResult",
    "NotificationPreferencesCreate",
    "NotificationPreferencesUpdate",
    "NotificationPreferencesResponse",
]
