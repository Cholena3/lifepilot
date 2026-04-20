"""Pydantic schemas for exam feed and discovery module.

Implements Requirements 3.1-3.8 for exam feed, filtering, and tracking.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.exam import ApplicationStatus, ExamType


# ============================================================================
# Exam Schemas
# ============================================================================

class ExamCreate(BaseModel):
    """Schema for creating a new exam (admin/scraper use)."""
    name: str = Field(..., min_length=1, max_length=255, description="Exam name")
    organization: str = Field(..., min_length=1, max_length=255, description="Organization")
    exam_type: ExamType = Field(..., description="Type of exam")
    description: Optional[str] = Field(None, description="Exam description")
    registration_start: Optional[date] = Field(None, description="Registration start date")
    registration_end: Optional[date] = Field(None, description="Registration deadline")
    exam_date: Optional[date] = Field(None, description="Exam date")
    min_cgpa: Optional[Decimal] = Field(None, ge=0, le=10, description="Minimum CGPA required")
    max_backlogs: Optional[int] = Field(None, ge=0, description="Maximum backlogs allowed")
    eligible_degrees: Optional[list[str]] = Field(default_factory=list, description="Eligible degrees")
    eligible_branches: Optional[list[str]] = Field(default_factory=list, description="Eligible branches")
    graduation_year_min: Optional[int] = Field(None, description="Minimum graduation year")
    graduation_year_max: Optional[int] = Field(None, description="Maximum graduation year")
    syllabus: Optional[str] = Field(None, description="Exam syllabus")
    cutoffs: Optional[dict[str, Any]] = Field(default_factory=dict, description="Cutoff information")
    resources: Optional[list[dict[str, str]]] = Field(default_factory=list, description="Resource links")
    source_url: Optional[str] = Field(None, max_length=500, description="Source URL")

    @field_validator("name", "organization")
    @classmethod
    def validate_string_fields(cls, v: str) -> str:
        """Validate and normalize string fields."""
        return v.strip()


class ExamUpdate(BaseModel):
    """Schema for updating an exam."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    organization: Optional[str] = Field(None, min_length=1, max_length=255)
    exam_type: Optional[ExamType] = None
    description: Optional[str] = None
    registration_start: Optional[date] = None
    registration_end: Optional[date] = None
    exam_date: Optional[date] = None
    min_cgpa: Optional[Decimal] = Field(None, ge=0, le=10)
    max_backlogs: Optional[int] = Field(None, ge=0)
    eligible_degrees: Optional[list[str]] = None
    eligible_branches: Optional[list[str]] = None
    graduation_year_min: Optional[int] = None
    graduation_year_max: Optional[int] = None
    syllabus: Optional[str] = None
    cutoffs: Optional[dict[str, Any]] = None
    resources: Optional[list[dict[str, str]]] = None
    is_active: Optional[bool] = None


class ExamResponse(BaseModel):
    """Schema for exam response in feed."""
    id: UUID
    name: str
    organization: str
    exam_type: ExamType
    description: Optional[str]
    registration_start: Optional[date]
    registration_end: Optional[date]
    exam_date: Optional[date]
    min_cgpa: Optional[Decimal]
    max_backlogs: Optional[int]
    eligible_degrees: Optional[list[str]]
    eligible_branches: Optional[list[str]]
    graduation_year_min: Optional[int]
    graduation_year_max: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamDetailResponse(ExamResponse):
    """Schema for detailed exam response.
    
    Requirement 3.8: Return syllabus, cutoffs, previous papers, and resource links
    """
    syllabus: Optional[str]
    cutoffs: Optional[dict[str, Any]]
    resources: Optional[list[dict[str, str]]]
    source_url: Optional[str]
    is_bookmarked: bool = False
    is_applied: bool = False
    application_status: Optional[ApplicationStatus] = None


# ============================================================================
# Filter Schemas
# ============================================================================

class ExamFilters(BaseModel):
    """Schema for exam feed filters.
    
    Requirement 3.1: Filter by degree, branch, graduation year
    Requirement 3.2: Apply CGPA filter
    Requirement 3.3: Apply backlog filter
    Requirement 3.4: Filter by exam type
    """
    exam_type: Optional[ExamType] = Field(None, description="Filter by exam type")
    degree: Optional[str] = Field(None, description="Filter by eligible degree")
    branch: Optional[str] = Field(None, description="Filter by eligible branch")
    graduation_year: Optional[int] = Field(None, description="Filter by graduation year")
    min_cgpa: Optional[Decimal] = Field(None, ge=0, le=10, description="User's CGPA for filtering")
    backlogs: Optional[int] = Field(None, ge=0, description="User's backlog count for filtering")
    search: Optional[str] = Field(None, description="Search in name and organization")
    upcoming_only: bool = Field(False, description="Show only exams with future deadlines")


# ============================================================================
# Bookmark Schemas
# ============================================================================

class ExamBookmarkCreate(BaseModel):
    """Schema for creating an exam bookmark."""
    exam_id: UUID = Field(..., description="ID of the exam to bookmark")


class ExamBookmarkResponse(BaseModel):
    """Schema for exam bookmark response."""
    id: UUID
    user_id: UUID
    exam_id: UUID
    created_at: datetime
    exam: Optional[ExamResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Application Schemas
# ============================================================================

class ExamApplicationCreate(BaseModel):
    """Schema for marking an exam as applied.
    
    Requirement 3.6: Record application date and update status
    """
    exam_id: UUID = Field(..., description="ID of the exam")
    applied_date: Optional[date] = Field(None, description="Date of application")
    notes: Optional[str] = Field(None, description="Notes about the application")


class ExamApplicationUpdate(BaseModel):
    """Schema for updating an exam application."""
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None


class ExamApplicationResponse(BaseModel):
    """Schema for exam application response."""
    id: UUID
    user_id: UUID
    exam_id: UUID
    status: ApplicationStatus
    applied_date: date
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    exam: Optional[ExamResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Feed Response Schemas
# ============================================================================

class ExamFeedResponse(BaseModel):
    """Schema for paginated exam feed response."""
    items: list[ExamResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[ExamResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "ExamFeedResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ExamsByTypeResponse(BaseModel):
    """Schema for exams grouped by type.
    
    Requirement 3.4: Categorize exams by type
    """
    exam_type: ExamType
    exams: list[ExamResponse]
    count: int


class ExamFeedGroupedResponse(BaseModel):
    """Schema for exam feed grouped by type."""
    groups: list[ExamsByTypeResponse]
    total_exams: int
