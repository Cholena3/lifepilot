"""Analytics router for spending analytics endpoints.

Provides endpoints for spending analytics including category breakdown,
spending trends, period comparison, and unusual spending detection.

Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
"""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.analytics import (
    CategoryBreakdownResponse,
    PeriodComparisonResponse,
    SpendingAnalyticsResponse,
    SpendingTrendsResponse,
    UnusualSpendingResponse,
)
from app.services.analytics import AnalyticsService

router = APIRouter()


def _get_default_date_range() -> tuple[date, date]:
    """Get default date range (current month)."""
    today = date.today()
    start_date = today.replace(day=1)
    # End date is today
    end_date = today
    return start_date, end_date


def _validate_date_range(start_date: date, end_date: date) -> None:
    """Validate date range parameters.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Raises:
        HTTPException: If date range is invalid
    """
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
    "",
    response_model=SpendingAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full spending analytics",
    description="Get comprehensive spending analytics including category breakdown, trends, period comparison, and unusual patterns.",
    responses={
        200: {"description": "Analytics returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid date range"},
    },
)
async def get_spending_analytics(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Annotated[
        date | None,
        Query(description="Start date of the analysis period (defaults to first day of current month)")
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date of the analysis period (defaults to today)")
    ] = None,
) -> SpendingAnalyticsResponse:
    """Get comprehensive spending analytics.
    
    Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
    
    Returns category breakdown, spending trends, period comparison,
    and unusual spending patterns for the specified date range.
    
    Args:
        current_user: Authenticated user
        db: Database session
        start_date: Start date (defaults to first day of current month)
        end_date: End date (defaults to today)
        
    Returns:
        Complete spending analytics
    """
    # Use defaults if not provided
    if start_date is None or end_date is None:
        default_start, default_end = _get_default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    
    _validate_date_range(start_date, end_date)
    
    service = AnalyticsService(db)
    return await service.get_full_analytics(current_user.id, start_date, end_date)


@router.get(
    "/categories",
    response_model=CategoryBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Get spending by category",
    description="Get spending breakdown by category with percentages for chart visualization.",
    responses={
        200: {"description": "Category breakdown returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid date range"},
    },
)
async def get_category_breakdown(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Annotated[
        date | None,
        Query(description="Start date of the analysis period")
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date of the analysis period")
    ] = None,
) -> CategoryBreakdownResponse:
    """Get spending breakdown by category.
    
    Validates: Requirements 12.1, 12.4
    
    Returns spending totals and percentages for each category,
    suitable for pie/donut chart visualization.
    
    Args:
        current_user: Authenticated user
        db: Database session
        start_date: Start date (defaults to first day of current month)
        end_date: End date (defaults to today)
        
    Returns:
        Category breakdown with spending per category
    """
    if start_date is None or end_date is None:
        default_start, default_end = _get_default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    
    _validate_date_range(start_date, end_date)
    
    service = AnalyticsService(db)
    return await service.get_category_breakdown(current_user.id, start_date, end_date)


@router.get(
    "/trends",
    response_model=SpendingTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get spending trends",
    description="Get daily spending trends over time for line chart visualization.",
    responses={
        200: {"description": "Spending trends returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid date range"},
    },
)
async def get_spending_trends(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Annotated[
        date | None,
        Query(description="Start date of the analysis period")
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date of the analysis period")
    ] = None,
) -> SpendingTrendsResponse:
    """Get spending trends over time.
    
    Validates: Requirements 12.2, 12.4
    
    Returns daily spending data suitable for line chart visualization.
    
    Args:
        current_user: Authenticated user
        db: Database session
        start_date: Start date (defaults to first day of current month)
        end_date: End date (defaults to today)
        
    Returns:
        Spending trends with daily data points
    """
    if start_date is None or end_date is None:
        default_start, default_end = _get_default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    
    _validate_date_range(start_date, end_date)
    
    service = AnalyticsService(db)
    return await service.get_spending_trends(current_user.id, start_date, end_date)


@router.get(
    "/comparison",
    response_model=PeriodComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare spending periods",
    description="Compare current period spending with the previous period of equal duration.",
    responses={
        200: {"description": "Period comparison returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid date range"},
    },
)
async def get_period_comparison(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Annotated[
        date | None,
        Query(description="Start date of the current period")
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date of the current period")
    ] = None,
) -> PeriodComparisonResponse:
    """Compare current period with previous period.
    
    Validates: Requirements 12.3, 12.4
    
    Compares spending in the specified period with the immediately
    preceding period of equal duration.
    
    Args:
        current_user: Authenticated user
        db: Database session
        start_date: Current period start date (defaults to first day of current month)
        end_date: Current period end date (defaults to today)
        
    Returns:
        Period comparison with change metrics
    """
    if start_date is None or end_date is None:
        default_start, default_end = _get_default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    
    _validate_date_range(start_date, end_date)
    
    service = AnalyticsService(db)
    return await service.get_period_comparison(current_user.id, start_date, end_date)


@router.get(
    "/unusual",
    response_model=UnusualSpendingResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect unusual spending",
    description="Identify and highlight unusual spending patterns in the specified period.",
    responses={
        200: {"description": "Unusual patterns returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid date range"},
    },
)
async def detect_unusual_spending(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: Annotated[
        date | None,
        Query(description="Start date of the analysis period")
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date of the analysis period")
    ] = None,
) -> UnusualSpendingResponse:
    """Detect unusual spending patterns.
    
    Validates: Requirements 12.5
    
    Identifies unusual patterns including:
    - High single expenses (significantly above average)
    - Category spending spikes (compared to historical average)
    - Daily spending spikes
    - First-time spending in new categories
    
    Args:
        current_user: Authenticated user
        db: Database session
        start_date: Start date (defaults to first day of current month)
        end_date: End date (defaults to today)
        
    Returns:
        Detected unusual spending patterns
    """
    if start_date is None or end_date is None:
        default_start, default_end = _get_default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    
    _validate_date_range(start_date, end_date)
    
    service = AnalyticsService(db)
    return await service.detect_unusual_spending(current_user.id, start_date, end_date)
