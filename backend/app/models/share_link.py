"""Share link models for document sharing functionality.

Includes ShareLink and ShareLinkAccess models for secure document sharing
with temporary links, password protection, and access logging.

Validates: Requirements 9.1, 9.2, 9.4, 9.5, 9.6
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import Document


class ShareLink(Base, UUIDMixin, TimestampMixin):
    """Share link model for temporary document sharing.
    
    Validates: Requirements 9.1, 9.2, 9.4, 9.5
    
    Attributes:
        id: Unique identifier for the share link
        document_id: Foreign key to the document being shared
        user_id: Foreign key to the user who created the share link
        token: Unique token for the share URL
        password_hash: Optional bcrypt hash of the password
        expires_at: Expiration timestamp for the share link
        is_revoked: Whether the share link has been revoked
        created_at: Timestamp when share link was created
        updated_at: Timestamp when share link was last updated
    """
    
    __tablename__ = "share_links"
    
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
    
    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="share_links",
    )
    
    accesses: Mapped[list["ShareLinkAccess"]] = relationship(
        "ShareLinkAccess",
        back_populates="share_link",
        cascade="all, delete-orphan",
    )


class ShareLinkAccess(Base, UUIDMixin):
    """Share link access log model for tracking document access.
    
    Validates: Requirements 9.6
    
    Attributes:
        id: Unique identifier for the access log entry
        share_link_id: Foreign key to the share link
        ip_address: IP address of the accessor
        user_agent: User agent string of the accessor
        accessed_at: Timestamp when the access occurred
    """
    
    __tablename__ = "share_link_accesses"
    
    share_link_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("share_links.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    ip_address: Mapped[str] = mapped_column(
        String(45),  # IPv6 max length
        nullable=False,
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    share_link: Mapped["ShareLink"] = relationship(
        "ShareLink",
        back_populates="accesses",
    )
