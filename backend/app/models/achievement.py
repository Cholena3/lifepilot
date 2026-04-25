"""Achievement models for career module achievement logging.

Requirement 29: Achievement Logging
- Store title, description, date, and category
- Support categories: Academic, Professional, Certification, Award, Project
- Allow attaching supporting documents
- Display achievements on a timeline view
"""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class AchievementCategory(str, enum.Enum):
    """Categories for achievements.
    
    Requirement 29.2: Support categories: Academic, Professional, Certification, Award, Project
    """
    ACADEMIC = "academic"
    PROFESSIONAL = "professional"
    CERTIFICATION = "certification"
    AWARD = "award"
    PROJECT = "project"
    PUBLICATION = "publication"
    OTHER = "other"


class Achievement(Base, UUIDMixin, TimestampMixin):
    """User achievement with category and document attachments.
    
    Requirement 29.1: Store title, description, date, and category
    Requirement 29.3: Allow attaching supporting documents
    Requirement 29.5: Display achievements on a timeline view
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        title: Achievement title
        description: Detailed description of the achievement
        achieved_date: Date when the achievement was earned
        category: Achievement category for grouping
        document_ids: List of document IDs attached to this achievement
    """

    __tablename__ = "achievements"

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
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    achieved_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    category: Mapped[AchievementCategory] = mapped_column(
        Enum(AchievementCategory),
        nullable=False,
        default=AchievementCategory.OTHER,
        index=True,
    )
    # Store document IDs as an array for linking to document vault
    # Requirement 29.3: Allow attaching supporting documents
    document_ids: Mapped[Optional[List[uuid.UUID]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="achievements",
    )

    def __repr__(self) -> str:
        return f"<Achievement(id={self.id}, title={self.title}, category={self.category})>"
