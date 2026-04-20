"""Interview preparation models for career module.

Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5
"""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.job_application import JobApplication


class InterviewType(str, enum.Enum):
    """Type of interview."""
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    PANEL = "panel"
    HR = "hr"
    FINAL = "final"
    OTHER = "other"


class InterviewNote(Base, UUIDMixin, TimestampMixin):
    """Interview notes and preparation materials.
    
    Requirement 28.1: Associate interview notes with a job application
    Requirement 28.2: Store company research, questions asked, and answers prepared
    Requirement 28.4: Allow users to rate their interview performance
    Requirement 28.5: Display interview history with outcomes
    
    Attributes:
        id: UUID primary key
        application_id: Foreign key to JobApplication
        interview_type: Type of interview (phone, technical, behavioral, etc.)
        interview_date: Scheduled date of the interview
        interview_time: Scheduled time of the interview (stored as string HH:MM)
        company_research: Notes about the company (culture, recent news, etc.)
        questions_asked: JSON array of questions asked during interview
        answers_prepared: JSON array of prepared answers
        performance_rating: Self-rating of interview performance (1-5)
        feedback: Post-interview feedback and notes
        outcome: Result of the interview (passed, failed, pending, etc.)
        reminder_sent: Whether preparation reminder was sent
    """

    __tablename__ = "interview_notes"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(InterviewType),
        nullable=False,
        default=InterviewType.OTHER,
    )
    interview_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    interview_time: Mapped[Optional[str]] = mapped_column(
        String(5),  # HH:MM format
        nullable=True,
    )
    company_research: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    questions_asked: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    answers_prepared: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    performance_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    outcome: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="interview_notes",
    )
    preparation_reminders: Mapped[list["InterviewPreparationReminder"]] = relationship(
        "InterviewPreparationReminder",
        back_populates="interview_note",
        cascade="all, delete-orphan",
        order_by="InterviewPreparationReminder.reminder_date",
    )

    def __repr__(self) -> str:
        return f"<InterviewNote(id={self.id}, application_id={self.application_id}, type={self.interview_type})>"


class InterviewPreparationReminder(Base, UUIDMixin, TimestampMixin):
    """Preparation reminder for an interview.
    
    Requirement 28.3: Send preparation reminders when interview is scheduled
    
    Attributes:
        id: UUID primary key
        interview_note_id: Foreign key to InterviewNote
        reminder_date: Date when the reminder should be sent
        reminder_time: Time when the reminder should be sent
        is_sent: Whether the reminder has been sent
        sent_at: Timestamp when the reminder was sent
        notes: Optional notes for the reminder
    """

    __tablename__ = "interview_preparation_reminders"

    interview_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reminder_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    reminder_time: Mapped[Optional[str]] = mapped_column(
        String(5),  # HH:MM format
        nullable=True,
    )
    is_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    interview_note: Mapped["InterviewNote"] = relationship(
        "InterviewNote",
        back_populates="preparation_reminders",
    )

    def __repr__(self) -> str:
        return f"<InterviewPreparationReminder(interview_note_id={self.interview_note_id}, date={self.reminder_date}, sent={self.is_sent})>"


class QuestionAnswer(Base, UUIDMixin, TimestampMixin):
    """Individual Q&A entry for interview preparation.
    
    Requirement 28.2: Store questions asked and answers prepared
    
    Attributes:
        id: UUID primary key
        interview_note_id: Foreign key to InterviewNote
        question: The interview question
        answer: The prepared answer
        category: Category of the question (technical, behavioral, etc.)
        is_asked: Whether this question was actually asked in the interview
        notes: Additional notes about this Q&A
    """

    __tablename__ = "interview_qa"

    interview_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    answer: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    is_asked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    interview_note: Mapped["InterviewNote"] = relationship(
        "InterviewNote",
        backref="qa_entries",
    )

    def __repr__(self) -> str:
        return f"<QuestionAnswer(id={self.id}, question={self.question[:50]}...)>"
