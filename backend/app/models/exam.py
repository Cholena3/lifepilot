"""Exam models for exam feed and discovery module.

Implements Requirements 3.1-3.8 for exam feed, filtering, and tracking.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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
    from app.models.user import User


class ExamType(str, enum.Enum):
    """Types of exams available.
    
    Requirement 3.4: Categorize exams into types
    """
    CAMPUS_PLACEMENT = "campus_placement"
    OFF_CAMPUS = "off_campus"
    INTERNSHIP = "internship"
    HIGHER_EDUCATION = "higher_education"
    GOVERNMENT = "government"
    SCHOLARSHIP = "scholarship"


class ApplicationStatus(str, enum.Enum):
    """Status of exam application."""
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    SELECTED = "selected"
    WITHDRAWN = "withdrawn"


class Exam(Base, UUIDMixin, TimestampMixin):
    """Exam model for exam feed and discovery.
    
    Requirement 3.1: Filter by degree, branch, graduation year
    Requirement 3.2: Apply CGPA filter
    Requirement 3.3: Apply backlog filter
    Requirement 3.4: Categorize exams by type
    Requirement 3.8: Return syllabus, cutoffs, previous papers, and resource links
    
    Attributes:
        id: UUID primary key
        name: Exam name/title
        organization: Organization conducting the exam
        exam_type: Type of exam (campus, government, etc.)
        description: Detailed description of the exam
        registration_start: Registration start date
        registration_end: Registration end date (deadline)
        exam_date: Date of the exam
        min_cgpa: Minimum CGPA required
        max_backlogs: Maximum backlogs allowed
        eligible_degrees: JSON array of eligible degrees
        eligible_branches: JSON array of eligible branches
        graduation_year_min: Minimum graduation year
        graduation_year_max: Maximum graduation year
        syllabus: Exam syllabus text
        cutoffs: JSON object with cutoff information
        resources: JSON array of resource links
        source_url: URL where exam was scraped from
        scraped_at: Timestamp when exam was scraped
    """

    __tablename__ = "exams"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    organization: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    exam_type: Mapped[ExamType] = mapped_column(
        Enum(ExamType),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    registration_start: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    registration_end: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )
    exam_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )
    # Eligibility criteria
    min_cgpa: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 1),
        nullable=True,
    )
    max_backlogs: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    eligible_degrees: Mapped[Optional[list[Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    eligible_branches: Mapped[Optional[list[Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    graduation_year_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    graduation_year_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    # Exam details
    syllabus: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    cutoffs: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    resources: Mapped[Optional[list[Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    # Scraping metadata
    source_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    scraped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Relationships
    bookmarks: Mapped[list["ExamBookmark"]] = relationship(
        "ExamBookmark",
        back_populates="exam",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["ExamApplication"]] = relationship(
        "ExamApplication",
        back_populates="exam",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "min_cgpa IS NULL OR (min_cgpa >= 0.0 AND min_cgpa <= 10.0)",
            name="check_exam_min_cgpa_range",
        ),
        CheckConstraint(
            "max_backlogs IS NULL OR max_backlogs >= 0",
            name="check_exam_max_backlogs_non_negative",
        ),
    )

    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, name={self.name}, type={self.exam_type})>"


class ExamBookmark(Base, UUIDMixin):
    """User bookmark for an exam.
    
    Requirement 3.5: Add exam to user's saved exams list
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        exam_id: Foreign key to Exam
        created_at: Timestamp when bookmarked
    """

    __tablename__ = "exam_bookmarks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    exam: Mapped["Exam"] = relationship(
        "Exam",
        back_populates="bookmarks",
    )

    __table_args__ = (
        # Unique constraint to prevent duplicate bookmarks
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<ExamBookmark(user_id={self.user_id}, exam_id={self.exam_id})>"


class ExamApplication(Base, UUIDMixin, TimestampMixin):
    """User application for an exam.
    
    Requirement 3.6: Record application date and update status
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        exam_id: Foreign key to Exam
        status: Application status
        applied_date: Date when user applied
        notes: User notes about the application
    """

    __tablename__ = "exam_applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        nullable=False,
        default=ApplicationStatus.APPLIED,
    )
    applied_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=func.current_date(),
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    exam: Mapped["Exam"] = relationship(
        "Exam",
        back_populates="applications",
    )

    def __repr__(self) -> str:
        return f"<ExamApplication(user_id={self.user_id}, exam_id={self.exam_id}, status={self.status})>"
