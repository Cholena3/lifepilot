"""Pydantic schemas for learning progress tracking.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CourseCreate(BaseModel):
    """Schema for creating a new course.
    
    Requirement 25.1: Store course name, platform, URL, and total duration
    """
    title: str = Field(..., min_length=1, max_length=255, description="Course title")
    platform: Optional[str] = Field(None, max_length=100, description="Learning platform")
    url: Optional[str] = Field(None, description="Course URL")
    total_hours: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=9999.99,
        description="Total course duration in hours"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate and normalize course title."""
        return v.strip()

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize platform name."""
        if v is not None:
            return v.strip()
        return v


class CourseUpdate(BaseModel):
    """Schema for updating an existing course."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    platform: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = None
    total_hours: Optional[Decimal] = Field(None, ge=0, le=9999.99)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize course title."""
        if v is not None:
            return v.strip()
        return v


class LearningSessionCreate(BaseModel):
    """Schema for logging a learning session.
    
    Requirement 25.2: Log progress updates
    """
    session_date: date = Field(default_factory=date.today, description="Date of the session")
    duration_minutes: int = Field(
        ...,
        gt=0,
        le=1440,  # Max 24 hours
        description="Duration in minutes"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Session notes")


class LearningSessionResponse(BaseModel):
    """Schema for learning session response."""
    id: UUID
    course_id: UUID
    session_date: date
    duration_minutes: int
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseResponse(BaseModel):
    """Schema for course response.
    
    Requirement 25.2: Display completion percentage
    """
    id: UUID
    user_id: UUID
    title: str
    platform: Optional[str]
    url: Optional[str]
    total_hours: Decimal
    completed_hours: Decimal
    completion_percentage: int
    is_completed: bool
    last_activity_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseWithSessionsResponse(CourseResponse):
    """Schema for course response with learning sessions."""
    learning_sessions: list[LearningSessionResponse] = []


class LearningStatsResponse(BaseModel):
    """Schema for learning statistics.
    
    Requirement 25.3: Display learning streak and total hours invested
    """
    total_courses: int = Field(description="Total number of courses")
    completed_courses: int = Field(description="Number of completed courses")
    in_progress_courses: int = Field(description="Number of courses in progress")
    total_hours_invested: Decimal = Field(description="Total hours spent learning")
    current_streak_days: int = Field(description="Current learning streak in days")
    longest_streak_days: int = Field(description="Longest learning streak in days")


class InactiveCourseResponse(BaseModel):
    """Schema for inactive course reminder.
    
    Requirement 25.5: Identify courses with no progress in 7 days
    """
    course_id: UUID
    title: str
    platform: Optional[str]
    days_inactive: int
    last_activity_at: Optional[datetime]
    completion_percentage: int


class PaginatedCourseResponse(BaseModel):
    """Schema for paginated course list response."""
    items: list[CourseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[CourseResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedCourseResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class CourseProgressUpdate(BaseModel):
    """Schema for updating course progress directly.
    
    Requirement 25.2: Update completion percentage
    """
    completion_percentage: int = Field(
        ...,
        ge=0,
        le=100,
        description="Completion percentage (0-100)"
    )
