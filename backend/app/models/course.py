"""Course models for learning progress tracking.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
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


class Course(Base, UUIDMixin, TimestampMixin):
    """User course for learning progress tracking.
    
    Requirement 25.1: Store course name, platform, URL, and total duration
    Requirement 25.2: Track completion percentage
    Requirement 25.4: Mark course complete and prompt for skill update
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        title: Course title/name
        platform: Learning platform (e.g., Coursera, Udemy)
        url: Course URL
        total_hours: Total duration in hours
        completed_hours: Hours completed
        completion_percentage: Calculated completion percentage (0-100)
        is_completed: Whether the course is marked as complete
        last_activity_at: Timestamp of last learning activity
    """

    __tablename__ = "courses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    platform: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    total_hours: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        default=0,
    )
    completed_hours: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        default=0,
    )
    completion_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="courses",
    )
    learning_sessions: Mapped[list["LearningSession"]] = relationship(
        "LearningSession",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="LearningSession.session_date.desc()",
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, title={self.title}, completion={self.completion_percentage}%)>"


class LearningSession(Base, UUIDMixin):
    """Learning session log for tracking time invested.
    
    Requirement 25.2: Log progress updates
    Requirement 25.3: Track total hours invested
    
    Attributes:
        id: UUID primary key
        course_id: Foreign key to Course
        session_date: Date of the learning session
        duration_minutes: Duration of the session in minutes
        notes: Optional notes about the session
        created_at: Timestamp when the session was logged
    """

    __tablename__ = "learning_sessions"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=func.current_date(),
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="learning_sessions",
    )

    def __repr__(self) -> str:
        return f"<LearningSession(id={self.id}, course_id={self.course_id}, duration={self.duration_minutes}min)>"
