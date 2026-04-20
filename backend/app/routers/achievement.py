"""API router for achievement logging.

Requirement 29: Achievement Logging
"""

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.achievement import AchievementCategory
from app.schemas.achievement import (
    AchievementCreate,
    AchievementResponse,
    AchievementsGroupedResponse,
    AchievementSuggestionsResponse,
    AchievementTimelineResponse,
    AchievementUpdate,
    PaginatedAchievementResponse,
)
from app.services.achievement import AchievementService

router = APIRouter(prefix="/achievements", tags=["career"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "",
    response_model=AchievementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new achievement",
    description="Add a new achievement to the user's achievement log. Requirement 29.1",
)
async def create_achievement(
    data: AchievementCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AchievementResponse:
    """Create a new achievement for the current user."""
    service = AchievementService(db)
    achievement = await service.add_achievement(user_id, data)
    return AchievementResponse.model_validate(achievement)


@router.get(
    "",
    response_model=PaginatedAchievementResponse,
    summary="List achievements",
    description="Get a paginated list of user's achievements with optional filtering by category and date range.",
)
async def list_achievements(
    category: Optional[AchievementCategory] = Query(None, description="Filter by category"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedAchievementResponse:
    """Get paginated list of achievements for the current user."""
    service = AchievementService(db)
    return await service.get_achievements(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/timeline",
    response_model=list[AchievementTimelineResponse],
    summary="Get achievements timeline",
    description="Get achievements grouped by year for timeline view. Requirement 29.5",
)
async def get_achievements_timeline(
    category: Optional[AchievementCategory] = Query(None, description="Filter by category"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[AchievementTimelineResponse]:
    """Get achievements grouped by year for timeline display."""
    service = AchievementService(db)
    return await service.get_achievements_timeline(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/grouped",
    response_model=AchievementsGroupedResponse,
    summary="Get achievements grouped by category",
    description="Get all achievements grouped by category. Requirement 29.2",
)
async def get_achievements_grouped(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AchievementsGroupedResponse:
    """Get achievements grouped by category for the current user."""
    service = AchievementService(db)
    return await service.get_achievements_grouped(user_id)


@router.get(
    "/suggestions",
    response_model=AchievementSuggestionsResponse,
    summary="Get achievement suggestions for resume",
    description="Get achievement suggestions for resume building. Requirement 29.4",
)
async def get_achievement_suggestions(
    target_role: Optional[str] = Query(
        None,
        description="Target role for relevance scoring",
    ),
    categories: Optional[str] = Query(
        None,
        description="Comma-separated list of categories to filter",
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions to return"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AchievementSuggestionsResponse:
    """Get achievement suggestions for resume building."""
    service = AchievementService(db)
    
    # Parse categories if provided
    category_list = None
    if categories:
        try:
            category_list = [
                AchievementCategory(c.strip().lower()) 
                for c in categories.split(",")
            ]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category value",
            )
    
    return await service.get_achievement_suggestions(
        user_id=user_id,
        target_role=target_role,
        categories=category_list,
        limit=limit,
    )


@router.get(
    "/{achievement_id}",
    response_model=AchievementResponse,
    summary="Get achievement details",
    description="Get an achievement by ID.",
)
async def get_achievement(
    achievement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AchievementResponse:
    """Get an achievement by ID."""
    service = AchievementService(db)
    achievement = await service.get_achievement(achievement_id, user_id)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Achievement not found",
        )
    return AchievementResponse.model_validate(achievement)


@router.put(
    "/{achievement_id}",
    response_model=AchievementResponse,
    summary="Update an achievement",
    description="Update an achievement's details.",
)
async def update_achievement(
    achievement_id: uuid.UUID,
    data: AchievementUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AchievementResponse:
    """Update an achievement for the current user."""
    service = AchievementService(db)
    achievement = await service.update_achievement(achievement_id, user_id, data)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Achievement not found",
        )
    return AchievementResponse.model_validate(achievement)


@router.delete(
    "/{achievement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an achievement",
    description="Delete an achievement from the user's log.",
)
async def delete_achievement(
    achievement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete an achievement for the current user."""
    service = AchievementService(db)
    deleted = await service.delete_achievement(achievement_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Achievement not found",
        )


@router.post(
    "/{achievement_id}/documents",
    response_model=AchievementResponse,
    summary="Attach documents to achievement",
    description="Attach supporting documents to an achievement. Requirement 29.3",
)
async def attach_documents(
    achievement_id: uuid.UUID,
    document_ids: list[uuid.UUID],
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AchievementResponse:
    """Attach documents to an achievement."""
    service = AchievementService(db)
    achievement = await service.attach_documents(achievement_id, user_id, document_ids)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Achievement not found",
        )
    return AchievementResponse.model_validate(achievement)


@router.delete(
    "/{achievement_id}/documents/{document_id}",
    response_model=AchievementResponse,
    summary="Detach document from achievement",
    description="Detach a supporting document from an achievement. Requirement 29.3",
)
async def detach_document(
    achievement_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AchievementResponse:
    """Detach a document from an achievement."""
    service = AchievementService(db)
    achievement = await service.detach_document(achievement_id, user_id, document_id)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Achievement not found",
        )
    return AchievementResponse.model_validate(achievement)
