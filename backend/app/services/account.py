"""Account management service for data export and deletion.

Validates: Requirements 36.5, 36.6
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthenticationError, NotFoundError, ValidationError
from app.models.achievement import Achievement
from app.models.badge import Badge
from app.models.budget import Budget
from app.models.course import Course
from app.models.document import Document
from app.models.emergency_info import EmergencyInfo
from app.models.exam import ExamApplication, ExamBookmark
from app.models.expense import Expense, ExpenseCategory
from app.models.health import FamilyMember, HealthRecord
from app.models.job_application import JobApplication
from app.models.life_score import LifeScore
from app.models.medicine import Medicine
from app.models.notification import Notification, NotificationPreferences
from app.models.profile import CareerPreferences, Profile, StudentProfile
from app.models.resume import Resume
from app.models.roadmap import CareerRoadmap
from app.models.skill import Skill
from app.models.user import User
from app.models.vital import Vital
from app.models.wardrobe import Outfit, OutfitPlan, PackingList, WardrobeItem
from app.models.weekly_summary import WeeklySummary
from app.schemas.account import (
    AccountDeletionCancelResponse,
    AccountDeletionResponse,
    AccountDeletionStatusResponse,
    DataExportResponse,
)
from app.services.auth import verify_password

logger = logging.getLogger(__name__)

# Deletion grace period in days
DELETION_GRACE_PERIOD_DAYS = 30


def _serialize_model(obj: Any) -> dict[str, Any]:
    """Serialize a SQLAlchemy model to a dictionary.
    
    Handles common types like UUID, datetime, Decimal.
    """
    if obj is None:
        return None
    
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, UUID):
            result[column.name] = str(value)
        elif isinstance(value, datetime):
            result[column.name] = value.isoformat()
        elif isinstance(value, Decimal):
            result[column.name] = float(value)
        elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes, dict)):
            result[column.name] = list(value)
        else:
            result[column.name] = value
    return result


def _serialize_list(items: list) -> list[dict[str, Any]]:
    """Serialize a list of SQLAlchemy models."""
    return [_serialize_model(item) for item in items]


class AccountService:
    """Service for account management operations.
    
    Validates: Requirements 36.5, 36.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session."""
        self.db = db
    
    async def export_user_data(self, user_id: UUID) -> DataExportResponse:
        """Export all user data in a portable JSON format.
        
        Validates: Requirements 36.5
        
        Args:
            user_id: UUID of the user requesting export
            
        Returns:
            DataExportResponse containing all user data
        """
        # Get user with related data
        user = await self._get_user(user_id)
        
        # Get profile data
        profile = await self._get_profile(user_id)
        student_profile = await self._get_student_profile(user_id)
        career_preferences = await self._get_career_preferences(user_id)
        
        # Get documents
        documents = await self._get_documents(user_id)
        
        # Get financial data
        expenses = await self._get_expenses(user_id)
        expense_categories = await self._get_expense_categories(user_id)
        budgets = await self._get_budgets(user_id)
        
        # Get health data
        health_records = await self._get_health_records(user_id)
        family_members = await self._get_family_members(user_id)
        medicines = await self._get_medicines(user_id)
        vitals = await self._get_vitals(user_id)
        emergency_info = await self._get_emergency_info(user_id)
        
        # Get wardrobe data
        wardrobe_items = await self._get_wardrobe_items(user_id)
        outfits = await self._get_outfits(user_id)
        outfit_plans = await self._get_outfit_plans(user_id)
        packing_lists = await self._get_packing_lists(user_id)
        
        # Get career data
        skills = await self._get_skills(user_id)
        courses = await self._get_courses(user_id)
        roadmaps = await self._get_roadmaps(user_id)
        job_applications = await self._get_job_applications(user_id)
        achievements = await self._get_achievements(user_id)
        resumes = await self._get_resumes(user_id)
        
        # Get exam data
        exam_bookmarks = await self._get_exam_bookmarks(user_id)
        exam_applications = await self._get_exam_applications(user_id)
        
        # Get notification data
        notifications = await self._get_notifications(user_id)
        notification_preferences = await self._get_notification_preferences(user_id)
        
        # Get analytics data
        life_scores = await self._get_life_scores(user_id)
        badges = await self._get_badges(user_id)
        weekly_summaries = await self._get_weekly_summaries(user_id)
        
        return DataExportResponse(
            export_date=datetime.now(timezone.utc),
            user=_serialize_model(user),
            profile=_serialize_model(profile) if profile else None,
            student_profile=_serialize_model(student_profile) if student_profile else None,
            career_preferences=_serialize_model(career_preferences) if career_preferences else None,
            documents=_serialize_list(documents),
            expenses=_serialize_list(expenses),
            expense_categories=_serialize_list(expense_categories),
            budgets=_serialize_list(budgets),
            health_records=_serialize_list(health_records),
            family_members=_serialize_list(family_members),
            medicines=_serialize_list(medicines),
            vitals=_serialize_list(vitals),
            emergency_info=_serialize_model(emergency_info) if emergency_info else None,
            wardrobe_items=_serialize_list(wardrobe_items),
            outfits=_serialize_list(outfits),
            outfit_plans=_serialize_list(outfit_plans),
            packing_lists=_serialize_list(packing_lists),
            skills=_serialize_list(skills),
            courses=_serialize_list(courses),
            roadmaps=_serialize_list(roadmaps),
            job_applications=_serialize_list(job_applications),
            achievements=_serialize_list(achievements),
            resumes=_serialize_list(resumes),
            exam_bookmarks=_serialize_list(exam_bookmarks),
            exam_applications=_serialize_list(exam_applications),
            notifications=_serialize_list(notifications),
            notification_preferences=_serialize_model(notification_preferences) if notification_preferences else None,
            life_scores=_serialize_list(life_scores),
            badges=_serialize_list(badges),
            weekly_summaries=_serialize_list(weekly_summaries),
        )
    
    async def request_account_deletion(
        self,
        user_id: UUID,
        password: Optional[str] = None,
    ) -> AccountDeletionResponse:
        """Request account deletion with 30-day grace period.
        
        Validates: Requirements 36.6
        
        Args:
            user_id: UUID of the user requesting deletion
            password: Password for verification (required for password-based accounts)
            
        Returns:
            AccountDeletionResponse with deletion schedule
        """
        user = await self._get_user(user_id)
        
        # Verify password for password-based accounts
        if user.password_hash:
            if not password:
                raise ValidationError(
                    message="Password required to confirm account deletion",
                    field_errors={"password": "Password is required"}
                )
            if not verify_password(password, user.password_hash):
                raise AuthenticationError(message="Invalid password")
        
        # Check if deletion is already pending
        if user.deletion_requested_at:
            raise ValidationError(
                message="Account deletion already requested",
                field_errors={"confirm": "Deletion is already scheduled"}
            )
        
        # Set deletion timestamps
        now = datetime.now(timezone.utc)
        deletion_scheduled = now + timedelta(days=DELETION_GRACE_PERIOD_DAYS)
        
        user.deletion_requested_at = now
        user.deletion_scheduled_at = deletion_scheduled
        
        await self.db.commit()
        
        logger.info(f"Account deletion requested for user {user_id}, scheduled for {deletion_scheduled}")
        
        return AccountDeletionResponse(
            message="Account deletion scheduled. Your data will be permanently deleted after 30 days.",
            deletion_requested_at=now,
            deletion_scheduled_at=deletion_scheduled,
            can_cancel_until=deletion_scheduled,
        )
    
    async def cancel_account_deletion(self, user_id: UUID) -> AccountDeletionCancelResponse:
        """Cancel a pending account deletion request.
        
        Validates: Requirements 36.6
        
        Args:
            user_id: UUID of the user cancelling deletion
            
        Returns:
            AccountDeletionCancelResponse confirming cancellation
        """
        user = await self._get_user(user_id)
        
        if not user.deletion_requested_at:
            raise ValidationError(
                message="No pending deletion request",
                field_errors={"confirm": "No deletion request to cancel"}
            )
        
        # Check if still within grace period
        now = datetime.now(timezone.utc)
        if user.deletion_scheduled_at and now >= user.deletion_scheduled_at:
            raise ValidationError(
                message="Deletion grace period has expired",
                field_errors={"confirm": "Cannot cancel after grace period"}
            )
        
        # Clear deletion timestamps
        user.deletion_requested_at = None
        user.deletion_scheduled_at = None
        
        await self.db.commit()
        
        logger.info(f"Account deletion cancelled for user {user_id}")
        
        return AccountDeletionCancelResponse(
            message="Account deletion cancelled successfully.",
            cancelled_at=now,
        )
    
    async def get_deletion_status(self, user_id: UUID) -> AccountDeletionStatusResponse:
        """Get the current account deletion status.
        
        Validates: Requirements 36.6
        
        Args:
            user_id: UUID of the user
            
        Returns:
            AccountDeletionStatusResponse with current status
        """
        user = await self._get_user(user_id)
        
        deletion_pending = user.deletion_requested_at is not None
        can_cancel = False
        
        if deletion_pending and user.deletion_scheduled_at:
            now = datetime.now(timezone.utc)
            can_cancel = now < user.deletion_scheduled_at
        
        return AccountDeletionStatusResponse(
            deletion_pending=deletion_pending,
            deletion_requested_at=user.deletion_requested_at,
            deletion_scheduled_at=user.deletion_scheduled_at,
            can_cancel=can_cancel,
        )
    
    async def permanently_delete_user(self, user_id: UUID) -> bool:
        """Permanently delete all user data.
        
        Validates: Requirements 36.6
        
        This method is called by the scheduled Celery task after the 30-day
        grace period has expired.
        
        Args:
            user_id: UUID of the user to delete
            
        Returns:
            True if deletion was successful
        """
        user = await self._get_user(user_id)
        
        # Verify deletion is scheduled and grace period has passed
        if not user.deletion_scheduled_at:
            logger.warning(f"Attempted to delete user {user_id} without scheduled deletion")
            return False
        
        now = datetime.now(timezone.utc)
        if now < user.deletion_scheduled_at:
            logger.warning(f"Attempted to delete user {user_id} before grace period expired")
            return False
        
        # Delete user (cascades to all related data due to foreign key constraints)
        await self.db.delete(user)
        await self.db.commit()
        
        logger.info(f"Permanently deleted user {user_id} and all associated data")
        
        return True
    
    # Helper methods for fetching user data
    
    async def _get_user(self, user_id: UUID) -> User:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError(detail="User not found")
        return user
    
    async def _get_profile(self, user_id: UUID) -> Optional[Profile]:
        """Get user profile."""
        stmt = select(Profile).where(Profile.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_student_profile(self, user_id: UUID) -> Optional[StudentProfile]:
        """Get student profile."""
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_career_preferences(self, user_id: UUID) -> Optional[CareerPreferences]:
        """Get career preferences."""
        stmt = select(CareerPreferences).where(CareerPreferences.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_documents(self, user_id: UUID) -> list[Document]:
        """Get all user documents."""
        stmt = select(Document).where(Document.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_expenses(self, user_id: UUID) -> list[Expense]:
        """Get all user expenses."""
        stmt = select(Expense).where(Expense.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_expense_categories(self, user_id: UUID) -> list[ExpenseCategory]:
        """Get user's custom expense categories."""
        stmt = select(ExpenseCategory).where(ExpenseCategory.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_budgets(self, user_id: UUID) -> list[Budget]:
        """Get all user budgets."""
        stmt = select(Budget).where(Budget.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_health_records(self, user_id: UUID) -> list[HealthRecord]:
        """Get all user health records."""
        stmt = select(HealthRecord).where(HealthRecord.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_family_members(self, user_id: UUID) -> list[FamilyMember]:
        """Get all family members."""
        stmt = select(FamilyMember).where(FamilyMember.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_medicines(self, user_id: UUID) -> list[Medicine]:
        """Get all user medicines."""
        stmt = select(Medicine).where(Medicine.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_vitals(self, user_id: UUID) -> list[Vital]:
        """Get all user vitals."""
        stmt = select(Vital).where(Vital.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_emergency_info(self, user_id: UUID) -> Optional[EmergencyInfo]:
        """Get emergency info."""
        stmt = select(EmergencyInfo).where(EmergencyInfo.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_wardrobe_items(self, user_id: UUID) -> list[WardrobeItem]:
        """Get all wardrobe items."""
        stmt = select(WardrobeItem).where(WardrobeItem.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_outfits(self, user_id: UUID) -> list[Outfit]:
        """Get all saved outfits."""
        stmt = select(Outfit).where(Outfit.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_outfit_plans(self, user_id: UUID) -> list[OutfitPlan]:
        """Get all outfit plans."""
        stmt = select(OutfitPlan).where(OutfitPlan.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_packing_lists(self, user_id: UUID) -> list[PackingList]:
        """Get all packing lists."""
        stmt = select(PackingList).where(PackingList.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_skills(self, user_id: UUID) -> list[Skill]:
        """Get all user skills."""
        stmt = select(Skill).where(Skill.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_courses(self, user_id: UUID) -> list[Course]:
        """Get all user courses."""
        stmt = select(Course).where(Course.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_roadmaps(self, user_id: UUID) -> list[CareerRoadmap]:
        """Get all career roadmaps."""
        stmt = select(CareerRoadmap).where(CareerRoadmap.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_job_applications(self, user_id: UUID) -> list[JobApplication]:
        """Get all job applications."""
        stmt = select(JobApplication).where(JobApplication.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_achievements(self, user_id: UUID) -> list[Achievement]:
        """Get all achievements."""
        stmt = select(Achievement).where(Achievement.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_resumes(self, user_id: UUID) -> list[Resume]:
        """Get all resumes."""
        stmt = select(Resume).where(Resume.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_exam_bookmarks(self, user_id: UUID) -> list[ExamBookmark]:
        """Get all exam bookmarks."""
        stmt = select(ExamBookmark).where(ExamBookmark.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_exam_applications(self, user_id: UUID) -> list[ExamApplication]:
        """Get all exam applications."""
        stmt = select(ExamApplication).where(ExamApplication.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_notifications(self, user_id: UUID) -> list[Notification]:
        """Get all notifications."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_notification_preferences(self, user_id: UUID) -> Optional[NotificationPreferences]:
        """Get notification preferences."""
        stmt = select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_life_scores(self, user_id: UUID) -> list[LifeScore]:
        """Get all life scores."""
        stmt = select(LifeScore).where(LifeScore.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_badges(self, user_id: UUID) -> list[Badge]:
        """Get all badges."""
        stmt = select(Badge).where(Badge.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_weekly_summaries(self, user_id: UUID) -> list[WeeklySummary]:
        """Get all weekly summaries."""
        stmt = select(WeeklySummary).where(WeeklySummary.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
