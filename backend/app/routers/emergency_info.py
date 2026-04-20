"""Emergency info router for emergency health information endpoints.

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.emergency_info import (
    EmergencyInfoCreate,
    EmergencyInfoUpdate,
    EmergencyInfoResponse,
    PublicEmergencyInfoResponse,
    VisibilityUpdate,
    QRCodeResponse,
    AvailableFieldsResponse,
)
from app.services.emergency_info import EmergencyInfoService

router = APIRouter()


# ============================================================================
# Public Endpoint (No Authentication Required)
# ============================================================================

@router.get(
    "/public/{token}",
    response_model=PublicEmergencyInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public emergency info",
    description="Access emergency health information via public token (no authentication required).",
    responses={
        200: {"description": "Emergency info returned successfully"},
        404: {"description": "Emergency info not found"},
    },
)
async def get_public_emergency_info(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str,
) -> PublicEmergencyInfoResponse:
    """Get public emergency info by token.
    
    Validates: Requirements 17.3, 17.4
    
    This endpoint is accessible without authentication and returns only
    the fields that the user has configured as visible.
    
    Args:
        db: Database session (injected)
        token: Public access token from QR code
        
    Returns:
        Public emergency info with only visible fields
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    result = await service.get_public(token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found",
        )
    return result


# ============================================================================
# Authenticated Endpoints
# ============================================================================

@router.get(
    "/fields",
    response_model=AvailableFieldsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get available fields",
    description="Get the list of available emergency info fields and blood types.",
    responses={
        200: {"description": "Fields returned successfully"},
    },
)
async def get_available_fields(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AvailableFieldsResponse:
    """Get available emergency info fields and blood types.
    
    Returns:
        Available fields and blood types
    """
    service = EmergencyInfoService(db)
    return service.get_available_fields()


@router.post(
    "",
    response_model=EmergencyInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update emergency info",
    description="Create or update emergency health information for the authenticated user.",
    responses={
        201: {"description": "Emergency info created/updated successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_or_update_emergency_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: EmergencyInfoCreate,
) -> EmergencyInfoResponse:
    """Create or update emergency health information.
    
    Validates: Requirements 17.1
    
    If emergency info already exists for the user, it will be updated.
    Otherwise, a new record will be created.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Emergency info creation data
        
    Returns:
        Created or updated emergency info
    """
    service = EmergencyInfoService(db)
    return await service.create_or_update(current_user.id, data)


@router.get(
    "",
    response_model=EmergencyInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get emergency info",
    description="Get emergency health information for the authenticated user.",
    responses={
        200: {"description": "Emergency info returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Emergency info not found"},
    },
)
async def get_emergency_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmergencyInfoResponse:
    """Get emergency info for the authenticated user.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Emergency info details
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    result = await service.get(current_user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found. Please create one first.",
        )
    return result


@router.patch(
    "",
    response_model=EmergencyInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update emergency info",
    description="Update emergency health information for the authenticated user.",
    responses={
        200: {"description": "Emergency info updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Emergency info not found"},
        422: {"description": "Validation error"},
    },
)
async def update_emergency_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: EmergencyInfoUpdate,
) -> EmergencyInfoResponse:
    """Update emergency health information.
    
    Validates: Requirements 17.1
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Emergency info update data
        
    Returns:
        Updated emergency info
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    result = await service.update(current_user.id, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found. Please create one first.",
        )
    return result


@router.put(
    "/visibility",
    response_model=EmergencyInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update visible fields",
    description="Update which fields are visible on the public emergency page.",
    responses={
        200: {"description": "Visibility updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Emergency info not found"},
        422: {"description": "Validation error"},
    },
)
async def update_visibility(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: VisibilityUpdate,
) -> EmergencyInfoResponse:
    """Update visible fields configuration.
    
    Validates: Requirements 17.5
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Visibility update data
        
    Returns:
        Updated emergency info
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    result = await service.update_visibility(current_user.id, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found. Please create one first.",
        )
    return result


@router.get(
    "/qr",
    status_code=status.HTTP_200_OK,
    summary="Get QR code image",
    description="Get QR code image linking to public emergency page.",
    responses={
        200: {"description": "QR code image returned successfully", "content": {"image/png": {}}},
        401: {"description": "Not authenticated"},
        404: {"description": "Emergency info not found"},
    },
)
async def get_qr_code(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
) -> Response:
    """Get QR code image linking to public emergency page.
    
    Validates: Requirements 17.2
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        request: FastAPI request object
        
    Returns:
        QR code PNG image
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    
    # Build base URL from request
    base_url = str(request.base_url).rstrip("/")
    
    qr_bytes = await service.get_qr_code_image(current_user.id, base_url)
    if qr_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found. Please create one first.",
        )
    
    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": "inline; filename=emergency_qr.png",
        },
    )


@router.get(
    "/qr/info",
    response_model=QRCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get QR code info",
    description="Get QR code URL and public access information.",
    responses={
        200: {"description": "QR code info returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Emergency info not found"},
    },
)
async def get_qr_code_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
) -> QRCodeResponse:
    """Get QR code URL and public access information.
    
    Validates: Requirements 17.2
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        request: FastAPI request object
        
    Returns:
        QR code response with URLs and token
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    
    # Build base URL from request
    base_url = str(request.base_url).rstrip("/")
    
    result = await service.generate_qr_code(current_user.id, base_url)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found. Please create one first.",
        )
    
    return result


@router.post(
    "/regenerate-token",
    response_model=EmergencyInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate public token",
    description="Regenerate the public access token, invalidating the old QR code.",
    responses={
        200: {"description": "Token regenerated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Emergency info not found"},
    },
)
async def regenerate_token(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmergencyInfoResponse:
    """Regenerate the public access token.
    
    Validates: Requirements 17.5
    
    This invalidates the old QR code and requires generating a new one.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Updated emergency info with new token
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    result = await service.regenerate_token(current_user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found. Please create one first.",
        )
    return result


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete emergency info",
    description="Delete emergency health information for the authenticated user.",
    responses={
        204: {"description": "Emergency info deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Emergency info not found"},
    },
)
async def delete_emergency_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete emergency health information.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Raises:
        HTTPException 404: Emergency info not found
    """
    service = EmergencyInfoService(db)
    deleted = await service.delete(current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency information not found",
        )
