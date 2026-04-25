"""Notification models for multi-channel notification delivery.

Validates: Requirements 31.1, 31.2, 31.5
"""

import enum
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationChannel(str, enum.Enum):
    """Supported notification channels.
    
    Validates: Requirements 31.1
    """
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class NotificationStatus(str, enum.Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    QUEUED = "queued"  # For quiet hours


class Notification(Base, UUIDMixin, TimestampMixin):
    """Notification model for tracking sent notifications.
    
    Validates: Requirements 31.1, 31.2, 31.5, 32.5
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to user
        title: Notification title
        body: Notification body content
        channel: Delivery channel used
        status: Current delivery status
        sent_at: When notification was sent
        delivered_at: When notification was delivered
        failed_at: When notification failed (if applicable)
        failure_reason: Reason for failure (if applicable)
        scheduled_at: When notification should be sent (for scheduled notifications)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "notifications"

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
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, channel={self.channel}, status={self.status})>"


class NotificationPreferences(Base, UUIDMixin, TimestampMixin):
    """User notification preferences model.
    
    Validates: Requirements 31.2, 31.3, 31.4
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to user (unique)
        push_enabled: Whether push notifications are enabled
        email_enabled: Whether email notifications are enabled
        sms_enabled: Whether SMS notifications are enabled
        whatsapp_enabled: Whether WhatsApp notifications are enabled
        quiet_hours_start: Start time for quiet hours
        quiet_hours_end: End time for quiet hours
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    sms_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    whatsapp_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    quiet_hours_start: Mapped[Optional[time]] = mapped_column(
        Time,
        nullable=True,
    )
    quiet_hours_end: Mapped[Optional[time]] = mapped_column(
        Time,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notification_preferences")

    def __repr__(self) -> str:
        return f"<NotificationPreferences(id={self.id}, user_id={self.user_id})>"

    def is_channel_enabled(self, channel: NotificationChannel) -> bool:
        """Check if a specific channel is enabled.
        
        Args:
            channel: The notification channel to check
            
        Returns:
            True if the channel is enabled, False otherwise
        """
        channel_map = {
            NotificationChannel.PUSH: self.push_enabled,
            NotificationChannel.EMAIL: self.email_enabled,
            NotificationChannel.SMS: self.sms_enabled,
            NotificationChannel.WHATSAPP: self.whatsapp_enabled,
        }
        return channel_map.get(channel, False)
