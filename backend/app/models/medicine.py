"""Medicine module models for medicine tracking and dose management.

Includes Medicine and MedicineDose models for tracking medications,
scheduling reminders, and recording dose history.

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

import uuid
from datetime import datetime, date, time
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.health import HealthRecord


class MedicineFrequency(str, Enum):
    """Valid medicine frequency options.
    
    Validates: Requirements 15.1
    """
    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES_DAILY = "three_times_daily"
    FOUR_TIMES_DAILY = "four_times_daily"
    EVERY_OTHER_DAY = "every_other_day"
    WEEKLY = "weekly"
    AS_NEEDED = "as_needed"
    CUSTOM = "custom"


class DoseStatus(str, Enum):
    """Status of a scheduled dose.
    
    Validates: Requirements 15.3, 15.4
    """
    SCHEDULED = "scheduled"
    TAKEN = "taken"
    MISSED = "missed"
    SKIPPED = "skipped"


class Medicine(Base, UUIDMixin, TimestampMixin):
    """Medicine model for tracking user medications.
    
    Validates: Requirements 15.1, 15.2, 15.5, 15.6
    
    Attributes:
        id: Unique identifier for the medicine
        user_id: Foreign key to the user who owns this medicine
        health_record_id: Optional foreign key to source prescription
        name: Name of the medicine
        dosage: Dosage amount and unit (e.g., "500mg", "10ml")
        frequency: How often the medicine should be taken
        instructions: Additional instructions (e.g., "take with food")
        reminder_times: JSON array of reminder times (HH:MM format)
        start_date: Date when medicine course starts
        end_date: Optional date when medicine course ends
        total_quantity: Total quantity of medicine (for refill tracking)
        remaining_quantity: Remaining quantity of medicine
        refill_threshold: Quantity at which to send refill reminder
        is_active: Whether the medicine is currently active
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "medicines"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    health_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("health_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    dosage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    frequency: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MedicineFrequency.ONCE_DAILY.value,
    )
    
    instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    reminder_times: Mapped[Optional[list]] = mapped_column(
        sa.JSON,
        nullable=True,
    )
    
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )
    
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    
    total_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    remaining_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    refill_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    
    # Relationships
    doses: Mapped[List["MedicineDose"]] = sa_relationship(
        "MedicineDose",
        back_populates="medicine",
        cascade="all, delete-orphan",
        order_by="MedicineDose.scheduled_time.desc()",
    )


class MedicineDose(Base, UUIDMixin, TimestampMixin):
    """Medicine dose model for tracking individual dose events.
    
    Validates: Requirements 15.2, 15.3, 15.4
    
    Attributes:
        id: Unique identifier for the dose record
        medicine_id: Foreign key to the medicine
        scheduled_time: When the dose was scheduled
        taken_time: When the dose was actually taken (null if not taken)
        status: Current status of the dose (scheduled, taken, missed, skipped)
        notes: Optional notes about this dose
        reminder_sent: Whether a reminder was sent for this dose
        followup_reminder_sent: Whether a follow-up reminder was sent
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "medicine_doses"
    
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("medicines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    scheduled_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    
    taken_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DoseStatus.SCHEDULED.value,
        index=True,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    followup_reminder_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Relationships
    medicine: Mapped["Medicine"] = sa_relationship(
        "Medicine",
        back_populates="doses",
    )
