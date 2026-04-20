"""Pydantic schemas for career roadmap management.

Validates: Requirements 26.1, 26.2, 26.3, 26.4, 26.5
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.roadmap import MilestoneStatus, ResourceType


class CareerGoalCreate(BaseModel):
    """Schema for creating a career goal and generating a roadmap.
    
    Requirement 26.1: Set career goals to generate roadmap
    """
    target_role: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Target career role/position"
    )
    target_timeline_months: int = Field(
        default=12,
        ge=1,
        le=60,
        description="Target timeline in months"
    )
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional notes about career goals"
    )

    @field_validator("target_role")
    @classmethod
    def validate_target_role(cls, v: str) -> str:
        """Validate and normalize target role."""
        return v.strip()


class RoadmapUpdate(BaseModel):
    """Schema for updating a roadmap."""
    target_role: Optional[str] = Field(None, min_length=1, max_length=255)
    target_timeline_months: Optional[int] = Field(None, ge=1, le=60)
    notes: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None

    @field_validator("target_role")
    @classmethod
    def validate_target_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize target role."""
        if v is not None:
            return v.strip()
        return v


class MilestoneCreate(BaseModel):
    """Schema for creating a milestone."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    target_date: Optional[date] = None
    required_skills: Optional[list[str]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate and normalize title."""
        return v.strip()


class MilestoneUpdate(BaseModel):
    """Schema for updating a milestone.
    
    Requirement 26.4: Update milestone completion
    """
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    target_date: Optional[date] = None
    status: Optional[MilestoneStatus] = None
    required_skills: Optional[list[str]] = None


class MilestoneResponse(BaseModel):
    """Schema for milestone response.
    
    Requirement 26.1: Roadmap milestones
    """
    id: UUID
    roadmap_id: UUID
    title: str
    description: Optional[str]
    order_index: int
    target_date: Optional[date]
    completed_at: Optional[datetime]
    status: MilestoneStatus
    required_skills: Optional[list[str]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceRecommendationResponse(BaseModel):
    """Schema for resource recommendation response.
    
    Requirement 26.3: Recommend courses and resources
    """
    id: UUID
    skill_gap_id: UUID
    title: str
    resource_type: ResourceType
    url: Optional[str]
    platform: Optional[str]
    estimated_hours: Optional[Decimal]
    is_completed: bool
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillGapResponse(BaseModel):
    """Schema for skill gap response.
    
    Requirement 26.2: Identify skill gaps
    """
    id: UUID
    roadmap_id: UUID
    skill_name: str
    current_level: Optional[str]
    required_level: str
    priority: int
    is_filled: bool
    recommendations: list[ResourceRecommendationResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoadmapResponse(BaseModel):
    """Schema for roadmap response.
    
    Requirement 26.1: Career roadmap with milestones
    """
    id: UUID
    user_id: UUID
    target_role: str
    target_timeline_months: int
    current_progress: int
    is_active: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoadmapDetailResponse(RoadmapResponse):
    """Schema for detailed roadmap response with milestones and skill gaps."""
    milestones: list[MilestoneResponse] = []
    skill_gaps: list[SkillGapResponse] = []


class SkillGapSummary(BaseModel):
    """Summary of skill gaps for a roadmap.
    
    Requirement 26.2: Skill gap analysis
    """
    total_gaps: int
    filled_gaps: int
    unfilled_gaps: int
    high_priority_gaps: list[SkillGapResponse]


class RoadmapProgressResponse(BaseModel):
    """Schema for roadmap progress summary.
    
    Requirement 26.4: Track milestone completion
    """
    roadmap_id: UUID
    target_role: str
    overall_progress: int
    milestones_total: int
    milestones_completed: int
    milestones_in_progress: int
    skill_gaps_total: int
    skill_gaps_filled: int
    estimated_completion_date: Optional[date]


class ResourceCompletionUpdate(BaseModel):
    """Schema for marking a resource as completed."""
    is_completed: bool = True


class SkillGapUpdate(BaseModel):
    """Schema for updating a skill gap."""
    is_filled: bool


class PaginatedRoadmapResponse(BaseModel):
    """Schema for paginated roadmap list response."""
    items: list[RoadmapResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[RoadmapResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedRoadmapResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
