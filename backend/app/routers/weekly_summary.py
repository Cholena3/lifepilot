"""Weekly Summary router for viewing and generating weekly summaries.

Provides endpoints for weekly summary management.

Validates: Requirements 34.1, 34.5
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.weekly_summary import (
    WeeklySummaryGenerateRequest,
    WeeklySummaryListResponse,
    WeeklySummaryResponse,
)
from app.services.weekly_summary import WeeklySummaryService, get_week_boundaries

router = APIRouter()


@router.get(
    "",
    response_model=WeeklySummaryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get past weekly summaries",
    description="Get paginated list of past weekly summaries for the authenticated user.",
    responses={
        200: {"description": "Weekly summaries returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_weekly_summaries(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=50, description="Number of items per page")
    ] = 10,
) -> WeeklySummaryListResponse:
    """Get paginated list of past weekly summaries.
    
    Validates: Requirements 34.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Paginated list of weekly summaries
    """
    service = WeeklySummaryService(db)
    return await service.get_past_summaries(current_user.id, page, page_size)


@router.get(
    "/latest",
    response_model=WeeklySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest weekly summary",
    description="Get the most recent weekly summary for the authenticated user.",
    responses={
        200: {"description": "Latest weekly summary returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "No weekly summaries found"},
    },
)
async def get_latest_weekly_summary(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WeeklySummaryResponse:
    """Get the most recent weekly summary.
    
    Validates: Requirements 34.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Most recent weekly summary
        
    Raises:
        HTTPException: If no summaries exist
    """
    service = WeeklySummaryService(db)
    summary = await service.get_latest_summary(current_user.id)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly summaries found. Summaries are generated automatically at the end of each week.",
        )
    
    return summary


@router.get(
    "/week/{week_start}",
    response_model=WeeklySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get weekly summary for specific week",
    description="Get the weekly summary for a specific week by its start date (Monday).",
    responses={
        200: {"description": "Weekly summary returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Weekly summary not found for the specified week"},
    },
)
async def get_weekly_summary_by_week(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    week_start: date,
) -> WeeklySummaryResponse:
    """Get weekly summary for a specific week.
    
    Validates: Requirements 34.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        week_start: Start date of the week (Monday)
        
    Returns:
        Weekly summary for the specified week
        
    Raises:
        HTTPException: If summary not found
    """
    # Normalize to Monday of the week
    normalized_start, _ = get_week_boundaries(week_start)
    
    service = WeeklySummaryService(db)
    summary = await service.get_summary(current_user.id, normalized_start)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No weekly summary found for week starting {normalized_start}",
        )
    
    return summary


@router.post(
    "/generate",
    response_model=WeeklySummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate weekly summary",
    description="Manually generate a weekly summary for a specific week. Useful for generating summaries for past weeks.",
    responses={
        201: {"description": "Weekly summary generated successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid week start date"},
    },
)
async def generate_weekly_summary(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: WeeklySummaryGenerateRequest,
) -> WeeklySummaryResponse:
    """Manually generate a weekly summary.
    
    Validates: Requirements 34.1
    
    This endpoint allows users to manually trigger summary generation,
    which is useful for:
    - Generating summaries for past weeks
    - Regenerating a summary with updated data
    
    Args:
        current_user: Authenticated user
        db: Database session
        request: Generation request with optional week_start
        
    Returns:
        Generated weekly summary
    """
    service = WeeklySummaryService(db)
    
    # Generate the summary (without sending notification for manual generation)
    summary = await service.generate_weekly_summary(
        current_user.id,
        request.week_start,
    )
    
    await db.commit()
    
    return service._to_response(summary)


@router.post(
    "/generate-and-notify",
    response_model=WeeklySummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate weekly summary and send notification",
    description="Generate a weekly summary and send it via the user's preferred notification channel.",
    responses={
        201: {"description": "Weekly summary generated and notification sent"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid week start date"},
    },
)
async def generate_and_notify_weekly_summary(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: WeeklySummaryGenerateRequest,
) -> WeeklySummaryResponse:
    """Generate a weekly summary and send notification.
    
    Validates: Requirements 34.1, 34.4
    
    Args:
        current_user: Authenticated user
        db: Database session
        request: Generation request with optional week_start
        
    Returns:
        Generated weekly summary
    """
    service = WeeklySummaryService(db)
    
    # Generate and send notification
    summary, notification_sent = await service.generate_and_send_summary(
        current_user.id,
        request.week_start,
    )
    
    await db.commit()
    
    return service._to_response(summary)
