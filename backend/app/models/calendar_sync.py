"""Calendar sync models for Google Calendar integration.

Implements Requirements 4.1-4.5 for exam calendar integration.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.exam import Exam
    from app.models.user import User


class GoogleCalendarToken(Base, UUIDMixin, TimestampMixin):
    """Store user's Google Calendar OAuth tokens.
    
    Requirement 4.1: Obtain OAuth tokens and store them securely
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        access_token: Google OAuth access token (encrypted)
        refresh_token: Google OAuth refresh token (encrypted)
        token_expiry: When the access token expires
        scope: OAuth scopes granted
    """

    __tablename__ = "google_calendar_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    token_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scope: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<GoogleCalendarToken(user_id={self.user_id})>"


class CalendarSync(Base, UUIDMixin):
    """Track synced exam events in Google Calendar.
    
    Requirement 4.2, 4.3, 4.4: Track calendar events for create, update, delete
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        exam_id: Foreign key to Exam
        google_event_id: Google Calendar event ID
        synced_at: When the event was last synced
    """

    __tablename__ = "calendar_syncs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    google_event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    exam: Mapped["Exam"] = relationship("Exam")

    def __repr__(self) -> str:
        return f"<CalendarSync(user_id={self.user_id}, exam_id={self.exam_id}, event_id={self.google_event_id})>"
