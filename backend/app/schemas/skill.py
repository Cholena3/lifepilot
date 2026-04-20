"""Pydantic schemas for skill inventory management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.skill import ProficiencyLevel, SkillCategory


class SkillCreate(BaseModel):
    """Schema for creating a new skill.
    
    Requirement 24.1: Store skill name, category, and proficiency level
    """
    name: str = Field(..., min_length=1, max_length=100, description="Skill name")
    category: SkillCategory = Field(
        default=SkillCategory.OTHER,
        description="Skill category for grouping"
    )
    proficiency: ProficiencyLevel = Field(
        default=ProficiencyLevel.BEGINNER,
        description="Current proficiency level"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize skill name."""
        return v.strip()


class SkillUpdate(BaseModel):
    """Schema for updating an existing skill.
    
    Requirement 24.3: Record proficiency changes with timestamp
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[SkillCategory] = None
    proficiency: Optional[ProficiencyLevel] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize skill name."""
        if v is not None:
            return v.strip()
        return v


class SkillProficiencyHistoryResponse(BaseModel):
    """Schema for skill proficiency history entry."""
    id: UUID
    skill_id: UUID
    previous_level: Optional[ProficiencyLevel]
    new_level: ProficiencyLevel
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillResponse(BaseModel):
    """Schema for skill response.
    
    Requirement 24.4: Display skills grouped by category with visual proficiency indicators
    """
    id: UUID
    user_id: UUID
    name: str
    category: SkillCategory
    proficiency: ProficiencyLevel
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillWithHistoryResponse(SkillResponse):
    """Schema for skill response with proficiency history."""
    proficiency_history: list[SkillProficiencyHistoryResponse] = []


class SkillSuggestion(BaseModel):
    """Schema for skill suggestion.
    
    Requirement 24.5: Suggest skills to learn based on career goals
    """
    name: str
    category: str
    reason: str = Field(
        default="Recommended for your career goals",
        description="Reason for suggesting this skill"
    )


class SkillSuggestionsResponse(BaseModel):
    """Schema for skill suggestions response."""
    suggestions: list[SkillSuggestion]
    based_on_roles: list[str] = Field(
        default_factory=list,
        description="Career roles used to generate suggestions"
    )


class SkillsByCategory(BaseModel):
    """Schema for skills grouped by category."""
    category: SkillCategory
    skills: list[SkillResponse]


class SkillsGroupedResponse(BaseModel):
    """Schema for skills grouped by category response.
    
    Requirement 24.4: Display skills grouped by category
    """
    groups: list[SkillsByCategory]
    total_skills: int


class PaginatedSkillResponse(BaseModel):
    """Schema for paginated skill list response."""
    items: list[SkillResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[SkillResponse],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedSkillResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
