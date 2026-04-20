"""Pydantic schemas for resume builder.

Requirement 30: Resume Builder
"""

from datetime import date, datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.resume import ResumeTemplate


# ============================================================================
# Content Section Schemas
# ============================================================================

class PersonalInfo(BaseModel):
    """Personal information section of resume."""
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class EducationEntry(BaseModel):
    """Education entry in resume."""
    institution: str = Field(..., min_length=1, max_length=255)
    degree: str = Field(..., min_length=1, max_length=255)
    field_of_study: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    gpa: Optional[str] = None
    description: Optional[str] = None


class ExperienceEntry(BaseModel):
    """Work experience entry in resume."""
    company: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class SkillEntry(BaseModel):
    """Skill entry in resume."""
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None
    proficiency: Optional[str] = None


class AchievementEntry(BaseModel):
    """Achievement entry in resume."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    achieved_date: Optional[date] = Field(default=None, alias="date")
    category: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)


class CertificationEntry(BaseModel):
    """Certification entry in resume."""
    name: str = Field(..., min_length=1, max_length=255)
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None


class ProjectEntry(BaseModel):
    """Project entry in resume."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CustomSection(BaseModel):
    """Custom section in resume."""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class ResumeContent(BaseModel):
    """Complete resume content structure.
    
    Requirement 30.1: Populate resume from profile, skills, achievements
    """
    personal_info: Optional[PersonalInfo] = None
    summary: Optional[str] = Field(None, max_length=2000)
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    achievements: list[AchievementEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    custom_sections: list[CustomSection] = Field(default_factory=list)


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ResumeCreate(BaseModel):
    """Schema for creating a new resume.
    
    Requirement 30.1: Populate resume from profile, skills, achievements
    Requirement 30.2: Support multiple resume templates
    """
    name: str = Field(..., min_length=1, max_length=255, description="Resume name")
    template: ResumeTemplate = Field(
        default=ResumeTemplate.CLASSIC,
        description="Resume template"
    )
    content: Optional[ResumeContent] = Field(
        default=None,
        description="Resume content (optional, can be populated from profile)"
    )
    populate_from_profile: bool = Field(
        default=True,
        description="Whether to populate from user profile, skills, and achievements"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize resume name."""
        return v.strip()


class ResumeUpdate(BaseModel):
    """Schema for updating an existing resume.
    
    Requirement 30.3: Edit resume content without affecting source data
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    template: Optional[ResumeTemplate] = None
    content: Optional[ResumeContent] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize resume name."""
        if v is not None:
            return v.strip()
        return v


class ResumeResponse(BaseModel):
    """Schema for resume response.
    
    Requirement 30.5: Allow saving multiple resume versions
    """
    id: UUID
    user_id: UUID
    name: str
    template: ResumeTemplate
    content: dict[str, Any]
    pdf_url: Optional[str]
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeVersionResponse(BaseModel):
    """Schema for resume version response.
    
    Requirement 30.5: Allow saving multiple resume versions
    """
    id: UUID
    resume_id: UUID
    version_number: int
    content: dict[str, Any]
    pdf_url: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeSummaryResponse(BaseModel):
    """Schema for resume summary (list view)."""
    id: UUID
    name: str
    template: ResumeTemplate
    version: int
    pdf_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedResumeResponse(BaseModel):
    """Schema for paginated resume list response."""
    items: list[ResumeSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[ResumeSummaryResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResumeResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ResumeTemplateInfo(BaseModel):
    """Schema for resume template information."""
    id: ResumeTemplate
    name: str
    description: str
    preview_url: Optional[str] = None


class ResumeTemplatesResponse(BaseModel):
    """Schema for available templates response.
    
    Requirement 30.2: Support multiple resume templates
    """
    templates: list[ResumeTemplateInfo]


class ResumePDFResponse(BaseModel):
    """Schema for PDF export response.
    
    Requirement 30.4: Export resumes in PDF format
    """
    resume_id: UUID
    pdf_url: str
    generated_at: datetime


class ResumePopulateRequest(BaseModel):
    """Schema for populating resume from profile data.
    
    Requirement 30.1: Populate resume from profile, skills, achievements
    """
    include_education: bool = True
    include_skills: bool = True
    include_achievements: bool = True
    include_experience: bool = True
    achievement_categories: Optional[list[str]] = None
    skill_categories: Optional[list[str]] = None
    max_achievements: int = Field(default=10, ge=1, le=50)
    max_skills: int = Field(default=20, ge=1, le=100)
