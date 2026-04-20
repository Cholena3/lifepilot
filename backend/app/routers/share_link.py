"""Share link router for document sharing endpoints.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.share_link import (
    DocumentAccessResponse,
    QRCodeResponse,
    ShareLinkAccessRequest,
    ShareLinkCreate,
    ShareLinkDetailResponse,
    ShareLinkListResponse,
    ShareLinkResponse,
    ShareLinkWithQRResponse,
)
from app.services.share_link import ShareLinkService

router = APIRouter()


@router.post(
    "",
    response_model=ShareLinkResponse | ShareLinkWithQRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a share link",
    description="Create a new share link for a document with optional password protection.",
    responses={
        201: {"description": "Share link created successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Document not found"},
        422: {"description": "Validation error"},
    },
)
async def create_share_link(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ShareLinkCreate,
    include_qr: Annotated[
        bool,
        Query(description="Include QR code in response")
    ] = False,
) -> ShareLinkResponse | ShareLinkWithQRResponse:
    """Create a new share link for a document.
    
    Validates: Requirements 9.1, 9.2, 9.3
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Share link creation data
        include_qr: Whether to include QR code in response
        
    Returns:
        ShareLinkResponse or ShareLinkWithQRResponse
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Document not found
        HTTPException 422: Validation error
    """
    service = ShareLinkService(db)
    return await service.create_share_link(
        user_id=current_user.id,
        data=data,
        include_qr=include_qr,
    )


@router.get(
    "/access/{token}",
    response_model=DocumentAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Access a shared document",
    description="Access a document via share link. Password required if link is protected.",
    responses={
        200: {"description": "Document access granted"},
        401: {"description": "Password required or invalid"},
        404: {"description": "Share link not found, expired, or revoked"},
    },
)
async def access_share_link(
    token: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    password: Annotated[
        Optional[str],
        Query(description="Password if the share link is protected")
    ] = None,
    user_agent: Annotated[
        Optional[str],
        Header(alias="User-Agent")
    ] = None,
) -> DocumentAccessResponse:
    """Access a shared document via share link.
    
    Validates: Requirements 9.2, 9.4, 9.5, 9.6
    
    This endpoint does not require authentication. Anyone with the link
    (and password if protected) can access the document.
    
    Args:
        token: Share link token
        request: FastAPI request object (for IP address)
        db: Database session (injected)
        password: Password if the share link is protected
        user_agent: User agent header
        
    Returns:
        DocumentAccessResponse with document info and download URL
        
    Raises:
        HTTPException 401: Password required or invalid
        HTTPException 404: Share link not found, expired, or revoked
    """
    # Get client IP address
    ip_address = request.client.host if request.client else "unknown"
    
    # Check for forwarded IP (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    
    service = ShareLinkService(db)
    return await service.access_share_link(
        token=token,
        password=password,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post(
    "/access/{token}",
    response_model=DocumentAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Access a shared document (POST)",
    description="Access a document via share link with password in body.",
    responses={
        200: {"description": "Document access granted"},
        401: {"description": "Password required or invalid"},
        404: {"description": "Share link not found, expired, or revoked"},
    },
)
async def access_share_link_post(
    token: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ShareLinkAccessRequest,
    user_agent: Annotated[
        Optional[str],
        Header(alias="User-Agent")
    ] = None,
) -> DocumentAccessResponse:
    """Access a shared document via share link (POST method).
    
    Validates: Requirements 9.2, 9.4, 9.5, 9.6
    
    This endpoint allows sending the password in the request body
    instead of as a query parameter for better security.
    
    Args:
        token: Share link token
        request: FastAPI request object (for IP address)
        db: Database session (injected)
        data: Access request with optional password
        user_agent: User agent header
        
    Returns:
        DocumentAccessResponse with document info and download URL
        
    Raises:
        HTTPException 401: Password required or invalid
        HTTPException 404: Share link not found, expired, or revoked
    """
    # Get client IP address
    ip_address = request.client.host if request.client else "unknown"
    
    # Check for forwarded IP (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    
    service = ShareLinkService(db)
    return await service.access_share_link(
        token=token,
        password=data.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get(
    "/{share_link_id}",
    response_model=ShareLinkResponse | ShareLinkDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a share link",
    description="Get details of a share link including optional access logs.",
    responses={
        200: {"description": "Share link details returned"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share link not found"},
    },
)
async def get_share_link(
    share_link_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_accesses: Annotated[
        bool,
        Query(description="Include access logs in response")
    ] = False,
) -> ShareLinkResponse | ShareLinkDetailResponse:
    """Get details of a share link.
    
    Validates: Requirements 9.6
    
    Args:
        share_link_id: ShareLink's UUID
        current_user: Authenticated user (injected)
        db: Database session (injected)
        include_accesses: Whether to include access logs
        
    Returns:
        ShareLinkResponse or ShareLinkDetailResponse
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Share link not found
    """
    from uuid import UUID
    
    service = ShareLinkService(db)
    return await service.get_share_link(
        user_id=current_user.id,
        share_link_id=UUID(share_link_id),
        include_accesses=include_accesses,
    )


@router.get(
    "/document/{document_id}",
    response_model=ShareLinkListResponse,
    status_code=status.HTTP_200_OK,
    summary="List share links for a document",
    description="List all share links created for a specific document.",
    responses={
        200: {"description": "Share links returned"},
        401: {"description": "Not authenticated"},
        404: {"description": "Document not found"},
    },
)
async def list_share_links(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_revoked: Annotated[
        bool,
        Query(description="Include revoked share links")
    ] = False,
) -> ShareLinkListResponse:
    """List all share links for a document.
    
    Args:
        document_id: Document's UUID
        current_user: Authenticated user (injected)
        db: Database session (injected)
        include_revoked: Whether to include revoked links
        
    Returns:
        ShareLinkListResponse with list of share links
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Document not found
    """
    from uuid import UUID
    
    service = ShareLinkService(db)
    return await service.list_share_links(
        user_id=current_user.id,
        document_id=UUID(document_id),
        include_revoked=include_revoked,
    )


@router.post(
    "/{share_link_id}/revoke",
    response_model=ShareLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a share link",
    description="Revoke a share link to immediately invalidate it.",
    responses={
        200: {"description": "Share link revoked"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share link not found"},
    },
)
async def revoke_share_link(
    share_link_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShareLinkResponse:
    """Revoke a share link.
    
    Validates: Requirements 9.5
    
    Args:
        share_link_id: ShareLink's UUID
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Updated ShareLinkResponse
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Share link not found
    """
    from uuid import UUID
    
    service = ShareLinkService(db)
    return await service.revoke_share_link(
        user_id=current_user.id,
        share_link_id=UUID(share_link_id),
    )


@router.get(
    "/{share_link_id}/qr",
    response_model=QRCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate QR code for share link",
    description="Generate a QR code containing the share link URL.",
    responses={
        200: {"description": "QR code generated"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share link not found"},
    },
)
async def generate_qr_code(
    share_link_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QRCodeResponse:
    """Generate a QR code for a share link.
    
    Validates: Requirements 9.3
    
    Args:
        share_link_id: ShareLink's UUID
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        QRCodeResponse with base64 encoded QR code
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Share link not found
    """
    from uuid import UUID
    
    service = ShareLinkService(db)
    return await service.generate_qr_code(
        user_id=current_user.id,
        share_link_id=UUID(share_link_id),
    )


@router.delete(
    "/{share_link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a share link",
    description="Permanently delete a share link and its access logs.",
    responses={
        204: {"description": "Share link deleted"},
        401: {"description": "Not authenticated"},
        404: {"description": "Share link not found"},
    },
)
async def delete_share_link(
    share_link_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a share link.
    
    Args:
        share_link_id: ShareLink's UUID
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Share link not found
    """
    from uuid import UUID
    
    service = ShareLinkService(db)
    await service.delete_share_link(
        user_id=current_user.id,
        share_link_id=UUID(share_link_id),
    )
