"""Weekly Summary model for analytics and reporting.

Requirement 34: Weekly Summary
- Generate summary of activities across all modules
- Include expenses total, documents added, health records logged, and career progress
- Compare metrics with previous week
- Store past summaries for viewing
"""

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


class WeeklySummary(Base, UUIDMixin, TimestampMixin):
    """Weekly summary of user activities across all modules.
    
    Requirement 34.1: Generate summary of activities across all modules
    Requirement 34.2: Include expenses total, documents added, health records logged, and career progress
    Requirement 34.3: Compare metrics with previous week
    Requirement 34.5: Store past summaries for viewing
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        week_start: Start date of the week (Monday)
        week_end: End date of the week (Sunday)
        metrics: JSON object with activity metrics for the week
        comparisons: JSON object with comparison to previous week
        generated_at: When the summary was generated
    """

    __tablename__ = "weekly_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_summary_user_week"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    week_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    # JSON structure for metrics:
    # {
    #   "expenses_total": 1500.00,
    #   "expenses_count": 15,
    #   "documents_added": 3,
    #   "health_records_logged": 5,
    #   "medicine_doses_taken": 21,
    #   "vitals_logged": 7,
    #   "wardrobe_items_added": 2,
    #   "outfits_worn": 5,
    #   "skills_updated": 1,
    #   "courses_progress_hours": 5.5,
    #   "job_applications": 3,
    #   "achievements_added": 1,
    #   "exams_bookmarked": 2,
    #   "life_score": 75
    # }
    metrics: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    # JSON structure for comparisons:
    # {
    #   "expenses_total_change": 200.00,
    #   "expenses_total_change_percent": 15.4,
    #   "documents_added_change": 1,
    #   "health_records_logged_change": -2,
    #   "life_score_change": 5,
    #   ...
    # }
    comparisons: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="weekly_summaries",
    )

    def __repr__(self) -> str:
        return f"<WeeklySummary(id={self.id}, user_id={self.user_id}, week={self.week_start} to {self.week_end})>"
