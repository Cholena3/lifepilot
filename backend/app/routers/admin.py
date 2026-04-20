"""Admin analytics router for admin dashboard endpoints.

Provides admin-only endpoints for user metrics, feature usage statistics,
system performance metrics, and scraper status.

Validates: Requirements 38.1, 38.2, 38.3, 38.4
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminUser
from app.schemas.admin import (
    FeatureUsageResponse,
    ScraperStatusResponse,
    SystemPerformanceResponse,
    UserMetricsResponse,
)
from app.services.admin_analytics import AdminAnalyticsService

router = APIRouter()


@router.get(
    "/users",
    response_model=UserMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user metrics",
    description="Get user metrics including total users, active users, and growth trends. Admin only.",
    responses={
        200: {"description": "User metrics returned successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_user_metrics(
    admin_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserMetricsResponse:
    """Get user metrics for admin dashboard.
    
    Validates: Requirements 38.1
    
    Returns user counts, active user statistics, and growth trends
    for the admin dashboard.
    
    Args:
        admin_user: Authenticated admin user
        db: Database session
        
    Returns:
        User metrics including counts and growth data
    """
    service = AdminAnalyticsService(db)
    return await service.get_user_metrics()


@router.get(
    "/features",
    response_model=FeatureUsageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get feature usage statistics",
    description="Get feature usage statistics by module. Admin only.",
    responses={
        200: {"description": "Feature usage statistics returned successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_feature_usage(
    admin_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureUsageResponse:
    """Get feature usage statistics for admin dashboard.
    
    Validates: Requirements 38.2
    
    Returns usage statistics for each module including total records,
    active users, and recent activity.
    
    Args:
        admin_user: Authenticated admin user
        db: Database session
        
    Returns:
        Feature usage statistics by module
    """
    service = AdminAnalyticsService(db)
    return await service.get_feature_usage()


@router.get(
    "/performance",
    response_model=SystemPerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get system performance metrics",
    description="Get system performance metrics including response times and error rates. Admin only.",
    responses={
        200: {"description": "System performance metrics returned successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_system_performance(
    admin_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SystemPerformanceResponse:
    """Get system performance metrics for admin dashboard.
    
    Validates: Requirements 38.3
    
    Returns system performance metrics including average response times,
    error rates, and infrastructure health status.
    
    Args:
        admin_user: Authenticated admin user
        db: Database session
        
    Returns:
        System performance metrics
    """
    service = AdminAnalyticsService(db)
    return await service.get_system_performance()


@router.get(
    "/scrapers",
    response_model=ScraperStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get scraper job status",
    description="Get status of all scraper jobs including last run times and success rates. Admin only.",
    responses={
        200: {"description": "Scraper status returned successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin access required"},
    },
)
async def get_scraper_status(
    admin_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScraperStatusResponse:
    """Get scraper job status for admin dashboard.
    
    Validates: Requirements 38.4
    
    Returns status of all configured scraper jobs including last run
    timestamps, success/failure status, and overall scraper health.
    
    Args:
        admin_user: Authenticated admin user
        db: Database session
        
    Returns:
        Scraper job status information
    """
    service = AdminAnalyticsService(db)
    return await service.get_scraper_status()
