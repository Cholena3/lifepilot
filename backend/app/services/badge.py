"""Badge service for gamification achievements and milestones.

Requirement 33.3: Notify users on significant score changes
Requirement 33.5: Award badges for achievements and milestones
Requirement 33.6: Show breakdown of score by module
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import Badge, BadgeType, BADGE_METADATA
from app.models.course import Course
from app.models.document import Document
from app.models.exam import ExamBookmark, ExamApplication
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.health import HealthRecord
from app.models.job_application import JobApplication
from app.models.life_score import LifeScore
from app.models.medicine import Medicine, MedicineDose
from app.models.notification import NotificationChannel
from app.models.skill import Skill
from app.models.vital import Vital
from app.models.wardrobe import WardrobeItem, OutfitPlan
from app.repositories.badge import BadgeRepository
from app.schemas.badge import (
    AllBadgesResponse,
    BadgeAwardResponse,
    BadgeListResponse,
    BadgeResponse,
    BadgeTypeInfo,
)

logger = logging.getLogger(__name__)

# Threshold for significant score change notification
SIGNIFICANT_SCORE_CHANGE_THRESHOLD = 10


class BadgeService:
    """Service for badge awarding and management.
    
    Requirement 33.3, 33.5, 33.6
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BadgeRepository(session)

    async def award_badge(
        self,
        user_id: uuid.UUID,
        badge_type: BadgeType,
    ) -> BadgeAwardResponse:
        """Award a badge to a user.
        
        Requirement 33.5: Award badges for achievements and milestones
        
        Args:
            user_id: User's UUID
            badge_type: Type of badge to award
            
        Returns:
            BadgeAwardResponse with badge details and status
        """
        badge, already_earned = await self.repo.award_badge(user_id, badge_type)
        
        if already_earned:
            return BadgeAwardResponse(
                badge=BadgeResponse.model_validate(badge),
                already_earned=True,
                message=f"Badge '{badge.name}' was already earned",
            )
        
        logger.info(f"Awarded badge '{badge_type.value}' to user {user_id}")
        
        return BadgeAwardResponse(
            badge=BadgeResponse.model_validate(badge),
            already_earned=False,
            message=f"Congratulations! You earned the '{badge.name}' badge!",
        )

    async def get_user_badges(
        self,
        user_id: uuid.UUID,
    ) -> BadgeListResponse:
        """Get all badges for a user.
        
        Requirement 33.5: Award badges for achievements and milestones
        
        Args:
            user_id: User's UUID
            
        Returns:
            BadgeListResponse with list of badges
        """
        badges = await self.repo.get_user_badges(user_id)
        return BadgeListResponse(
            badges=[BadgeResponse.model_validate(b) for b in badges],
            total_count=len(badges),
        )

    async def get_all_badges_with_status(
        self,
        user_id: uuid.UUID,
    ) -> AllBadgesResponse:
        """Get all available badges with earned status for a user.
        
        Requirement 33.5: Award badges for achievements and milestones
        
        Args:
            user_id: User's UUID
            
        Returns:
            AllBadgesResponse with all badges and their status
        """
        # Get user's earned badges
        earned_badges = await self.repo.get_user_badges(user_id)
        earned_map = {b.badge_type: b for b in earned_badges}
        
        # Build response with all badge types
        badges_info = []
        for badge_type in BadgeType:
            metadata = BADGE_METADATA.get(badge_type, {
                "name": badge_type.value.replace("_", " ").title(),
                "description": f"Earn the {badge_type.value} badge",
            })
            
            earned_badge = earned_map.get(badge_type.value)
            badges_info.append(BadgeTypeInfo(
                badge_type=badge_type.value,
                name=metadata["name"],
                description=metadata["description"],
                earned=earned_badge is not None,
                earned_at=earned_badge.earned_at if earned_badge else None,
            ))
        
        return AllBadgesResponse(
            badges=badges_info,
            earned_count=len(earned_badges),
            total_count=len(BadgeType),
        )

    async def check_and_award_milestone_badges(
        self,
        user_id: uuid.UUID,
    ) -> list[BadgeAwardResponse]:
        """Check and award all applicable milestone badges for a user.
        
        Requirement 33.5: Award badges for achievements and milestones
        
        This method checks various milestones across all modules and awards
        badges that the user has earned but not yet received.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of BadgeAwardResponse for newly awarded badges
        """
        awarded = []
        
        # Check document milestones
        doc_badges = await self._check_document_milestones(user_id)
        awarded.extend(doc_badges)
        
        # Check expense/budget milestones
        money_badges = await self._check_money_milestones(user_id)
        awarded.extend(money_badges)
        
        # Check health milestones
        health_badges = await self._check_health_milestones(user_id)
        awarded.extend(health_badges)
        
        # Check wardrobe milestones
        wardrobe_badges = await self._check_wardrobe_milestones(user_id)
        awarded.extend(wardrobe_badges)
        
        # Check career milestones
        career_badges = await self._check_career_milestones(user_id)
        awarded.extend(career_badges)
        
        # Check exam milestones
        exam_badges = await self._check_exam_milestones(user_id)
        awarded.extend(exam_badges)
        
        return awarded

    async def _check_document_milestones(
        self,
        user_id: uuid.UUID,
    ) -> list[BadgeAwardResponse]:
        """Check and award document-related badges."""
        awarded = []
        
        # Count documents
        query = select(func.count(Document.id)).where(Document.user_id == user_id)
        result = await self.session.execute(query)
        doc_count = result.scalar() or 0
        
        if doc_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_DOCUMENT)
            if not response.already_earned:
                awarded.append(response)
        
        if doc_count >= 10:
            response = await self.award_badge(user_id, BadgeType.DOCUMENT_ORGANIZER)
            if not response.already_earned:
                awarded.append(response)
        
        if doc_count >= 50:
            response = await self.award_badge(user_id, BadgeType.DOCUMENT_MASTER)
            if not response.already_earned:
                awarded.append(response)
        
        return awarded

    async def _check_money_milestones(
        self,
        user_id: uuid.UUID,
    ) -> list[BadgeAwardResponse]:
        """Check and award money-related badges."""
        awarded = []
        
        # Count expenses
        expense_query = select(func.count(Expense.id)).where(Expense.user_id == user_id)
        result = await self.session.execute(expense_query)
        expense_count = result.scalar() or 0
        
        if expense_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_EXPENSE)
            if not response.already_earned:
                awarded.append(response)
        
        if expense_count >= 30:
            response = await self.award_badge(user_id, BadgeType.EXPENSE_TRACKER)
            if not response.already_earned:
                awarded.append(response)
        
        # Count budgets
        budget_query = select(func.count(Budget.id)).where(Budget.user_id == user_id)
        result = await self.session.execute(budget_query)
        budget_count = result.scalar() or 0
        
        if budget_count >= 1:
            response = await self.award_badge(user_id, BadgeType.BUDGET_CREATOR)
            if not response.already_earned:
                awarded.append(response)
        
        return awarded

    async def _check_health_milestones(
        self,
        user_id: uuid.UUID,
    ) -> list[BadgeAwardResponse]:
        """Check and award health-related badges."""
        awarded = []
        
        # Count health records
        health_query = select(func.count(HealthRecord.id)).where(
            HealthRecord.user_id == user_id
        )
        result = await self.session.execute(health_query)
        health_count = result.scalar() or 0
        
        if health_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_HEALTH_RECORD)
            if not response.already_earned:
                awarded.append(response)
        
        # Count vitals
        vital_query = select(func.count(Vital.id)).where(Vital.user_id == user_id)
        result = await self.session.execute(vital_query)
        vital_count = result.scalar() or 0
        
        if vital_count >= 30:
            response = await self.award_badge(user_id, BadgeType.VITAL_TRACKER)
            if not response.already_earned:
                awarded.append(response)
        
        return awarded

    async def _check_wardrobe_milestones(
        self,
        user_id: uuid.UUID,
    ) -> list[BadgeAwardResponse]:
        """Check and award wardrobe-related badges."""
        awarded = []
        
        # Count wardrobe items
        item_query = select(func.count(WardrobeItem.id)).where(
            WardrobeItem.user_id == user_id
        )
        result = await self.session.execute(item_query)
        item_count = result.scalar() or 0
        
        if item_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_WARDROBE_ITEM)
            if not response.already_earned:
                awarded.append(response)
        
        if item_count >= 20:
            response = await self.award_badge(user_id, BadgeType.FASHION_ENTHUSIAST)
            if not response.already_earned:
                awarded.append(response)
        
        # Count outfit plans
        plan_query = select(func.count(OutfitPlan.id)).where(
            OutfitPlan.user_id == user_id
        )
        result = await self.session.execute(plan_query)
        plan_count = result.scalar() or 0
        
        if plan_count >= 5:
            response = await self.award_badge(user_id, BadgeType.OUTFIT_PLANNER)
            if not response.already_earned:
                awarded.append(response)
        
        return awarded

    async def _check_career_milestones(
        self,
        user_id: uuid.UUID,
    ) -> list[BadgeAwardResponse]:
        """Check and award career-related badges."""
        awarded = []
        
        # Count skills
        skill_query = select(func.count(Skill.id)).where(Skill.user_id == user_id)
        result = await self.session.execute(skill_query)
        skill_count = result.scalar() or 0
        
        if skill_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_SKILL)
            if not response.already_earned:
                awarded.append(response)
        
        if skill_count >= 10:
            response = await self.award_badge(user_id, BadgeType.SKILL_BUILDER)
            if not response.already_earned:
                awarded.append(response)
        
        # Count courses
        course_query = select(func.count(Course.id)).where(Course.user_id == user_id)
        result = await self.session.execute(course_query)
        course_count = result.scalar() or 0
        
        if course_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_COURSE)
            if not response.already_earned:
                awarded.append(response)
        
        # Count completed courses
        completed_query = select(func.count(Course.id)).where(
            and_(
                Course.user_id == user_id,
                Course.is_completed == True,
            )
        )
        result = await self.session.execute(completed_query)
        completed_count = result.scalar() or 0
        
        if completed_count >= 1:
            response = await self.award_badge(user_id, BadgeType.COURSE_COMPLETER)
            if not response.already_earned:
                awarded.append(response)
        
        if completed_count >= 5:
            response = await self.award_badge(user_id, BadgeType.LIFELONG_LEARNER)
            if not response.already_earned:
                awarded.append(response)
        
        # Count job applications
        app_query = select(func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id
        )
        result = await self.session.execute(app_query)
        app_count = result.scalar() or 0
        
        if app_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_APPLICATION)
            if not response.already_earned:
                awarded.append(response)
        
        if app_count >= 10:
            response = await self.award_badge(user_id, BadgeType.JOB_HUNTER)
            if not response.already_earned:
                awarded.append(response)
        
        return awarded

    async def _check_exam_milestones(
        self,
        user_id: uuid.UUID,
    ) -> list[BadgeAwardResponse]:
        """Check and award exam-related badges."""
        awarded = []
        
        # Count exam bookmarks
        bookmark_query = select(func.count(ExamBookmark.id)).where(
            ExamBookmark.user_id == user_id
        )
        result = await self.session.execute(bookmark_query)
        bookmark_count = result.scalar() or 0
        
        if bookmark_count >= 1:
            response = await self.award_badge(user_id, BadgeType.FIRST_EXAM_BOOKMARK)
            if not response.already_earned:
                awarded.append(response)
        
        if bookmark_count >= 10:
            response = await self.award_badge(user_id, BadgeType.EXAM_EXPLORER)
            if not response.already_earned:
                awarded.append(response)
        
        # Count exam applications
        app_query = select(func.count(ExamApplication.id)).where(
            ExamApplication.user_id == user_id
        )
        result = await self.session.execute(app_query)
        app_count = result.scalar() or 0
        
        if app_count >= 1:
            response = await self.award_badge(user_id, BadgeType.EXAM_APPLICANT)
            if not response.already_earned:
                awarded.append(response)
        
        return awarded

    async def check_score_milestones(
        self,
        user_id: uuid.UUID,
        current_score: int,
        previous_score: Optional[int] = None,
    ) -> list[BadgeAwardResponse]:
        """Check and award Life Score milestone badges.
        
        Requirement 33.5: Award badges for achievements and milestones
        
        Args:
            user_id: User's UUID
            current_score: Current Life Score
            previous_score: Previous Life Score (for change detection)
            
        Returns:
            List of BadgeAwardResponse for newly awarded badges
        """
        awarded = []
        
        # Check score level badges
        if current_score >= 50:
            response = await self.award_badge(user_id, BadgeType.SCORE_ACHIEVER)
            if not response.already_earned:
                awarded.append(response)
        
        if current_score >= 80:
            response = await self.award_badge(user_id, BadgeType.SCORE_MASTER)
            if not response.already_earned:
                awarded.append(response)
        
        # Check score increase badge
        if previous_score is not None:
            score_increase = current_score - previous_score
            if score_increase >= 10:
                response = await self.award_badge(user_id, BadgeType.SCORE_RISING)
                if not response.already_earned:
                    awarded.append(response)
        
        return awarded

    async def check_significant_score_change(
        self,
        user_id: uuid.UUID,
        current_score: int,
        previous_score: int,
    ) -> bool:
        """Check if score change is significant enough for notification.
        
        Requirement 33.3: Notify users on significant score changes
        
        Args:
            user_id: User's UUID
            current_score: Current Life Score
            previous_score: Previous Life Score
            
        Returns:
            True if change is significant, False otherwise
        """
        change = abs(current_score - previous_score)
        return change >= SIGNIFICANT_SCORE_CHANGE_THRESHOLD

    async def get_score_change_notification_message(
        self,
        current_score: int,
        previous_score: int,
    ) -> tuple[str, str]:
        """Generate notification message for significant score change.
        
        Requirement 33.3: Notify users on significant score changes
        
        Args:
            current_score: Current Life Score
            previous_score: Previous Life Score
            
        Returns:
            Tuple of (title, body) for notification
        """
        change = current_score - previous_score
        
        if change > 0:
            title = "🎉 Life Score Increased!"
            body = (
                f"Great job! Your Life Score increased from {previous_score} to "
                f"{current_score} (+{change} points). Keep up the good work!"
            )
        else:
            title = "📉 Life Score Update"
            body = (
                f"Your Life Score changed from {previous_score} to {current_score} "
                f"({change} points). Stay active to boost your score!"
            )
        
        return title, body
