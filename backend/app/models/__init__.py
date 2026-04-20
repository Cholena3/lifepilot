# SQLAlchemy models module
from app.core.database import Base
from app.models.achievement import Achievement, AchievementCategory
from app.models.audit_log import AuditLog
from app.models.badge import Badge, BadgeType, BADGE_METADATA
from app.models.base import TimestampMixin, UUIDMixin
from app.models.budget import Budget, BudgetHistory, BudgetPeriod
from app.models.calendar_sync import CalendarSync, GoogleCalendarToken
from app.models.course import Course, LearningSession
from app.models.document import Document, DocumentVersion
from app.models.document_expiry import (
    DocumentExpiryAlert,
    DocumentExpiryAlertPreferences,
    ExpiryAlertType,
)
from app.models.emergency_info import EmergencyInfo, EmergencyInfoField, BloodType
from app.models.exam import (
    Exam,
    ExamApplication,
    ExamBookmark,
    ExamType,
    ApplicationStatus as ExamApplicationStatus,
)
from app.models.expense import Expense, ExpenseCategory
from app.models.health import FamilyMember, HealthRecord, HealthRecordCategory
from app.models.health_share import HealthRecordShare, HealthShareAccessLog
from app.models.interview import (
    InterviewNote,
    InterviewPreparationReminder,
    InterviewType,
    QuestionAnswer,
)
from app.models.job_application import (
    ApplicationFollowUpReminder,
    ApplicationSource,
    ApplicationStatus,
    ApplicationStatusHistory,
    JobApplication,
)
from app.models.life_score import LifeScore, ModuleType
from app.models.medicine import Medicine, MedicineDose, MedicineFrequency, DoseStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationPreferences,
    NotificationStatus,
)
from app.models.profile import CareerPreferences, Profile, StudentProfile
from app.models.resume import Resume, ResumeTemplate, ResumeVersion
from app.models.roadmap import (
    CareerRoadmap,
    MilestoneStatus,
    ResourceRecommendation,
    ResourceType,
    RoadmapMilestone,
    SkillGap,
)
from app.models.share_link import ShareLink, ShareLinkAccess
from app.models.skill import (
    ProficiencyLevel,
    Skill,
    SkillCategory,
    SkillProficiencyHistory,
)
from app.models.split import (
    ExpenseSplit,
    Settlement,
    SharedExpense,
    SplitGroup,
    SplitGroupMember,
    SplitType,
)
from app.models.user import User
from app.models.vital import Vital, VitalTargetRange, VitalType
from app.models.wardrobe import (
    WardrobeItem,
    WearLog,
    Outfit,
    OutfitItem,
    OutfitPlan,
    PackingList,
    PackingListItem,
    ClothingType,
    ClothingPattern,
    Occasion,
)
from app.models.weekly_summary import WeeklySummary

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "Profile",
    "StudentProfile",
    "CareerPreferences",
    "Achievement",
    "AchievementCategory",
    "ApplicationFollowUpReminder",
    "ApplicationSource",
    "ApplicationStatus",
    "ApplicationStatusHistory",
    "AuditLog",
    "Badge",
    "BadgeType",
    "BADGE_METADATA",
    "BloodType",
    "Budget",
    "BudgetHistory",
    "BudgetPeriod",
    "CalendarSync",
    "CareerRoadmap",
    "Course",
    "Document",
    "DocumentExpiryAlert",
    "DocumentExpiryAlertPreferences",
    "DocumentVersion",
    "DoseStatus",
    "EmergencyInfo",
    "EmergencyInfoField",
    "Exam",
    "ExamApplication",
    "ExamApplicationStatus",
    "ExamBookmark",
    "ExamType",
    "Expense",
    "ExpenseCategory",
    "ExpenseSplit",
    "ExpiryAlertType",
    "FamilyMember",
    "GoogleCalendarToken",
    "HealthRecord",
    "HealthRecordCategory",
    "HealthRecordShare",
    "HealthShareAccessLog",
    "InterviewNote",
    "InterviewPreparationReminder",
    "InterviewType",
    "JobApplication",
    "LearningSession",
    "LifeScore",
    "Medicine",
    "MedicineDose",
    "MedicineFrequency",
    "MilestoneStatus",
    "ModuleType",
    "Notification",
    "NotificationChannel",
    "NotificationPreferences",
    "NotificationStatus",
    "ProficiencyLevel",
    "QuestionAnswer",
    "ResourceRecommendation",
    "ResourceType",
    "Resume",
    "ResumeTemplate",
    "ResumeVersion",
    "RoadmapMilestone",
    "Settlement",
    "SharedExpense",
    "ShareLink",
    "ShareLinkAccess",
    "Skill",
    "SkillCategory",
    "SkillGap",
    "SkillProficiencyHistory",
    "SplitGroup",
    "SplitGroupMember",
    "SplitType",
    "Vital",
    "VitalTargetRange",
    "VitalType",
    "WardrobeItem",
    "WearLog",
    "WeeklySummary",
    "Outfit",
    "OutfitItem",
    "OutfitPlan",
    "PackingList",
    "PackingListItem",
    "ClothingType",
    "ClothingPattern",
    "Occasion",
]
