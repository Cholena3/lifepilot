"""Document models for the document vault module.

Includes Document and DocumentVersion models for storing and versioning documents.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document_expiry import DocumentExpiryAlert
    from app.models.share_link import ShareLink


class Document(Base, UUIDMixin, TimestampMixin):
    """Document model for storing user documents.
    
    Attributes:
        id: Unique identifier for the document
        user_id: Foreign key to the user who owns the document
        title: Document title
        category: Document category (Identity, Education, Career, Finance)
        file_path: Path to the encrypted file in storage
        content_type: MIME type of the document
        file_size: Size of the file in bytes
        encryption_key: Key used for AES-256 encryption
        expiry_date: Optional expiry date for the document
        is_expired: Whether the document has expired
        ocr_text: Extracted text from OCR processing
        extracted_fields: JSON field for structured OCR data
        current_version: Current version number
        created_at: Timestamp when document was created
        updated_at: Timestamp when document was last updated
    """
    
    __tablename__ = "documents"
    
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
    
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    encryption_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    is_expired: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    
    ocr_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    current_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    
    # Relationships
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )
    expiry_alerts: Mapped[List["DocumentExpiryAlert"]] = relationship(
        "DocumentExpiryAlert",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    share_links: Mapped[List["ShareLink"]] = relationship(
        "ShareLink",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentVersion(Base, UUIDMixin):
    """Document version model for tracking document history.
    
    Each time a document is updated, a new version is created to maintain
    the complete history of changes.
    
    Attributes:
        id: Unique identifier for the version
        document_id: Foreign key to the parent document
        version_number: Sequential version number (1, 2, 3, ...)
        file_path: Path to the encrypted file for this version
        file_size: Size of the file in bytes
        content_type: MIME type of the document
        created_at: Timestamp when this version was created
    """
    
    __tablename__ = "document_versions"
    
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="versions",
    )
