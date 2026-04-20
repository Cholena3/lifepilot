"""Health record share router for sharing records with doctors.

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.health_share import (
    HealthRecordShareCreate,
    HealthRecordShareUpdate,
    HealthRecordShareResponse,
    HealthRecordShareDetailResponse,
    PublicHealthShareResponse,
    PaginatedHealthRecordShareResponse,
)
from app.services.health_share import HealthShareService

router = APIRouter()


# ============================================================================
# Public Endpoint (No Authentication Required)
# ============================================================================

@router.get(
    "/public/{token}",
    response_model=PublicHealthShareResponse,
    status_code=status.HTTP_200_OK,
    summary="Access shared health records",
    description="Access shared health records via public token (no authentication required).",
    responses={
        200: {"description": "Shared records returned successfully"},
        404: {"description": "Share not found or expired"},
    },
)
async def get_public_shared_records(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    token: str,
) -> PublicHealthShareResponse:
    """Access shared health records by public token.
    
    Validates: Requirements 18.3, 18.4, 18.5
    
    This endpoint is accessible without authentication and returns
    read-only health record information. Each access is logged.
    
    Args:
        db: Database session (injected)
        request: FastAPI request object
        token: Public access token from share link
        
    Returns:
        Public share response with health records
        
    Raises:
        HTTPException 404: Share not found, expired, or revoked
    """
    service = HealthShareService(db)
    
    # Get client IP and user agent for logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    result = await service.get_public_share(token, ip_address, user_agent)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found, expired, or has been revoked",
        )
    return result


# ============================================================================
# Authenticated Endpoints
# ============================================================================

@router.post(
    "",
    response_model=HealthRecordShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create share link",
    description="Create a new share link for selected health records.",
    responses={
        201: {"description": "Share link created successfully"},
        400: {"description": "Invalid record IDs"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_share(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: HealthRecordShareCreate,
) -> HealthRecordShareResponse:
    """Create a new health record share link.
    
    Validates: Requirements 18.1, 18.2
    
    Creates a temporary share link that allows doctors to view
    selected health records without authentication.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Share creation data
        
    Returns:
        Created share response with public token
        
    Raises:
        HTTPException 400: If any record IDs don't belong to the user
    """
    service = HealthShareService(db)
    try:
        return await service.create_share(current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=PaginatedHealthRecordShareResponse,
    status_code=status.HTTP_200_OK,
    summary="List share links",
    description="List all share links created by the authenticated user.",
    responses={
        200: {"description": "Share links returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_shares(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_expired: bool = Query(False, description="Include expired shares"),
    include_revoked: bool = Query(False, description="Include revoked shares"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedHealthRecordShareResponse:
    """List all health record share links for the authenticated user.
    
    Validates: Requirements 18.1
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        include_expired: Whether to include expired shares
        include_revoked: Whether to include revoked shares
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Paginated list of share links
    """
    service = HealthShareService(db)
    return await service.list_shares(
        current_user.id,
        include_expired=include_expired,
        include_revoked=include_revoked,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{share_id}",
    response_model=HealthRecordShareDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get share details",
    description="Get detailed information about a share link including access logs.",
    responses={
        200: {"description": "Share details returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share not found"},
    },
)
async def get_share(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    share_id: str,
) -> HealthRecordShareDetailResponse:
    """Get detailed information about a share link.
    
    Validates: Requirements 18.5
    
    Returns share details including access logs showing when
    and from where the share link was accessed.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        share_id: Share's UUID
        
    Returns:
        Detailed share response with access logs
        
    Raises:
        HTTPException 404: Share not found
    """
    from uuid import UUID
    
    service = HealthShareService(db)
    try:
        share_uuid = UUID(share_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
    
    result = await service.get_share_with_logs(current_user.id, share_uuid)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
    return result


@router.patch(
    "/{share_id}",
    response_model=HealthRecordShareResponse,
    status_code=status.HTTP_200_OK,
    summary="Update share",
    description="Update share link details (doctor name, email, purpose, notes).",
    responses={
        200: {"description": "Share updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share not found"},
        422: {"description": "Validation error"},
    },
)
async def update_share(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    share_id: str,
    data: HealthRecordShareUpdate,
) -> HealthRecordShareResponse:
    """Update a health record share.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        share_id: Share's UUID
        data: Share update data
        
    Returns:
        Updated share response
        
    Raises:
        HTTPException 404: Share not found
    """
    from uuid import UUID
    
    service = HealthShareService(db)
    try:
        share_uuid = UUID(share_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
    
    result = await service.update_share(current_user.id, share_uuid, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
    return result


@router.post(
    "/{share_id}/revoke",
    response_model=HealthRecordShareResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke share link",
    description="Revoke a share link, making it inaccessible.",
    responses={
        200: {"description": "Share revoked successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share not found"},
    },
)
async def revoke_share(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    share_id: str,
) -> HealthRecordShareResponse:
    """Revoke a health record share link.
    
    Validates: Requirements 18.4
    
    Once revoked, the share link can no longer be accessed
    by doctors, even if it hasn't expired yet.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        share_id: Share's UUID
        
    Returns:
        Revoked share response
        
    Raises:
        HTTPException 404: Share not found
    """
    from uuid import UUID
    
    service = HealthShareService(db)
    try:
        share_uuid = UUID(share_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
    
    result = await service.revoke_share(current_user.id, share_uuid)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
    return result


@router.delete(
    "/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete share link",
    description="Permanently delete a share link.",
    responses={
        204: {"description": "Share deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share not found"},
    },
)
async def delete_share(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    share_id: str,
) -> None:
    """Delete a health record share link.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        share_id: Share's UUID
        
    Raises:
        HTTPException 404: Share not found
    """
    from uuid import UUID
    
    service = HealthShareService(db)
    try:
        share_uuid = UUID(share_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
    
    deleted = await service.delete_share(current_user.id, share_uuid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
