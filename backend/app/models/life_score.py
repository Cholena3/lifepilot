"""Life Score model for gamification and engagement tracking.

Requirement 33: Life Score Gamification
- Calculate Life Score based on activity across all modules
- Weight activities by importance and recency
- Display Life Score trends over time
- Show breakdown of score by module
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ModuleType(str, enum.Enum):
    """Module types for Life Score breakdown.
    
    Requirement 33.6: Show breakdown of score by module
    """
    DOCUMENTS = "documents"
    MONEY = "money"
    HEALTH = "health"
    WARDROBE = "wardrobe"
    CAREER = "career"
    EXAMS = "exams"


class LifeScore(Base, UUIDMixin, TimestampMixin):
    """Daily Life Score snapshot for a user.
    
    Requirement 33.1: Calculate Life Score based on activity across all modules
    Requirement 33.4: Display Life Score trends over time
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        score_date: Date of the score snapshot
        total_score: Overall life score (0-100)
        module_scores: JSON object with scores per module
        activity_count: Total activities counted for this score
    """

    __tablename__ = "life_scores"
    __table_args__ = (
        UniqueConstraint("user_id", "score_date", name="uq_life_score_user_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    total_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    # JSON structure: {"documents": 15, "money": 20, "health": 10, ...}
    module_scores: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    activity_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="life_scores",
    )

    def __repr__(self) -> str:
        return f"<LifeScore(id={self.id}, user_id={self.user_id}, date={self.score_date}, score={self.total_score})>"
