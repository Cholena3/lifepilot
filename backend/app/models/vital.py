"""Vital module models for vitals tracking.

Includes Vital and VitalTargetRange models for logging and tracking
vital signs with custom target ranges.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.health import FamilyMember


class VitalType(str, Enum):
    """Valid vital types.
    
    Validates: Requirements 16.1
    """
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    HEART_RATE = "heart_rate"
    WEIGHT = "weight"
    TEMPERATURE = "temperature"
    BLOOD_SUGAR = "blood_sugar"
    OXYGEN_SATURATION = "oxygen_saturation"
    RESPIRATORY_RATE = "respiratory_rate"


# Default normal ranges for vital types
DEFAULT_VITAL_RANGES = {
    VitalType.BLOOD_PRESSURE_SYSTOLIC.value: {"min": 90.0, "max": 120.0, "unit": "mmHg"},
    VitalType.BLOOD_PRESSURE_DIASTOLIC.value: {"min": 60.0, "max": 80.0, "unit": "mmHg"},
    VitalType.HEART_RATE.value: {"min": 60.0, "max": 100.0, "unit": "bpm"},
    VitalType.WEIGHT.value: {"min": None, "max": None, "unit": "kg"},  # No default range
    VitalType.TEMPERATURE.value: {"min": 36.1, "max": 37.2, "unit": "°C"},
    VitalType.BLOOD_SUGAR.value: {"min": 70.0, "max": 100.0, "unit": "mg/dL"},  # Fasting
    VitalType.OXYGEN_SATURATION.value: {"min": 95.0, "max": 100.0, "unit": "%"},
    VitalType.RESPIRATORY_RATE.value: {"min": 12.0, "max": 20.0, "unit": "breaths/min"},
}


class Vital(Base, UUIDMixin, TimestampMixin):
    """Vital model for tracking user vital signs.
    
    Validates: Requirements 16.1, 16.2, 16.3
    
    Attributes:
        id: Unique identifier for the vital record
        user_id: Foreign key to the user who owns the record
        family_member_id: Optional foreign key to family member (null = self)
        vital_type: Type of vital (blood_pressure, heart_rate, etc.)
        value: Numeric value of the vital reading
        unit: Unit of measurement
        notes: Optional notes about the reading
        recorded_at: When the vital was recorded
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "vitals"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    family_member_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    vital_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=func.now(),
    )
    
    # Relationships
    family_member: Mapped[Optional["FamilyMember"]] = sa_relationship(
        "FamilyMember",
        foreign_keys=[family_member_id],
    )


class VitalTargetRange(Base, UUIDMixin, TimestampMixin):
    """Custom target range for vital types.
    
    Validates: Requirements 16.4
    
    Attributes:
        id: Unique identifier for the target range
        user_id: Foreign key to the user who owns the range
        family_member_id: Optional foreign key to family member (null = self)
        vital_type: Type of vital this range applies to
        min_value: Minimum acceptable value (null = no minimum)
        max_value: Maximum acceptable value (null = no maximum)
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "vital_target_ranges"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    family_member_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    vital_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    min_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    max_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    # Relationships
    family_member: Mapped[Optional["FamilyMember"]] = sa_relationship(
        "FamilyMember",
        foreign_keys=[family_member_id],
    )
