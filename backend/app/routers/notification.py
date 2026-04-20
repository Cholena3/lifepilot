"""Notification router for notification management endpoints.

Validates: Requirements 31.2, 31.3, 31.4, 32.1, 32.2, 32.3, 32.4, 32.5
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.common import PaginatedResponse, PaginationParams, get_pagination_params
from app.schemas.notification import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
)
from app.services.notification import NotificationService

router = APIRouter()


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get notification preferences",
    description="Retrieve the authenticated user's notification preferences.",
    responses={
        200: {"description": "Preferences retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_notification_preferences(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationPreferencesResponse:
    """Get the current user's notification preferences.
    
    Validates: Requirements 32.1, 32.2, 32.3
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        NotificationPreferencesResponse with user's notification preferences
        
    Raises:
        HTTPException 401: Not authenticated
    """
    service = NotificationService(db)
    preferences = await service.get_preferences(current_user.id)
    return NotificationPreferencesResponse.model_validate(preferences)


@router.put(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update notification preferences",
    description="Update the authenticated user's notification preferences. Changes are applied immediately.",
    responses={
        200: {"description": "Preferences updated successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def update_notification_preferences(
    preferences_data: NotificationPreferencesUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationPreferencesResponse:
    """Update the current user's notification preferences.
    
    Validates: Requirements 32.1, 32.2, 32.3, 32.4
    
    - Changes are applied immediately (Requirement 32.1)
    - Can enable/disable notifications per module (Requirement 32.2)
    - Can set quiet hours with start and end times (Requirement 32.3)
    - Can set notification frequency limits (Requirement 32.4)
    
    Args:
        preferences_data: Notification preferences update data
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        NotificationPreferencesResponse with updated preferences
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 422: Validation error
    """
    service = NotificationService(db)
    
    # Convert Pydantic model to dict, excluding None values
    update_data = preferences_data.model_dump(exclude_none=True)
    
    preferences = await service.update_preferences(current_user.id, **update_data)
    return NotificationPreferencesResponse.model_validate(preferences)


@router.get(
    "/history",
    response_model=PaginatedResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get notification history",
    description="Retrieve the authenticated user's notification history with pagination.",
    responses={
        200: {"description": "History retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_notification_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> PaginatedResponse[NotificationResponse]:
    """Get the current user's notification history.
    
    Validates: Requirements 32.5, 37.5
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        pagination: Pagination parameters (injected)
        
    Returns:
        PaginatedResponse with user's notification history
        
    Raises:
        HTTPException 401: Not authenticated
    """
    service = NotificationService(db)
    notifications, total = await service.get_notification_history_paginated(
        current_user.id, 
        page=pagination.page, 
        page_size=pagination.page_size
    )
    return PaginatedResponse.create(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
