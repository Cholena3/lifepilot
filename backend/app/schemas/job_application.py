"""Pydantic schemas for job application tracking.

Validates: Requirements 27.1, 27.2, 27.3, 27.4, 27.5, 27.6
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.job_application import ApplicationSource, ApplicationStatus


class JobApplicationCreate(BaseModel):
    """Schema for creating a new job application.
    
    Requirement 27.1: Store company, role, date, source, and status
    """
    company: str = Field(..., min_length=1, max_length=255, description="Company name")
    role: str = Field(..., min_length=1, max_length=255, description="Job role/position")
    url: Optional[str] = Field(None, description="Job posting URL")
    source: ApplicationSource = Field(
        default=ApplicationSource.OTHER,
        description="Where the job was found"
    )
    status: ApplicationStatus = Field(
        default=ApplicationStatus.APPLIED,
        description="Current application status"
    )
    salary_min: Optional[Decimal] = Field(
        None,
        ge=0,
        le=999999999999.99,
        description="Minimum salary"
    )
    salary_max: Optional[Decimal] = Field(
        None,
        ge=0,
        le=999999999999.99,
        description="Maximum salary"
    )
    applied_date: date = Field(
        default_factory=date.today,
        description="Date when application was submitted"
    )
    notes: Optional[str] = Field(None, max_length=5000, description="Additional notes")
    location: Optional[str] = Field(None, max_length=255, description="Job location")
    is_remote: bool = Field(default=False, description="Whether the job is remote")

    @field_validator("company", "role")
    @classmethod
    def validate_string_fields(cls, v: str) -> str:
        """Validate and normalize string fields."""
        return v.strip()

    @model_validator(mode="after")
    def validate_salary_range(self) -> "JobApplicationCreate":
        """Validate that salary_min <= salary_max if both are provided."""
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min must be less than or equal to salary_max")
        return self


class JobApplicationUpdate(BaseModel):
    """Schema for updating an existing job application."""
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = None
    source: Optional[ApplicationSource] = None
    salary_min: Optional[Decimal] = Field(None, ge=0, le=999999999999.99)
    salary_max: Optional[Decimal] = Field(None, ge=0, le=999999999999.99)
    applied_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=255)
    is_remote: Optional[bool] = None

    @field_validator("company", "role")
    @classmethod
    def validate_string_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize string fields."""
        if v is not None:
            return v.strip()
        return v


class StatusUpdateRequest(BaseModel):
    """Schema for updating application status.
    
    Requirement 27.2, 27.3: Update status and record change with timestamp
    """
    status: ApplicationStatus = Field(..., description="New application status")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes about the status change")


class ApplicationStatusHistoryResponse(BaseModel):
    """Schema for status history response.
    
    Requirement 27.3: Record status changes with timestamp
    """
    id: UUID
    application_id: UUID
    previous_status: Optional[ApplicationStatus]
    new_status: ApplicationStatus
    changed_at: datetime
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class FollowUpReminderCreate(BaseModel):
    """Schema for creating a follow-up reminder."""
    reminder_date: date = Field(..., description="Date when the reminder should be sent")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes for the reminder")


class FollowUpReminderResponse(BaseModel):
    """Schema for follow-up reminder response."""
    id: UUID
    application_id: UUID
    reminder_date: date
    is_sent: bool
    sent_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobApplicationResponse(BaseModel):
    """Schema for job application response.
    
    Requirement 27.1: Return application details
    """
    id: UUID
    user_id: UUID
    company: str
    role: str
    url: Optional[str]
    source: ApplicationSource
    status: ApplicationStatus
    salary_min: Optional[Decimal]
    salary_max: Optional[Decimal]
    applied_date: date
    notes: Optional[str]
    location: Optional[str]
    is_remote: bool
    last_status_update: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobApplicationWithHistoryResponse(JobApplicationResponse):
    """Schema for job application response with status history."""
    status_history: list[ApplicationStatusHistoryResponse] = []
    follow_up_reminders: list[FollowUpReminderResponse] = []


class KanbanColumnResponse(BaseModel):
    """Schema for a kanban board column.
    
    Requirement 27.4: Display applications in kanban board view by status
    """
    status: ApplicationStatus
    applications: list[JobApplicationResponse]
    count: int


class KanbanBoardResponse(BaseModel):
    """Schema for kanban board view.
    
    Requirement 27.4: Display applications in kanban board view by status
    """
    columns: list[KanbanColumnResponse]
    total_applications: int


class ApplicationStatisticsResponse(BaseModel):
    """Schema for application statistics.
    
    Requirement 27.6: Track application statistics including response rate and time to response
    """
    total_applications: int = Field(description="Total number of applications")
    by_status: dict[str, int] = Field(description="Count of applications by status")
    response_rate: float = Field(
        description="Percentage of applications that received a response (not in Applied status)"
    )
    average_days_to_response: Optional[float] = Field(
        None,
        description="Average days from application to first status change"
    )
    applications_this_month: int = Field(description="Applications submitted this month")
    applications_this_week: int = Field(description="Applications submitted this week")
    offer_rate: float = Field(description="Percentage of applications that resulted in offers")
    rejection_rate: float = Field(description="Percentage of applications that were rejected")


class StaleApplicationResponse(BaseModel):
    """Schema for applications needing follow-up.
    
    Requirement 27.5: Identify applications with no update in 14 days
    """
    application_id: UUID
    company: str
    role: str
    status: ApplicationStatus
    days_since_update: int
    last_status_update: datetime
    applied_date: date


class PaginatedJobApplicationResponse(BaseModel):
    """Schema for paginated job application list response."""
    items: list[JobApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[JobApplicationResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedJobApplicationResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
