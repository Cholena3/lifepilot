"""Health module models for health record management.

Includes HealthRecord and FamilyMember models for storing and organizing
health records for users and their family members.

Validates: Requirements 14.1, 14.2, 14.5
"""

import uuid
from datetime import datetime, date
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class HealthRecordCategory(str, Enum):
    """Valid health record categories.
    
    Validates: Requirements 14.1
    """
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    SCAN = "scan"
    VACCINE = "vaccine"
    INSURANCE = "insurance"


class FamilyMember(Base, UUIDMixin, TimestampMixin):
    """Family member model for managing health records of family members.
    
    Validates: Requirements 14.2
    
    Attributes:
        id: Unique identifier for the family member
        user_id: Foreign key to the user who manages this family member
        name: Full name of the family member
        relationship: Relationship to the user (e.g., spouse, child, parent)
        date_of_birth: Date of birth of the family member
        gender: Gender of the family member
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "family_members"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    relationship: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    date_of_birth: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    
    gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # Relationships
    health_records: Mapped[List["HealthRecord"]] = sa_relationship(
        "HealthRecord",
        back_populates="family_member",
        cascade="all, delete-orphan",
    )


class HealthRecord(Base, UUIDMixin, TimestampMixin):
    """Health record model for storing user health documents.
    
    Validates: Requirements 14.1, 14.2, 14.5
    
    Attributes:
        id: Unique identifier for the health record
        user_id: Foreign key to the user who owns the record
        family_member_id: Optional foreign key to family member (null = self)
        category: Record category (prescription, lab_report, scan, vaccine, insurance)
        title: Title/description of the health record
        file_path: Path to the encrypted file in storage
        content_type: MIME type of the document
        file_size: Size of the file in bytes
        encryption_key: Key used for AES-256 encryption
        ocr_text: Extracted text from OCR processing
        extracted_data: JSON field for structured OCR data
        record_date: Date of the health record/visit
        doctor_name: Name of the doctor (for prescriptions)
        hospital_name: Name of the hospital/clinic
        notes: Additional notes about the record
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "health_records"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    family_member_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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
    
    ocr_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    extracted_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    record_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )
    
    doctor_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    hospital_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    family_member: Mapped[Optional["FamilyMember"]] = sa_relationship(
        "FamilyMember",
        back_populates="health_records",
    )
