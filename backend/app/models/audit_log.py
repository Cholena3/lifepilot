"""Audit log model for tracking all data access.

Validates: Requirements 36.7

Stores audit trail of all data access operations for security compliance.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """Model for storing audit log entries.
    
    Validates: Requirements 36.7
    
    Tracks all data access operations including:
    - User performing the action
    - Action type (CREATE, READ, UPDATE, DELETE)
    - Entity type and ID being accessed
    - Request details (method, path, IP)
    - Old and new data for modifications
    """
    
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # User who performed the action (null for unauthenticated requests)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Action type: CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Entity type being accessed (e.g., "document", "expense", "health_record")
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    
    # Entity ID being accessed
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    
    # HTTP method (GET, POST, PUT, DELETE, etc.)
    http_method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    
    # Request path
    request_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    # Client IP address
    ip_address: Mapped[str] = mapped_column(
        String(45),  # IPv6 max length
        nullable=False,
    )
    
    # User agent string
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Response status code
    status_code: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )
    
    # Old data (for UPDATE/DELETE operations)
    old_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    # New data (for CREATE/UPDATE operations)
    new_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    # Additional metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, "
            f"action={self.action}, entity_type={self.entity_type})>"
        )
