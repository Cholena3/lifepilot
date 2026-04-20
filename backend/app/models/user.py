"""User model for authentication and account management.

Validates: Requirements 36.5, 36.6
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.achievement import Achievement
    from app.models.badge import Badge
    from app.models.course import Course
    from app.models.document_expiry import DocumentExpiryAlertPreferences
    from app.models.job_application import JobApplication
    from app.models.life_score import LifeScore
    from app.models.notification import Notification, NotificationPreferences
    from app.models.profile import CareerPreferences, Profile, StudentProfile
    from app.models.resume import Resume
    from app.models.roadmap import CareerRoadmap
    from app.models.skill import Skill
    from app.models.weekly_summary import WeeklySummary


class User(Base, UUIDMixin, TimestampMixin):
    """User model for authentication.
    
    Attributes:
        id: UUID primary key
        email: Unique email address
        password_hash: Bcrypt hashed password
        phone: Optional phone number
        phone_verified: Whether phone is verified via OTP
        oauth_provider: OAuth provider name (e.g., 'google')
        oauth_id: OAuth provider user ID
        deletion_requested_at: Timestamp when account deletion was requested
        deletion_scheduled_at: Timestamp when account will be permanently deleted
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        
    Validates: Requirements 36.5, 36.6
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,  # Nullable for OAuth-only users
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    oauth_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    oauth_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    # Admin role field - Validates: Requirements 38.1, 38.2, 38.3, 38.4
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    # Account deletion fields - Validates: Requirements 36.6
    deletion_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    deletion_scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    profile: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    career_preferences: Mapped[Optional["CareerPreferences"]] = relationship(
        "CareerPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_preferences: Mapped[Optional["NotificationPreferences"]] = relationship(
        "NotificationPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    document_expiry_preferences: Mapped[list["DocumentExpiryAlertPreferences"]] = relationship(
        "DocumentExpiryAlertPreferences",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    skills: Mapped[list["Skill"]] = relationship(
        "Skill",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    courses: Mapped[list["Course"]] = relationship(
        "Course",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    roadmaps: Mapped[list["CareerRoadmap"]] = relationship(
        "CareerRoadmap",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    job_applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    achievements: Mapped[list["Achievement"]] = relationship(
        "Achievement",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    life_scores: Mapped[list["LifeScore"]] = relationship(
        "LifeScore",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    badges: Mapped[list["Badge"]] = relationship(
        "Badge",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    weekly_summaries: Mapped[list["WeeklySummary"]] = relationship(
        "WeeklySummary",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
