"""Account management router for data export and deletion endpoints.

Validates: Requirements 36.5, 36.6
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.account import (
    AccountDeletionCancelResponse,
    AccountDeletionRequest,
    AccountDeletionResponse,
    AccountDeletionStatusResponse,
    DataExportResponse,
)
from app.services.account import AccountService

router = APIRouter()


@router.get(
    "/export",
    response_model=DataExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export all user data",
    description="Export all user data in a portable JSON format. Includes profile, documents, expenses, health records, wardrobe, career data, and more.",
    responses={
        200: {"description": "User data exported successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def export_user_data(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DataExportResponse:
    """Export all user data in a portable format.
    
    Validates: Requirements 36.5
    
    Returns all user data including:
    - Profile and preferences
    - Documents metadata
    - Expenses and budgets
    - Health records and vitals
    - Wardrobe items and outfits
    - Skills and career data
    - Notifications and analytics
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        DataExportResponse containing all user data in JSON format
    """
    service = AccountService(db)
    return await service.export_user_data(current_user.id)


@router.post(
    "/delete",
    response_model=AccountDeletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Request account deletion",
    description="Request account deletion with a 30-day grace period. The account and all data will be permanently deleted after 30 days unless cancelled.",
    responses={
        200: {"description": "Account deletion scheduled"},
        400: {"description": "Invalid request or deletion already pending"},
        401: {"description": "Not authenticated or invalid password"},
    },
)
async def request_account_deletion(
    request: AccountDeletionRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AccountDeletionResponse:
    """Request account deletion with 30-day grace period.
    
    Validates: Requirements 36.6
    
    - Schedules account for permanent deletion after 30 days
    - Requires password confirmation for password-based accounts
    - Can be cancelled within the 30-day window
    
    Args:
        request: Deletion request with confirmation
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        AccountDeletionResponse with deletion schedule
        
    Raises:
        HTTPException 400: If confirmation is False or deletion already pending
        HTTPException 401: If password is invalid
    """
    if not request.confirm:
        from app.core.exceptions import ValidationError
        raise ValidationError(
            message="Must confirm account deletion",
            field_errors={"confirm": "Confirmation required"}
        )
    
    service = AccountService(db)
    return await service.request_account_deletion(
        user_id=current_user.id,
        password=request.password,
    )


@router.post(
    "/delete/cancel",
    response_model=AccountDeletionCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel account deletion",
    description="Cancel a pending account deletion request within the 30-day grace period.",
    responses={
        200: {"description": "Account deletion cancelled"},
        400: {"description": "No pending deletion or grace period expired"},
        401: {"description": "Not authenticated"},
    },
)
async def cancel_account_deletion(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AccountDeletionCancelResponse:
    """Cancel a pending account deletion request.
    
    Validates: Requirements 36.6
    
    - Can only cancel within the 30-day grace period
    - Restores account to normal status
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        AccountDeletionCancelResponse confirming cancellation
        
    Raises:
        HTTPException 400: If no pending deletion or grace period expired
    """
    service = AccountService(db)
    return await service.cancel_account_deletion(current_user.id)


@router.get(
    "/delete/status",
    response_model=AccountDeletionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get account deletion status",
    description="Check if account deletion is pending and when it will be executed.",
    responses={
        200: {"description": "Deletion status retrieved"},
        401: {"description": "Not authenticated"},
    },
)
async def get_deletion_status(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AccountDeletionStatusResponse:
    """Get the current account deletion status.
    
    Validates: Requirements 36.6
    
    Returns:
    - Whether deletion is pending
    - When deletion was requested
    - When deletion will be executed
    - Whether it can still be cancelled
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        AccountDeletionStatusResponse with current status
    """
    service = AccountService(db)
    return await service.get_deletion_status(current_user.id)
