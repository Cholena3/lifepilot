"""Pydantic schemas for achievement logging.

Requirement 29: Achievement Logging
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.achievement import AchievementCategory


class AchievementCreate(BaseModel):
    """Schema for creating a new achievement.
    
    Requirement 29.1: Store title, description, date, and category
    Requirement 29.3: Allow attaching supporting documents
    """
    title: str = Field(..., min_length=1, max_length=255, description="Achievement title")
    description: Optional[str] = Field(None, description="Detailed description")
    achieved_date: date = Field(..., description="Date when the achievement was earned")
    category: AchievementCategory = Field(
        default=AchievementCategory.OTHER,
        description="Achievement category"
    )
    document_ids: Optional[list[UUID]] = Field(
        default=None,
        description="List of document IDs to attach"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate and normalize achievement title."""
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize description."""
        if v is not None:
            return v.strip() or None
        return v


class AchievementUpdate(BaseModel):
    """Schema for updating an existing achievement."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    achieved_date: Optional[date] = None
    category: Optional[AchievementCategory] = None
    document_ids: Optional[list[UUID]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize achievement title."""
        if v is not None:
            return v.strip()
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize description."""
        if v is not None:
            return v.strip() or None
        return v


class AchievementResponse(BaseModel):
    """Schema for achievement response.
    
    Requirement 29.5: Display achievements on a timeline view
    """
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    achieved_date: date
    category: AchievementCategory
    document_ids: Optional[list[UUID]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AchievementTimelineResponse(BaseModel):
    """Schema for achievement timeline response.
    
    Requirement 29.5: Display achievements on a timeline view
    Groups achievements by year for timeline display.
    """
    year: int
    achievements: list[AchievementResponse]


class AchievementsByCategory(BaseModel):
    """Schema for achievements grouped by category."""
    category: AchievementCategory
    achievements: list[AchievementResponse]
    count: int


class AchievementsGroupedResponse(BaseModel):
    """Schema for achievements grouped by category response."""
    groups: list[AchievementsByCategory]
    total_achievements: int


class PaginatedAchievementResponse(BaseModel):
    """Schema for paginated achievement list response."""
    items: list[AchievementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[AchievementResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedAchievementResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class AchievementSuggestion(BaseModel):
    """Schema for achievement suggestion for resume building.
    
    Requirement 29.4: Suggest relevant achievements to include when building a resume
    """
    achievement: AchievementResponse
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score for resume inclusion (0-1)"
    )
    reason: str = Field(
        default="Relevant achievement",
        description="Reason for suggesting this achievement"
    )


class AchievementSuggestionsResponse(BaseModel):
    """Schema for achievement suggestions response."""
    suggestions: list[AchievementSuggestion]
    total_achievements: int
