"""Emergency health information model.

Stores emergency health information accessible via QR code without authentication.

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""

import uuid
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class EmergencyInfoField:
    """Valid emergency info field names for visibility configuration.
    
    Validates: Requirements 17.5
    """
    BLOOD_TYPE = "blood_type"
    ALLERGIES = "allergies"
    MEDICAL_CONDITIONS = "medical_conditions"
    EMERGENCY_CONTACTS = "emergency_contacts"
    CURRENT_MEDICATIONS = "current_medications"
    
    ALL = [BLOOD_TYPE, ALLERGIES, MEDICAL_CONDITIONS, EMERGENCY_CONTACTS, CURRENT_MEDICATIONS]


class BloodType:
    """Valid blood type values.
    
    Validates: Requirements 17.1
    """
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "Unknown"
    
    ALL = [A_POSITIVE, A_NEGATIVE, B_POSITIVE, B_NEGATIVE, 
           AB_POSITIVE, AB_NEGATIVE, O_POSITIVE, O_NEGATIVE, UNKNOWN]


class EmergencyInfo(Base, UUIDMixin, TimestampMixin):
    """Emergency health information model.
    
    Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
    
    Attributes:
        id: Unique identifier for the emergency info record
        user_id: Foreign key to the user who owns the record
        public_token: Unique token for public access without authentication
        blood_type: User's blood type
        allergies: List of allergies (JSON array)
        medical_conditions: List of medical conditions (JSON array)
        emergency_contacts: List of emergency contacts with name and phone (JSON array)
        current_medications: List of current medications (JSON array)
        visible_fields: List of field names visible on public emergency page (JSON array)
        qr_code_path: Path to the generated QR code image
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "emergency_info"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One emergency info per user
        index=True,
    )
    
    public_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    
    blood_type: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    
    allergies: Mapped[Optional[List]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    
    medical_conditions: Mapped[Optional[List]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    
    emergency_contacts: Mapped[Optional[List]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    
    current_medications: Mapped[Optional[List]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    
    visible_fields: Mapped[Optional[List]] = mapped_column(
        JSONB,
        nullable=True,
        default=lambda: EmergencyInfoField.ALL.copy(),
    )
    
    qr_code_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    @staticmethod
    def generate_public_token() -> str:
        """Generate a new unique public access token.
        
        Returns:
            A URL-safe random token string
        """
        return secrets.token_urlsafe(32)
