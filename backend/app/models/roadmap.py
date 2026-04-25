"""Career roadmap models for professional development tracking.

Validates: Requirements 26.1, 26.2, 26.3, 26.4, 26.5
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class MilestoneStatus(str, enum.Enum):
    """Status of a roadmap milestone."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ResourceType(str, enum.Enum):
    """Type of learning resource."""
    COURSE = "course"
    BOOK = "book"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"
    VIDEO = "video"
    ARTICLE = "article"
    PROJECT = "project"
    CERTIFICATION = "certification"
    OTHER = "other"


class CareerRoadmap(Base, UUIDMixin, TimestampMixin):
    """Career roadmap for professional development.
    
    Requirement 26.1: Generate roadmap from career goals with milestones
    Requirement 26.4: Track roadmap progress
    Requirement 26.5: Adjust roadmap based on user progress
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        target_role: Target career role/position
        target_timeline_months: Target timeline in months
        current_progress: Overall progress percentage (0-100)
        is_active: Whether this is the active roadmap
        notes: Optional notes about the roadmap
    """

    __tablename__ = "career_roadmaps"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_role: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_timeline_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=12,
    )
    current_progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="roadmaps",
    )
    milestones: Mapped[list["RoadmapMilestone"]] = relationship(
        "RoadmapMilestone",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapMilestone.order_index",
    )
    skill_gaps: Mapped[list["SkillGap"]] = relationship(
        "SkillGap",
        back_populates="roadmap",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CareerRoadmap(id={self.id}, target_role={self.target_role}, progress={self.current_progress}%)>"


class RoadmapMilestone(Base, UUIDMixin, TimestampMixin):
    """Milestone within a career roadmap.
    
    Requirement 26.1: Roadmap milestones
    Requirement 26.4: Track milestone completion
    
    Attributes:
        id: UUID primary key
        roadmap_id: Foreign key to CareerRoadmap
        title: Milestone title
        description: Detailed description
        order_index: Order in the roadmap
        target_date: Target completion date
        completed_at: Actual completion date
        status: Current status
        required_skills: Skills needed for this milestone
    """

    __tablename__ = "roadmap_milestones"

    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("career_roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    target_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus),
        nullable=False,
        default=MilestoneStatus.NOT_STARTED,
    )
    required_skills: Mapped[Optional[list[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    roadmap: Mapped["CareerRoadmap"] = relationship(
        "CareerRoadmap",
        back_populates="milestones",
    )

    def __repr__(self) -> str:
        return f"<RoadmapMilestone(id={self.id}, title={self.title}, status={self.status})>"


class SkillGap(Base, UUIDMixin, TimestampMixin):
    """Identified skill gap for a career roadmap.
    
    Requirement 26.2: Identify skill gaps between current skills and goal requirements
    
    Attributes:
        id: UUID primary key
        roadmap_id: Foreign key to CareerRoadmap
        skill_name: Name of the required skill
        current_level: User's current proficiency (None if not possessed)
        required_level: Required proficiency level
        priority: Priority level (1=highest)
        is_filled: Whether the gap has been filled
    """

    __tablename__ = "skill_gaps"

    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("career_roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    current_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    required_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    is_filled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Relationships
    roadmap: Mapped["CareerRoadmap"] = relationship(
        "CareerRoadmap",
        back_populates="skill_gaps",
    )
    recommendations: Mapped[list["ResourceRecommendation"]] = relationship(
        "ResourceRecommendation",
        back_populates="skill_gap",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SkillGap(id={self.id}, skill={self.skill_name}, filled={self.is_filled})>"


class ResourceRecommendation(Base, UUIDMixin, TimestampMixin):
    """Recommended resource to fill a skill gap.
    
    Requirement 26.3: Recommend courses and resources to fill skill gaps
    
    Attributes:
        id: UUID primary key
        skill_gap_id: Foreign key to SkillGap
        title: Resource title
        resource_type: Type of resource
        url: Resource URL
        platform: Platform/provider name
        estimated_hours: Estimated time to complete
        is_completed: Whether user has completed this resource
        completed_at: Completion timestamp
    """

    __tablename__ = "resource_recommendations"

    skill_gap_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("skill_gaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType),
        nullable=False,
        default=ResourceType.COURSE,
    )
    url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    platform: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    estimated_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    skill_gap: Mapped["SkillGap"] = relationship(
        "SkillGap",
        back_populates="recommendations",
    )

    def __repr__(self) -> str:
        return f"<ResourceRecommendation(id={self.id}, title={self.title}, type={self.resource_type})>"


# Role-based skill requirements for roadmap generation
# Requirement 26.1, 26.2: Define required skills for different career goals
ROLE_SKILL_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "software engineer": [
        {"name": "Python", "level": "intermediate"},
        {"name": "JavaScript", "level": "intermediate"},
        {"name": "Git", "level": "intermediate"},
        {"name": "SQL", "level": "intermediate"},
        {"name": "Data Structures", "level": "intermediate"},
        {"name": "Algorithms", "level": "intermediate"},
        {"name": "System Design", "level": "beginner"},
        {"name": "Testing", "level": "beginner"},
    ],
    "frontend developer": [
        {"name": "JavaScript", "level": "advanced"},
        {"name": "TypeScript", "level": "intermediate"},
        {"name": "React", "level": "intermediate"},
        {"name": "CSS", "level": "advanced"},
        {"name": "HTML", "level": "advanced"},
        {"name": "Responsive Design", "level": "intermediate"},
        {"name": "Web Performance", "level": "beginner"},
        {"name": "Accessibility", "level": "beginner"},
    ],
    "backend developer": [
        {"name": "Python", "level": "advanced"},
        {"name": "SQL", "level": "advanced"},
        {"name": "REST APIs", "level": "intermediate"},
        {"name": "Database Design", "level": "intermediate"},
        {"name": "Docker", "level": "intermediate"},
        {"name": "Security", "level": "beginner"},
        {"name": "Caching", "level": "beginner"},
        {"name": "Message Queues", "level": "beginner"},
    ],
    "data scientist": [
        {"name": "Python", "level": "advanced"},
        {"name": "Machine Learning", "level": "intermediate"},
        {"name": "Statistics", "level": "advanced"},
        {"name": "SQL", "level": "intermediate"},
        {"name": "Data Visualization", "level": "intermediate"},
        {"name": "Deep Learning", "level": "beginner"},
        {"name": "Feature Engineering", "level": "intermediate"},
        {"name": "Model Deployment", "level": "beginner"},
    ],
    "devops engineer": [
        {"name": "Linux", "level": "advanced"},
        {"name": "Docker", "level": "advanced"},
        {"name": "Kubernetes", "level": "intermediate"},
        {"name": "CI/CD", "level": "intermediate"},
        {"name": "AWS", "level": "intermediate"},
        {"name": "Terraform", "level": "intermediate"},
        {"name": "Monitoring", "level": "intermediate"},
        {"name": "Scripting", "level": "intermediate"},
    ],
    "full stack developer": [
        {"name": "JavaScript", "level": "advanced"},
        {"name": "Python", "level": "intermediate"},
        {"name": "React", "level": "intermediate"},
        {"name": "Node.js", "level": "intermediate"},
        {"name": "SQL", "level": "intermediate"},
        {"name": "REST APIs", "level": "intermediate"},
        {"name": "Docker", "level": "beginner"},
        {"name": "Git", "level": "intermediate"},
    ],
}

# Resource recommendations by skill
# Requirement 26.3: Recommend courses and resources
SKILL_RESOURCES: dict[str, list[dict[str, str]]] = {
    "Python": [
        {"title": "Python for Everybody", "type": "course", "platform": "Coursera", "hours": "40"},
        {"title": "Automate the Boring Stuff with Python", "type": "book", "platform": "No Starch Press", "hours": "20"},
        {"title": "Python Documentation", "type": "documentation", "platform": "python.org", "hours": "10"},
    ],
    "JavaScript": [
        {"title": "JavaScript: The Complete Guide", "type": "course", "platform": "Udemy", "hours": "50"},
        {"title": "Eloquent JavaScript", "type": "book", "platform": "Online", "hours": "30"},
        {"title": "MDN JavaScript Guide", "type": "documentation", "platform": "MDN", "hours": "15"},
    ],
    "React": [
        {"title": "React - The Complete Guide", "type": "course", "platform": "Udemy", "hours": "40"},
        {"title": "React Documentation", "type": "documentation", "platform": "react.dev", "hours": "10"},
        {"title": "Build a React Project", "type": "project", "platform": "Self-guided", "hours": "20"},
    ],
    "SQL": [
        {"title": "SQL for Data Science", "type": "course", "platform": "Coursera", "hours": "20"},
        {"title": "PostgreSQL Tutorial", "type": "tutorial", "platform": "PostgreSQL.org", "hours": "10"},
        {"title": "SQL Practice Problems", "type": "project", "platform": "LeetCode", "hours": "15"},
    ],
    "Docker": [
        {"title": "Docker Mastery", "type": "course", "platform": "Udemy", "hours": "20"},
        {"title": "Docker Documentation", "type": "documentation", "platform": "docker.com", "hours": "10"},
        {"title": "Containerize an Application", "type": "project", "platform": "Self-guided", "hours": "10"},
    ],
    "Git": [
        {"title": "Git Complete", "type": "course", "platform": "Udemy", "hours": "10"},
        {"title": "Pro Git Book", "type": "book", "platform": "git-scm.com", "hours": "15"},
        {"title": "Git Practice", "type": "tutorial", "platform": "learngitbranching.js.org", "hours": "5"},
    ],
    "Machine Learning": [
        {"title": "Machine Learning by Andrew Ng", "type": "course", "platform": "Coursera", "hours": "60"},
        {"title": "Hands-On Machine Learning", "type": "book", "platform": "O'Reilly", "hours": "40"},
        {"title": "Kaggle Competitions", "type": "project", "platform": "Kaggle", "hours": "30"},
    ],
    "AWS": [
        {"title": "AWS Certified Solutions Architect", "type": "certification", "platform": "AWS", "hours": "80"},
        {"title": "AWS Documentation", "type": "documentation", "platform": "aws.amazon.com", "hours": "20"},
        {"title": "Deploy an Application on AWS", "type": "project", "platform": "Self-guided", "hours": "15"},
    ],
}
