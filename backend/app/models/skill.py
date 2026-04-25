"""Skill models for career module skill inventory management."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ProficiencyLevel(str, enum.Enum):
    """Proficiency levels for skills.
    
    Requirement 24.2: Support proficiency levels: Beginner, Intermediate, Advanced, Expert
    """
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillCategory(str, enum.Enum):
    """Categories for organizing skills."""
    PROGRAMMING = "programming"
    FRAMEWORK = "framework"
    DATABASE = "database"
    DEVOPS = "devops"
    CLOUD = "cloud"
    SOFT_SKILL = "soft_skill"
    LANGUAGE = "language"
    DESIGN = "design"
    DATA_SCIENCE = "data_science"
    OTHER = "other"


class Skill(Base, UUIDMixin, TimestampMixin):
    """User skill with proficiency tracking.
    
    Requirement 24.1: Store skill name, category, and proficiency level
    Requirement 24.4: Display skills grouped by category with visual proficiency indicators
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        name: Skill name
        category: Skill category for grouping
        proficiency: Current proficiency level
    """

    __tablename__ = "skills"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    category: Mapped[SkillCategory] = mapped_column(
        Enum(SkillCategory),
        nullable=False,
        default=SkillCategory.OTHER,
    )
    proficiency: Mapped[ProficiencyLevel] = mapped_column(
        Enum(ProficiencyLevel),
        nullable=False,
        default=ProficiencyLevel.BEGINNER,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="skills",
    )
    proficiency_history: Mapped[list["SkillProficiencyHistory"]] = relationship(
        "SkillProficiencyHistory",
        back_populates="skill",
        cascade="all, delete-orphan",
        order_by="SkillProficiencyHistory.changed_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name={self.name}, proficiency={self.proficiency})>"


class SkillProficiencyHistory(Base, UUIDMixin):
    """History of proficiency level changes for a skill.
    
    Requirement 24.3: Record proficiency changes with timestamp
    
    Attributes:
        id: UUID primary key
        skill_id: Foreign key to Skill
        previous_level: Previous proficiency level (None for initial)
        new_level: New proficiency level
        changed_at: Timestamp of the change
    """

    __tablename__ = "skill_proficiency_history"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_level: Mapped[Optional[ProficiencyLevel]] = mapped_column(
        Enum(ProficiencyLevel),
        nullable=True,
    )
    new_level: Mapped[ProficiencyLevel] = mapped_column(
        Enum(ProficiencyLevel),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    skill: Mapped["Skill"] = relationship(
        "Skill",
        back_populates="proficiency_history",
    )

    def __repr__(self) -> str:
        return f"<SkillProficiencyHistory(skill_id={self.skill_id}, {self.previous_level} -> {self.new_level})>"


# Skill suggestions based on career goals
# Requirement 24.5: Suggest skills to learn based on career goals
SKILL_SUGGESTIONS_BY_ROLE: dict[str, list[dict[str, str]]] = {
    "software engineer": [
        {"name": "Python", "category": "programming"},
        {"name": "JavaScript", "category": "programming"},
        {"name": "Git", "category": "devops"},
        {"name": "SQL", "category": "database"},
        {"name": "Docker", "category": "devops"},
        {"name": "REST APIs", "category": "framework"},
    ],
    "frontend developer": [
        {"name": "JavaScript", "category": "programming"},
        {"name": "TypeScript", "category": "programming"},
        {"name": "React", "category": "framework"},
        {"name": "CSS", "category": "design"},
        {"name": "HTML", "category": "programming"},
        {"name": "Next.js", "category": "framework"},
    ],
    "backend developer": [
        {"name": "Python", "category": "programming"},
        {"name": "Java", "category": "programming"},
        {"name": "Node.js", "category": "framework"},
        {"name": "PostgreSQL", "category": "database"},
        {"name": "Redis", "category": "database"},
        {"name": "Docker", "category": "devops"},
    ],
    "data scientist": [
        {"name": "Python", "category": "programming"},
        {"name": "Machine Learning", "category": "data_science"},
        {"name": "TensorFlow", "category": "framework"},
        {"name": "Pandas", "category": "data_science"},
        {"name": "SQL", "category": "database"},
        {"name": "Statistics", "category": "data_science"},
    ],
    "devops engineer": [
        {"name": "Docker", "category": "devops"},
        {"name": "Kubernetes", "category": "devops"},
        {"name": "AWS", "category": "cloud"},
        {"name": "Terraform", "category": "devops"},
        {"name": "CI/CD", "category": "devops"},
        {"name": "Linux", "category": "devops"},
    ],
    "product manager": [
        {"name": "Agile", "category": "soft_skill"},
        {"name": "User Research", "category": "soft_skill"},
        {"name": "Data Analysis", "category": "data_science"},
        {"name": "Communication", "category": "soft_skill"},
        {"name": "SQL", "category": "database"},
        {"name": "Roadmapping", "category": "soft_skill"},
    ],
    "full stack developer": [
        {"name": "JavaScript", "category": "programming"},
        {"name": "Python", "category": "programming"},
        {"name": "React", "category": "framework"},
        {"name": "Node.js", "category": "framework"},
        {"name": "PostgreSQL", "category": "database"},
        {"name": "Docker", "category": "devops"},
    ],
}
