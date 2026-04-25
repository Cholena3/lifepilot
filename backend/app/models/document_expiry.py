"""Document expiry alert models.

Validates: Requirements 8.1, 8.2, 8.3, 8.4
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class ExpiryAlertType(str, enum.Enum):
    """Types of expiry alerts.
    
    Validates: Requirements 8.1
    """
    DAYS_30 = "days_30"
    DAYS_14 = "days_14"
    DAYS_7 = "days_7"


class DocumentExpiryAlertPreferences(Base, UUIDMixin, TimestampMixin):
    """User preferences for document expiry alerts per category.
    
    Validates: Requirements 8.4
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to user
        category: Document category (Identity, Education, Career, Finance)
        alerts_enabled: Whether expiry alerts are enabled for this category
        alert_30_days: Whether to send alert 30 days before expiry
        alert_14_days: Whether to send alert 14 days before expiry
        alert_7_days: Whether to send alert 7 days before expiry
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "document_expiry_alert_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category_expiry_prefs"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    alert_30_days: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    alert_14_days: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    alert_7_days: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="document_expiry_preferences")

    def __repr__(self) -> str:
        return f"<DocumentExpiryAlertPreferences(id={self.id}, user_id={self.user_id}, category={self.category})>"


class DocumentExpiryAlert(Base, UUIDMixin, TimestampMixin):
    """Tracks sent expiry alerts to prevent duplicate notifications.
    
    Validates: Requirements 8.1, 8.3
    
    Attributes:
        id: UUID primary key
        document_id: Foreign key to document
        user_id: Foreign key to user
        alert_type: Type of alert (30, 14, or 7 days)
        sent_at: When the alert was sent
        notification_id: Reference to the notification record
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "document_expiry_alerts"
    __table_args__ = (
        UniqueConstraint("document_id", "alert_type", name="uq_document_alert_type"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[ExpiryAlertType] = mapped_column(
        Enum(ExpiryAlertType),
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    notification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("notifications.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="expiry_alerts")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<DocumentExpiryAlert(id={self.id}, document_id={self.document_id}, alert_type={self.alert_type})>"
