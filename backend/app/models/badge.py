"""Badge model for gamification achievements and milestones.

Requirement 33.5: Award badges for achievements and milestones
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class BadgeType(str, enum.Enum):
    """Badge types for various achievements and milestones.
    
    Requirement 33.5: Award badges for achievements and milestones
    """
    # Profile milestones
    PROFILE_COMPLETE = "profile_complete"
    
    # Document milestones
    FIRST_DOCUMENT = "first_document"
    DOCUMENT_ORGANIZER = "document_organizer"  # 10+ documents
    DOCUMENT_MASTER = "document_master"  # 50+ documents
    
    # Finance milestones
    FIRST_EXPENSE = "first_expense"
    BUDGET_CREATOR = "budget_creator"
    EXPENSE_TRACKER = "expense_tracker"  # 30+ expenses logged
    BUDGET_MASTER = "budget_master"  # Stayed within budget for a month
    
    # Health milestones
    FIRST_HEALTH_RECORD = "first_health_record"
    MEDICINE_ADHERENT = "medicine_adherent"  # 7-day streak
    VITAL_TRACKER = "vital_tracker"  # 30+ vitals logged
    HEALTH_CONSCIOUS = "health_conscious"  # 90% medicine adherence
    
    # Wardrobe milestones
    FIRST_WARDROBE_ITEM = "first_wardrobe_item"
    FASHION_ENTHUSIAST = "fashion_enthusiast"  # 20+ items
    OUTFIT_PLANNER = "outfit_planner"  # 5+ planned outfits
    
    # Career milestones
    FIRST_SKILL = "first_skill"
    SKILL_BUILDER = "skill_builder"  # 10+ skills
    FIRST_COURSE = "first_course"
    COURSE_COMPLETER = "course_completer"  # First course completed
    LIFELONG_LEARNER = "lifelong_learner"  # 5+ courses completed
    FIRST_APPLICATION = "first_application"
    JOB_HUNTER = "job_hunter"  # 10+ applications
    INTERVIEW_PRO = "interview_pro"  # 5+ interviews
    
    # Exam milestones
    FIRST_EXAM_BOOKMARK = "first_exam_bookmark"
    EXAM_EXPLORER = "exam_explorer"  # 10+ bookmarks
    EXAM_APPLICANT = "exam_applicant"  # First exam applied
    
    # Life Score milestones
    SCORE_RISING = "score_rising"  # Score increased by 10+ points
    SCORE_ACHIEVER = "score_achiever"  # Reached score of 50+
    SCORE_MASTER = "score_master"  # Reached score of 80+
    CONSISTENT_USER = "consistent_user"  # Active for 7 consecutive days
    POWER_USER = "power_user"  # Active for 30 consecutive days


# Badge metadata with names and descriptions
BADGE_METADATA = {
    BadgeType.PROFILE_COMPLETE: {
        "name": "Profile Complete",
        "description": "Completed your profile with all required information",
    },
    BadgeType.FIRST_DOCUMENT: {
        "name": "First Document",
        "description": "Uploaded your first document to the vault",
    },
    BadgeType.DOCUMENT_ORGANIZER: {
        "name": "Document Organizer",
        "description": "Uploaded 10 or more documents",
    },
    BadgeType.DOCUMENT_MASTER: {
        "name": "Document Master",
        "description": "Uploaded 50 or more documents",
    },
    BadgeType.FIRST_EXPENSE: {
        "name": "First Expense",
        "description": "Logged your first expense",
    },
    BadgeType.BUDGET_CREATOR: {
        "name": "Budget Creator",
        "description": "Created your first budget",
    },
    BadgeType.EXPENSE_TRACKER: {
        "name": "Expense Tracker",
        "description": "Logged 30 or more expenses",
    },
    BadgeType.BUDGET_MASTER: {
        "name": "Budget Master",
        "description": "Stayed within budget for an entire month",
    },
    BadgeType.FIRST_HEALTH_RECORD: {
        "name": "First Health Record",
        "description": "Added your first health record",
    },
    BadgeType.MEDICINE_ADHERENT: {
        "name": "Medicine Adherent",
        "description": "Maintained a 7-day medicine adherence streak",
    },
    BadgeType.VITAL_TRACKER: {
        "name": "Vital Tracker",
        "description": "Logged 30 or more vital readings",
    },
    BadgeType.HEALTH_CONSCIOUS: {
        "name": "Health Conscious",
        "description": "Achieved 90% medicine adherence",
    },
    BadgeType.FIRST_WARDROBE_ITEM: {
        "name": "First Wardrobe Item",
        "description": "Added your first item to the wardrobe",
    },
    BadgeType.FASHION_ENTHUSIAST: {
        "name": "Fashion Enthusiast",
        "description": "Added 20 or more wardrobe items",
    },
    BadgeType.OUTFIT_PLANNER: {
        "name": "Outfit Planner",
        "description": "Planned 5 or more outfits",
    },
    BadgeType.FIRST_SKILL: {
        "name": "First Skill",
        "description": "Added your first skill to your profile",
    },
    BadgeType.SKILL_BUILDER: {
        "name": "Skill Builder",
        "description": "Added 10 or more skills",
    },
    BadgeType.FIRST_COURSE: {
        "name": "First Course",
        "description": "Started your first learning course",
    },
    BadgeType.COURSE_COMPLETER: {
        "name": "Course Completer",
        "description": "Completed your first course",
    },
    BadgeType.LIFELONG_LEARNER: {
        "name": "Lifelong Learner",
        "description": "Completed 5 or more courses",
    },
    BadgeType.FIRST_APPLICATION: {
        "name": "First Application",
        "description": "Submitted your first job application",
    },
    BadgeType.JOB_HUNTER: {
        "name": "Job Hunter",
        "description": "Submitted 10 or more job applications",
    },
    BadgeType.INTERVIEW_PRO: {
        "name": "Interview Pro",
        "description": "Completed 5 or more interviews",
    },
    BadgeType.FIRST_EXAM_BOOKMARK: {
        "name": "First Exam Bookmark",
        "description": "Bookmarked your first exam",
    },
    BadgeType.EXAM_EXPLORER: {
        "name": "Exam Explorer",
        "description": "Bookmarked 10 or more exams",
    },
    BadgeType.EXAM_APPLICANT: {
        "name": "Exam Applicant",
        "description": "Applied for your first exam",
    },
    BadgeType.SCORE_RISING: {
        "name": "Score Rising",
        "description": "Increased your Life Score by 10 or more points",
    },
    BadgeType.SCORE_ACHIEVER: {
        "name": "Score Achiever",
        "description": "Reached a Life Score of 50 or higher",
    },
    BadgeType.SCORE_MASTER: {
        "name": "Score Master",
        "description": "Reached a Life Score of 80 or higher",
    },
    BadgeType.CONSISTENT_USER: {
        "name": "Consistent User",
        "description": "Used LifePilot for 7 consecutive days",
    },
    BadgeType.POWER_USER: {
        "name": "Power User",
        "description": "Used LifePilot for 30 consecutive days",
    },
}


class Badge(Base, UUIDMixin, TimestampMixin):
    """Badge earned by a user for achievements and milestones.
    
    Requirement 33.5: Award badges for achievements and milestones
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        badge_type: Type of badge earned
        name: Display name of the badge
        description: Description of how the badge was earned
        earned_at: When the badge was earned
    """

    __tablename__ = "badges"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="badges",
    )

    def __repr__(self) -> str:
        return f"<Badge(id={self.id}, user_id={self.user_id}, type={self.badge_type})>"
