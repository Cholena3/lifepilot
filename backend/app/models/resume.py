"""Resume models for career module resume builder.

Requirement 30: Resume Builder
- Populate resume from profile, skills, achievements
- Support multiple templates
- Export as PDF
- Save multiple versions
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ResumeTemplate(str, enum.Enum):
    """Available resume templates.
    
    Requirement 30.2: Support multiple resume templates
    """
    CLASSIC = "classic"
    MODERN = "modern"
    MINIMAL = "minimal"
    PROFESSIONAL = "professional"
    CREATIVE = "creative"


class Resume(Base, UUIDMixin, TimestampMixin):
    """User resume with template and content.
    
    Requirement 30.1: Populate resume from profile, skills, achievements
    Requirement 30.2: Support multiple resume templates
    Requirement 30.5: Allow saving multiple resume versions
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        name: Resume name/title for identification
        template: Selected resume template
        content: JSON content with resume sections
        pdf_url: URL to generated PDF (if exported)
        version: Version number for this resume
    """

    __tablename__ = "resumes"

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
    template: Mapped[ResumeTemplate] = mapped_column(
        Enum(ResumeTemplate),
        nullable=False,
        default=ResumeTemplate.CLASSIC,
    )
    # JSON content structure:
    # {
    #   "personal_info": {...},
    #   "summary": "...",
    #   "education": [...],
    #   "experience": [...],
    #   "skills": [...],
    #   "achievements": [...],
    #   "certifications": [...],
    #   "projects": [...],
    #   "custom_sections": [...]
    # }
    content: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    pdf_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="resumes",
    )
    versions: Mapped[list["ResumeVersion"]] = relationship(
        "ResumeVersion",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeVersion.version_number.desc()",
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, name={self.name}, template={self.template})>"


class ResumeVersion(Base, UUIDMixin):
    """Version history for a resume.
    
    Requirement 30.5: Allow saving multiple resume versions
    
    Attributes:
        id: UUID primary key
        resume_id: Foreign key to Resume
        version_number: Version number
        content: JSON content snapshot at this version
        pdf_url: URL to PDF for this version
        created_at: Timestamp when version was created
    """

    __tablename__ = "resume_versions"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    pdf_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="versions",
    )

    def __repr__(self) -> str:
        return f"<ResumeVersion(resume_id={self.resume_id}, version={self.version_number})>"
