"""API router for Life Score gamification.

Requirement 33: Life Score Gamification
"""

from datetime import date, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.life_score import (
    LifeScoreComparisonResponse,
    LifeScoreDetailResponse,
    LifeScoreTrendResponse,
    PaginatedLifeScoreResponse,
)
from app.services.life_score import LifeScoreService

router = APIRouter()


def _validate_date_range(start_date: date, end_date: date) -> None:
    """Validate date range parameters."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must not be before start_date",
        )
    
    # Limit date range to 1 year
    max_days = 365
    if (end_date - start_date).days > max_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Date range cannot exceed {max_days} days",
        )


@router.get(
    "/current",
    response_model=LifeScoreDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current Life Score",
    description="Get the current Life Score with module breakdown. Calculates fresh score based on recent activity.",
    responses={
        200: {"description": "Life Score returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_current_life_score(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LifeScoreDetailResponse:
    """Get current Life Score with breakdown.
    
    Validates: Requirements 33.1, 33.6
    
    Calculates the Life Score based on activity across all modules
    in the last 30 days, weighted by importance.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Current Life Score with module breakdown
    """
    service = LifeScoreService(db)
    result = await service.get_current_score(current_user.id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate Life Score",
        )
    
    return result


@router.get(
    "/breakdown",
    response_model=LifeScoreDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Life Score breakdown by module",
    description="Get the Life Score breakdown showing contribution from each module.",
    responses={
        200: {"description": "Score breakdown returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_score_breakdown(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LifeScoreDetailResponse:
    """Get Life Score breakdown by module.
    
    Validates: Requirements 33.6
    
    Returns the Life Score with detailed breakdown showing how much
    each module (Documents, Money, Health, Wardrobe, Career, Exams)
    contributes to the total score.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Life Score with module breakdown
    """
    service = LifeScoreService(db)
    return await service.get_score_breakdown(current_user.id)


@router.get(
    "/trends",
    response_model=LifeScoreTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Life Score trends",
    description="Get Life Score trends over time for visualization.",
    responses={
        200: {"description": "Trends returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid date range"},
    },
)
async def get_life_score_trends(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Annotated[
        Optional[date],
        Query(description="Start date for trends (defaults to 30 days ago)")
    ] = None,
    end_date: Annotated[
        Optional[date],
        Query(description="End date for trends (defaults to today)")
    ] = None,
) -> LifeScoreTrendResponse:
    """Get Life Score trends over time.
    
    Validates: Requirements 33.4
    
    Returns daily Life Score data points for the specified period,
    suitable for line chart visualization.
    
    Args:
        current_user: Authenticated user
        db: Database session
        start_date: Start date (defaults to 30 days ago)
        end_date: End date (defaults to today)
        
    Returns:
        Life Score trends with data points
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    _validate_date_range(start_date, end_date)
    
    service = LifeScoreService(db)
    return await service.get_score_trends(current_user.id, start_date, end_date)


@router.get(
    "/history",
    response_model=PaginatedLifeScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Life Score history",
    description="Get paginated Life Score history for the user.",
    responses={
        200: {"description": "History returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_life_score_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 30,
) -> PaginatedLifeScoreResponse:
    """Get paginated Life Score history.
    
    Validates: Requirements 33.4
    
    Returns historical Life Score records for the user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Paginated Life Score history
    """
    service = LifeScoreService(db)
    return await service.get_score_history(current_user.id, page, page_size)


@router.get(
    "/compare",
    response_model=LifeScoreComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Life Scores",
    description="Compare current Life Score with a previous score.",
    responses={
        200: {"description": "Comparison returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def compare_life_scores(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    days_ago: Annotated[
        int,
        Query(ge=1, le=365, description="Number of days ago to compare with")
    ] = 7,
) -> LifeScoreComparisonResponse:
    """Compare current Life Score with a previous score.
    
    Validates: Requirements 33.4
    
    Compares today's Life Score with the score from the specified
    number of days ago.
    
    Args:
        current_user: Authenticated user
        db: Database session
        days_ago: Number of days ago to compare with (default: 7)
        
    Returns:
        Life Score comparison with change metrics
    """
    service = LifeScoreService(db)
    return await service.compare_scores(current_user.id, days_ago=days_ago)


@router.post(
    "/calculate",
    response_model=LifeScoreDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalculate Life Score",
    description="Force recalculation of Life Score for a specific date.",
    responses={
        200: {"description": "Life Score recalculated successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def recalculate_life_score(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    score_date: Annotated[
        Optional[date],
        Query(description="Date to calculate score for (defaults to today)")
    ] = None,
) -> LifeScoreDetailResponse:
    """Force recalculation of Life Score.
    
    Validates: Requirements 33.1, 33.2
    
    Recalculates the Life Score for the specified date based on
    activity across all modules, weighted by importance and recency.
    
    Args:
        current_user: Authenticated user
        db: Database session
        score_date: Date to calculate score for (defaults to today)
        
    Returns:
        Recalculated Life Score with breakdown
    """
    if score_date is None:
        score_date = date.today()
    
    service = LifeScoreService(db)
    
    # Calculate and store
    result = await service.calculate_life_score(current_user.id, score_date)
    life_score = await service.calculate_and_store_score(current_user.id, score_date)
    
    return LifeScoreDetailResponse(
        id=life_score.id,
        user_id=life_score.user_id,
        score_date=life_score.score_date,
        total_score=life_score.total_score,
        activity_count=life_score.activity_count,
        breakdown=result.breakdown,
        created_at=life_score.created_at,
        updated_at=life_score.updated_at,
    )
