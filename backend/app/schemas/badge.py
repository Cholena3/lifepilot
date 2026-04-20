"""Pydantic schemas for Badge gamification.

Requirement 33.5: Award badges for achievements and milestones
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.badge import BadgeType


class BadgeResponse(BaseModel):
    """Response schema for a Badge.
    
    Requirement 33.5: Award badges for achievements and milestones
    """
    id: UUID
    user_id: UUID
    badge_type: str = Field(..., description="Type of badge earned")
    name: str = Field(..., description="Display name of the badge")
    description: str = Field(..., description="Description of how the badge was earned")
    earned_at: datetime = Field(..., description="When the badge was earned")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BadgeAwardRequest(BaseModel):
    """Request schema for awarding a badge.
    
    Requirement 33.5: Award badges for achievements and milestones
    """
    badge_type: BadgeType = Field(..., description="Type of badge to award")


class BadgeAwardResponse(BaseModel):
    """Response schema for badge award operation.
    
    Requirement 33.5: Award badges for achievements and milestones
    """
    badge: Optional[BadgeResponse] = Field(None, description="The awarded badge, if new")
    already_earned: bool = Field(..., description="Whether the badge was already earned")
    message: str = Field(..., description="Status message")


class BadgeListResponse(BaseModel):
    """Response schema for listing user badges.
    
    Requirement 33.5: Award badges for achievements and milestones
    """
    badges: list[BadgeResponse] = Field(..., description="List of earned badges")
    total_count: int = Field(..., ge=0, description="Total number of badges earned")


class BadgeTypeInfo(BaseModel):
    """Information about a badge type.
    
    Requirement 33.5: Award badges for achievements and milestones
    """
    badge_type: str = Field(..., description="Badge type identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Description of how to earn")
    earned: bool = Field(..., description="Whether the user has earned this badge")
    earned_at: Optional[datetime] = Field(None, description="When earned, if applicable")


class AllBadgesResponse(BaseModel):
    """Response schema for all available badges with earned status.
    
    Requirement 33.5: Award badges for achievements and milestones
    """
    badges: list[BadgeTypeInfo] = Field(..., description="All available badges with status")
    earned_count: int = Field(..., ge=0, description="Number of badges earned")
    total_count: int = Field(..., ge=0, description="Total number of available badges")
