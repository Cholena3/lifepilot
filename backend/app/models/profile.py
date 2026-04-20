"""Profile models for user information management."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Profile(Base, UUIDMixin, TimestampMixin):
    """User profile with basic personal information.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        first_name: User's first name
        last_name: User's last name
        date_of_birth: User's date of birth
        gender: User's gender
        avatar_url: URL to user's avatar image
        completion_percentage: Profile completion percentage (0-100)
    """

    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    date_of_birth: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    completion_percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )

    __table_args__ = (
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="check_completion_percentage_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, user_id={self.user_id})>"


class StudentProfile(Base, UUIDMixin, TimestampMixin):
    """Student academic profile information.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        institution: Name of educational institution
        degree: Degree type (e.g., B.Tech, M.Tech)
        branch: Branch/major of study
        cgpa: Cumulative GPA (0.0-10.0)
        backlogs: Number of backlogs
        graduation_year: Expected graduation year
    """

    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    institution: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    degree: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    branch: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    cgpa: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 1),  # Allows values like 9.5, 10.0
        nullable=True,
    )
    backlogs: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        nullable=True,
    )
    graduation_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="student_profile",
    )

    __table_args__ = (
        CheckConstraint(
            "cgpa IS NULL OR (cgpa >= 0.0 AND cgpa <= 10.0)",
            name="check_cgpa_range",
        ),
        CheckConstraint(
            "backlogs IS NULL OR backlogs >= 0",
            name="check_backlogs_non_negative",
        ),
    )

    def __repr__(self) -> str:
        return f"<StudentProfile(id={self.id}, user_id={self.user_id})>"


class CareerPreferences(Base, UUIDMixin, TimestampMixin):
    """User career preferences for job recommendations.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        preferred_roles: JSON array of preferred job roles
        preferred_locations: JSON array of preferred work locations
        min_salary: Minimum expected salary
        max_salary: Maximum expected salary
        job_type: Type of job (full-time, part-time, internship, etc.)
    """

    __tablename__ = "career_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    preferred_roles: Mapped[Optional[list[Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    preferred_locations: Mapped[Optional[list[Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    min_salary: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),  # Supports up to 999,999,999.99
        nullable=True,
    )
    max_salary: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    job_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="career_preferences",
    )

    __table_args__ = (
        CheckConstraint(
            "min_salary IS NULL OR min_salary >= 0",
            name="check_min_salary_non_negative",
        ),
        CheckConstraint(
            "max_salary IS NULL OR max_salary >= 0",
            name="check_max_salary_non_negative",
        ),
        CheckConstraint(
            "min_salary IS NULL OR max_salary IS NULL OR min_salary <= max_salary",
            name="check_salary_range_valid",
        ),
    )

    def __repr__(self) -> str:
        return f"<CareerPreferences(id={self.id}, user_id={self.user_id})>"
