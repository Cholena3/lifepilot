"""Job application models for career module job tracking.

Validates: Requirements 27.1, 27.2, 27.3, 27.4, 27.5, 27.6
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.interview import InterviewNote
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    """Status of a job application.
    
    Requirement 27.2: Support status pipeline: Applied, Screening, Interview, Offer, Rejected, Withdrawn
    """
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationSource(str, enum.Enum):
    """Source where the job was found."""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    COMPANY_WEBSITE = "company_website"
    REFERRAL = "referral"
    RECRUITER = "recruiter"
    JOB_BOARD = "job_board"
    NETWORKING = "networking"
    OTHER = "other"


class JobApplication(Base, UUIDMixin, TimestampMixin):
    """Job application tracking model.
    
    Requirement 27.1: Store company, role, date, source, and status
    Requirement 27.4: Display applications in kanban board view by status
    Requirement 27.6: Track application statistics
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        company: Company name
        role: Job role/position
        url: Job posting URL
        source: Where the job was found
        status: Current application status
        salary_min: Minimum salary offered/expected
        salary_max: Maximum salary offered/expected
        applied_date: Date when application was submitted
        notes: Additional notes about the application
        location: Job location
        is_remote: Whether the job is remote
    """

    __tablename__ = "job_applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    source: Mapped[ApplicationSource] = mapped_column(
        Enum(ApplicationSource),
        nullable=False,
        default=ApplicationSource.OTHER,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        nullable=False,
        default=ApplicationStatus.APPLIED,
        index=True,
    )
    salary_min: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    salary_max: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    applied_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=func.current_date(),
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    last_status_update: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="job_applications",
    )
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at.desc()",
    )
    follow_up_reminders: Mapped[list["ApplicationFollowUpReminder"]] = relationship(
        "ApplicationFollowUpReminder",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationFollowUpReminder.reminder_date",
    )
    interview_notes: Mapped[list["InterviewNote"]] = relationship(
        "InterviewNote",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="InterviewNote.interview_date",
    )

    def __repr__(self) -> str:
        return f"<JobApplication(id={self.id}, company={self.company}, role={self.role}, status={self.status})>"


class ApplicationStatusHistory(Base, UUIDMixin):
    """History of status changes for a job application.
    
    Requirement 27.3: Record status changes with timestamp
    
    Attributes:
        id: UUID primary key
        application_id: Foreign key to JobApplication
        previous_status: Previous application status (None for initial)
        new_status: New application status
        changed_at: Timestamp of the change
        notes: Optional notes about the status change
    """

    __tablename__ = "application_status_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[Optional[ApplicationStatus]] = mapped_column(
        Enum(ApplicationStatus),
        nullable=True,
    )
    new_status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="status_history",
    )

    def __repr__(self) -> str:
        return f"<ApplicationStatusHistory(application_id={self.application_id}, {self.previous_status} -> {self.new_status})>"


class ApplicationFollowUpReminder(Base, UUIDMixin, TimestampMixin):
    """Follow-up reminder for a job application.
    
    Requirement 27.5: Prompt user to follow up when application has no update in 14 days
    
    Attributes:
        id: UUID primary key
        application_id: Foreign key to JobApplication
        reminder_date: Date when the reminder should be sent
        is_sent: Whether the reminder has been sent
        sent_at: Timestamp when the reminder was sent
        notes: Optional notes for the reminder
    """

    __tablename__ = "application_follow_up_reminders"

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reminder_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
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
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="follow_up_reminders",
    )

    def __repr__(self) -> str:
        return f"<ApplicationFollowUpReminder(application_id={self.application_id}, date={self.reminder_date}, sent={self.is_sent})>"
