"""Health record sharing model for sharing records with doctors.

Stores temporary access links for sharing health records with healthcare providers.

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

import uuid
import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.health import HealthRecord


class HealthRecordShare(Base, UUIDMixin, TimestampMixin):
    """Health record share model for sharing records with doctors.
    
    Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
    
    Attributes:
        id: Unique identifier for the share
        user_id: Foreign key to the user who owns the records
        public_token: Unique token for public access without authentication
        doctor_name: Name of the doctor/healthcare provider
        doctor_email: Optional email of the doctor
        purpose: Purpose of sharing (e.g., "consultation", "second opinion")
        record_ids: List of health record IDs being shared (JSON array)
        expires_at: When the share link expires
        is_revoked: Whether the share has been revoked
        access_count: Number of times the share link has been accessed
        last_accessed_at: When the share was last accessed
        notes: Optional notes for the doctor
        created_at: Timestamp when share was created
        updated_at: Timestamp when share was last updated
    """
    
    __tablename__ = "health_record_shares"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    public_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    
    doctor_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    doctor_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    purpose: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    record_ids: Mapped[List] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    access_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    @staticmethod
    def generate_public_token() -> str:
        """Generate a new unique public access token.
        
        Returns:
            A URL-safe random token string
        """
        return secrets.token_urlsafe(32)
    
    @property
    def is_expired(self) -> bool:
        """Check if the share link has expired.
        
        Returns:
            True if expired, False otherwise
        """
        from datetime import timezone
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the share link is valid (not expired and not revoked).
        
        Returns:
            True if valid, False otherwise
        """
        return not self.is_expired and not self.is_revoked


class HealthShareAccessLog(Base, UUIDMixin, TimestampMixin):
    """Access log for health record share links.
    
    Validates: Requirements 18.5
    
    Attributes:
        id: Unique identifier for the access log entry
        share_id: Foreign key to the health record share
        ip_address: IP address of the accessor
        user_agent: User agent string of the accessor
        accessed_at: When the access occurred
    """
    
    __tablename__ = "health_share_access_logs"
    
    share_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("health_record_shares.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now,
    )
