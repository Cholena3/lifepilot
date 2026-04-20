"""Pydantic schemas for Life Score gamification.

Requirement 33: Life Score Gamification
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.life_score import ModuleType


class ModuleScoreBreakdown(BaseModel):
    """Score breakdown for a single module.
    
    Requirement 33.6: Show breakdown of score by module
    """
    module: ModuleType = Field(..., description="Module type")
    score: int = Field(..., ge=0, description="Module score contribution")
    activity_count: int = Field(..., ge=0, description="Number of activities in this module")
    percentage: Decimal = Field(..., ge=0, le=100, description="Percentage of total score")


class LifeScoreResponse(BaseModel):
    """Response schema for Life Score.
    
    Requirement 33.1, 33.4, 33.6
    """
    id: UUID
    user_id: UUID
    score_date: date
    total_score: int = Field(..., ge=0, le=100, description="Total life score (0-100)")
    module_scores: dict[str, int] = Field(..., description="Scores per module")
    activity_count: int = Field(..., ge=0, description="Total activities counted")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LifeScoreDetailResponse(BaseModel):
    """Detailed Life Score response with module breakdown.
    
    Requirement 33.6: Show breakdown of score by module
    """
    id: UUID
    user_id: UUID
    score_date: date
    total_score: int = Field(..., ge=0, le=100, description="Total life score (0-100)")
    activity_count: int = Field(..., ge=0, description="Total activities counted")
    breakdown: list[ModuleScoreBreakdown] = Field(..., description="Score breakdown by module")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LifeScoreTrendPoint(BaseModel):
    """Single point in Life Score trend.
    
    Requirement 33.4: Display Life Score trends over time
    """
    score_date: date
    total_score: int = Field(..., ge=0, le=100)
    activity_count: int = Field(..., ge=0)


class LifeScoreTrendResponse(BaseModel):
    """Response schema for Life Score trends.
    
    Requirement 33.4: Display Life Score trends over time
    """
    start_date: date
    end_date: date
    current_score: int = Field(..., ge=0, le=100, description="Most recent score")
    average_score: Decimal = Field(..., ge=0, le=100, description="Average score in period")
    trend_direction: str = Field(..., description="'up', 'down', or 'stable'")
    score_change: int = Field(..., description="Change from start to end of period")
    data_points: list[LifeScoreTrendPoint] = Field(..., description="Daily score data points")


class LifeScoreCalculationResult(BaseModel):
    """Result of Life Score calculation.
    
    Requirement 33.1, 33.2
    """
    total_score: int = Field(..., ge=0, le=100)
    module_scores: dict[str, int]
    activity_count: int
    breakdown: list[ModuleScoreBreakdown]


class LifeScoreComparisonResponse(BaseModel):
    """Response for comparing Life Score between periods.
    
    Requirement 33.4
    """
    current_score: int = Field(..., ge=0, le=100)
    previous_score: int = Field(..., ge=0, le=100)
    score_change: int
    change_percentage: Optional[Decimal] = Field(None, description="Percentage change")
    current_date: date
    previous_date: date


class PaginatedLifeScoreResponse(BaseModel):
    """Paginated Life Score history response."""
    items: list[LifeScoreResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[LifeScoreResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedLifeScoreResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
