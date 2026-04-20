"""Pydantic schemas for interview preparation.

Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.interview import InterviewType


class QuestionAnswerCreate(BaseModel):
    """Schema for creating a Q&A entry.
    
    Requirement 28.2: Store questions asked and answers prepared
    """
    question: str = Field(..., min_length=1, max_length=2000, description="Interview question")
    answer: Optional[str] = Field(None, max_length=5000, description="Prepared answer")
    category: Optional[str] = Field(None, max_length=100, description="Question category")
    is_asked: bool = Field(default=False, description="Whether this question was asked")
    notes: Optional[str] = Field(None, max_length=2000, description="Additional notes")

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and normalize question."""
        return v.strip()


class QuestionAnswerUpdate(BaseModel):
    """Schema for updating a Q&A entry."""
    question: Optional[str] = Field(None, min_length=1, max_length=2000)
    answer: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = Field(None, max_length=100)
    is_asked: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=2000)


class QuestionAnswerResponse(BaseModel):
    """Schema for Q&A response."""
    id: UUID
    interview_note_id: UUID
    question: str
    answer: Optional[str]
    category: Optional[str]
    is_asked: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewNoteCreate(BaseModel):
    """Schema for creating interview notes.
    
    Requirement 28.1: Associate interview notes with a job application
    Requirement 28.2: Store company research, questions asked, and answers prepared
    """
    application_id: UUID = Field(..., description="Job application ID")
    interview_type: InterviewType = Field(
        default=InterviewType.OTHER,
        description="Type of interview"
    )
    interview_date: Optional[date] = Field(None, description="Scheduled interview date")
    interview_time: Optional[str] = Field(
        None,
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Scheduled interview time (HH:MM)"
    )
    company_research: Optional[str] = Field(
        None,
        max_length=10000,
        description="Company research notes"
    )
    questions_asked: Optional[list[str]] = Field(
        None,
        description="Questions asked during interview"
    )
    answers_prepared: Optional[list[str]] = Field(
        None,
        description="Prepared answers"
    )


class InterviewNoteUpdate(BaseModel):
    """Schema for updating interview notes."""
    interview_type: Optional[InterviewType] = None
    interview_date: Optional[date] = None
    interview_time: Optional[str] = Field(
        None,
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    company_research: Optional[str] = Field(None, max_length=10000)
    questions_asked: Optional[list[str]] = None
    answers_prepared: Optional[list[str]] = None
    feedback: Optional[str] = Field(None, max_length=5000)
    outcome: Optional[str] = Field(None, max_length=50)


class PerformanceRatingUpdate(BaseModel):
    """Schema for updating interview performance rating.
    
    Requirement 28.4: Allow users to rate their interview performance
    """
    performance_rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Performance rating (1-5 scale)"
    )
    feedback: Optional[str] = Field(
        None,
        max_length=5000,
        description="Post-interview feedback"
    )
    outcome: Optional[str] = Field(
        None,
        max_length=50,
        description="Interview outcome (passed, failed, pending)"
    )


class PreparationReminderCreate(BaseModel):
    """Schema for creating a preparation reminder.
    
    Requirement 28.3: Send preparation reminders
    """
    reminder_date: date = Field(..., description="Date for the reminder")
    reminder_time: Optional[str] = Field(
        None,
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Time for the reminder (HH:MM)"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Reminder notes")


class PreparationReminderResponse(BaseModel):
    """Schema for preparation reminder response."""
    id: UUID
    interview_note_id: UUID
    reminder_date: date
    reminder_time: Optional[str]
    is_sent: bool
    sent_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewNoteResponse(BaseModel):
    """Schema for interview note response.
    
    Requirement 28.1, 28.2, 28.4: Return interview details
    """
    id: UUID
    application_id: UUID
    interview_type: InterviewType
    interview_date: Optional[date]
    interview_time: Optional[str]
    company_research: Optional[str]
    questions_asked: Optional[list[str]]
    answers_prepared: Optional[list[str]]
    performance_rating: Optional[int]
    feedback: Optional[str]
    outcome: Optional[str]
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewNoteWithRemindersResponse(InterviewNoteResponse):
    """Schema for interview note with reminders."""
    preparation_reminders: list[PreparationReminderResponse] = []


class InterviewNoteWithQAResponse(InterviewNoteResponse):
    """Schema for interview note with Q&A entries."""
    qa_entries: list[QuestionAnswerResponse] = []
    preparation_reminders: list[PreparationReminderResponse] = []



class InterviewHistoryResponse(BaseModel):
    """Schema for interview history with outcomes.
    
    Requirement 28.5: Display interview history with outcomes for pattern analysis
    """
    id: UUID
    application_id: UUID
    company: str
    role: str
    interview_type: InterviewType
    interview_date: Optional[date]
    performance_rating: Optional[int]
    outcome: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewStatisticsResponse(BaseModel):
    """Schema for interview statistics.
    
    Requirement 28.5: Pattern analysis from interview history
    """
    total_interviews: int = Field(description="Total number of interviews")
    by_type: dict[str, int] = Field(description="Count of interviews by type")
    by_outcome: dict[str, int] = Field(description="Count of interviews by outcome")
    average_rating: Optional[float] = Field(
        None,
        description="Average performance rating"
    )
    interviews_this_month: int = Field(description="Interviews this month")
    pass_rate: float = Field(description="Percentage of interviews passed")


class PaginatedInterviewNoteResponse(BaseModel):
    """Schema for paginated interview notes list."""
    items: list[InterviewNoteResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[InterviewNoteResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedInterviewNoteResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
