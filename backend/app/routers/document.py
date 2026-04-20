"""Document router for document management endpoints.

Validates: Requirements 6.7
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.document import (
    DocumentCategory,
    DocumentSearchResponse,
    PaginatedResponse,
)
from app.services.document_db import DocumentDBService

router = APIRouter()


@router.get(
    "/search",
    response_model=PaginatedResponse[DocumentSearchResponse],
    status_code=status.HTTP_200_OK,
    summary="Search documents",
    description="Search documents by full-text search across document metadata and OCR content.",
    responses={
        200: {"description": "Search results returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def search_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    query: Annotated[
        str,
        Query(
            min_length=1,
            max_length=500,
            description="Search query string"
        )
    ],
    category: Annotated[
        Optional[str],
        Query(description="Optional category filter")
    ] = None,
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of results per page")
    ] = 20,
) -> PaginatedResponse[DocumentSearchResponse]:
    """Search documents by full-text search.
    
    Validates: Requirements 6.7
    
    Searches across:
    - Document title
    - Document category
    - OCR extracted text (from processed documents)
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        query: Search query string
        category: Optional category filter (Identity, Education, Career, Finance)
        page: Page number (1-indexed, default 1)
        page_size: Number of results per page (1-100, default 20)
        
    Returns:
        PaginatedResponse with matching documents
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 422: Validation error (invalid category, etc.)
    """
    # Validate category if provided
    if category is not None and category not in DocumentCategory.ALL:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Category must be one of: {', '.join(DocumentCategory.ALL)}",
        )
    
    service = DocumentDBService(db)
    return await service.search(
        user_id=current_user.id,
        query=query,
        category=category,
        page=page,
        page_size=page_size,
    )
