"""API router for Badge gamification.

Requirement 33.5: Award badges for achievements and milestones
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.badge import BadgeType
from app.schemas.badge import (
    AllBadgesResponse,
    BadgeAwardRequest,
    BadgeAwardResponse,
    BadgeListResponse,
)
from app.services.badge import BadgeService

router = APIRouter()


@router.get(
    "",
    response_model=BadgeListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user badges",
    description="Get all badges earned by the current user.",
    responses={
        200: {"description": "Badges returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_user_badges(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BadgeListResponse:
    """Get all badges earned by the current user.
    
    Validates: Requirements 33.5
    
    Returns a list of all badges the user has earned, ordered by
    most recently earned first.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of earned badges with total count
    """
    service = BadgeService(db)
    return await service.get_user_badges(current_user.id)


@router.get(
    "/all",
    response_model=AllBadgesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all badges with status",
    description="Get all available badges with earned status for the current user.",
    responses={
        200: {"description": "All badges returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_all_badges_with_status(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AllBadgesResponse:
    """Get all available badges with earned status.
    
    Validates: Requirements 33.5
    
    Returns a list of all available badge types with information about
    whether the current user has earned each one.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        All badges with earned status and counts
    """
    service = BadgeService(db)
    return await service.get_all_badges_with_status(current_user.id)


@router.post(
    "/check",
    response_model=list[BadgeAwardResponse],
    status_code=status.HTTP_200_OK,
    summary="Check and award milestone badges",
    description="Check all milestones and award any badges the user has earned.",
    responses={
        200: {"description": "Badges checked and awarded successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def check_and_award_badges(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BadgeAwardResponse]:
    """Check and award all applicable milestone badges.
    
    Validates: Requirements 33.5
    
    Checks various milestones across all modules and awards any badges
    that the user has earned but not yet received.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of newly awarded badges
    """
    service = BadgeService(db)
    return await service.check_and_award_milestone_badges(current_user.id)


@router.post(
    "/award",
    response_model=BadgeAwardResponse,
    status_code=status.HTTP_200_OK,
    summary="Award a specific badge",
    description="Award a specific badge to the current user (for testing/admin).",
    responses={
        200: {"description": "Badge awarded successfully"},
        401: {"description": "Not authenticated"},
        400: {"description": "Invalid badge type"},
    },
)
async def award_badge(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: BadgeAwardRequest,
) -> BadgeAwardResponse:
    """Award a specific badge to the current user.
    
    Validates: Requirements 33.5
    
    This endpoint is primarily for testing and admin purposes.
    In normal operation, badges are awarded automatically through
    the check_and_award_badges endpoint.
    
    Args:
        current_user: Authenticated user
        db: Database session
        request: Badge award request with badge type
        
    Returns:
        Badge award response with status
    """
    service = BadgeService(db)
    return await service.award_badge(current_user.id, request.badge_type)
