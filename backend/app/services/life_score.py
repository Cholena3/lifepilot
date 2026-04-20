"""Life Score service for gamification and engagement tracking.

Requirement 33: Life Score Gamification
- Calculate Life Score based on activity across all modules
- Weight activities by importance and recency
- Notify users on significant score changes
- Display Life Score trends over time
- Show breakdown of score by module
- Award badges for achievements and milestones
"""

import logging
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement
from app.models.course import Course
from app.models.document import Document
from app.models.expense import Expense
from app.models.health import HealthRecord
from app.models.job_application import JobApplication
from app.models.life_score import LifeScore, ModuleType
from app.models.medicine import Medicine, MedicineDose
from app.models.notification import NotificationChannel
from app.models.skill import Skill
from app.models.vital import Vital
from app.models.wardrobe import WardrobeItem, WearLog
from app.models.exam import ExamBookmark, ExamApplication
from app.repositories.life_score import LifeScoreRepository
from app.schemas.life_score import (
    LifeScoreCalculationResult,
    LifeScoreComparisonResponse,
    LifeScoreDetailResponse,
    LifeScoreResponse,
    LifeScoreTrendPoint,
    LifeScoreTrendResponse,
    ModuleScoreBreakdown,
    PaginatedLifeScoreResponse,
)

logger = logging.getLogger(__name__)

# Threshold for significant score change notification
SIGNIFICANT_SCORE_CHANGE_THRESHOLD = 10

# Activity weights by importance (higher = more important)
# Requirement 33.2: Weight activities by importance
ACTIVITY_WEIGHTS = {
    # Documents module
    "document_upload": 3,
    "document_share": 2,
    
    # Money module
    "expense_logged": 2,
    "budget_created": 3,
    
    # Health module
    "health_record_added": 3,
    "medicine_dose_taken": 2,
    "vital_logged": 2,
    
    # Wardrobe module
    "wardrobe_item_added": 2,
    "outfit_worn": 1,
    
    # Career module
    "skill_added": 3,
    "skill_updated": 2,
    "course_progress": 3,
    "course_completed": 5,
    "job_application": 4,
    "achievement_added": 4,
    
    # Exams module
    "exam_bookmarked": 2,
    "exam_applied": 4,
}

# Maximum score per module (out of 100 total)
MODULE_MAX_SCORES = {
    ModuleType.DOCUMENTS: 15,
    ModuleType.MONEY: 20,
    ModuleType.HEALTH: 20,
    ModuleType.WARDROBE: 10,
    ModuleType.CAREER: 25,
    ModuleType.EXAMS: 10,
}

# Recency decay factor (activities older than this many days get reduced weight)
RECENCY_DECAY_DAYS = 30
RECENCY_DECAY_FACTOR = 0.5  # Activities older than RECENCY_DECAY_DAYS get 50% weight


class LifeScoreService:
    """Service for Life Score calculation and management.
    
    Requirement 33.1, 33.2, 33.4, 33.6
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LifeScoreRepository(session)

    def _calculate_recency_weight(self, activity_date: date, reference_date: date) -> float:
        """Calculate recency weight for an activity.
        
        Requirement 33.2: Weight activities by recency
        
        Activities within RECENCY_DECAY_DAYS get full weight.
        Older activities get reduced weight based on RECENCY_DECAY_FACTOR.
        """
        days_ago = (reference_date - activity_date).days
        if days_ago <= 0:
            return 1.0
        if days_ago <= RECENCY_DECAY_DAYS:
            return 1.0
        # Apply decay for older activities
        decay_periods = (days_ago - RECENCY_DECAY_DAYS) / RECENCY_DECAY_DAYS
        return max(0.1, RECENCY_DECAY_FACTOR ** decay_periods)

    async def _count_document_activities(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Count document-related activities and calculate weighted score."""
        # Count documents uploaded in period
        doc_query = select(func.count(Document.id)).where(
            and_(
                Document.user_id == user_id,
                func.date(Document.created_at) >= start_date,
                func.date(Document.created_at) <= end_date,
            )
        )
        result = await self.session.execute(doc_query)
        doc_count = result.scalar() or 0
        
        activity_count = doc_count
        raw_score = doc_count * ACTIVITY_WEIGHTS["document_upload"]
        
        return activity_count, raw_score

    async def _count_money_activities(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Count money-related activities and calculate weighted score."""
        # Count expenses logged in period
        expense_query = select(func.count(Expense.id)).where(
            and_(
                Expense.user_id == user_id,
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date,
            )
        )
        result = await self.session.execute(expense_query)
        expense_count = result.scalar() or 0
        
        activity_count = expense_count
        raw_score = expense_count * ACTIVITY_WEIGHTS["expense_logged"]
        
        return activity_count, raw_score

    async def _count_health_activities(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Count health-related activities and calculate weighted score."""
        activity_count = 0
        raw_score = 0
        
        # Count health records added
        health_query = select(func.count(HealthRecord.id)).where(
            and_(
                HealthRecord.user_id == user_id,
                func.date(HealthRecord.created_at) >= start_date,
                func.date(HealthRecord.created_at) <= end_date,
            )
        )
        result = await self.session.execute(health_query)
        health_count = result.scalar() or 0
        activity_count += health_count
        raw_score += health_count * ACTIVITY_WEIGHTS["health_record_added"]
        
        # Count medicine doses taken
        dose_query = select(func.count(MedicineDose.id)).where(
            and_(
                MedicineDose.status == "taken",
                func.date(MedicineDose.taken_time) >= start_date,
                func.date(MedicineDose.taken_time) <= end_date,
            )
        ).join(Medicine, MedicineDose.medicine_id == Medicine.id).where(
            Medicine.user_id == user_id
        )
        result = await self.session.execute(dose_query)
        dose_count = result.scalar() or 0
        activity_count += dose_count
        raw_score += dose_count * ACTIVITY_WEIGHTS["medicine_dose_taken"]
        
        # Count vitals logged
        vital_query = select(func.count(Vital.id)).where(
            and_(
                Vital.user_id == user_id,
                func.date(Vital.recorded_at) >= start_date,
                func.date(Vital.recorded_at) <= end_date,
            )
        )
        result = await self.session.execute(vital_query)
        vital_count = result.scalar() or 0
        activity_count += vital_count
        raw_score += vital_count * ACTIVITY_WEIGHTS["vital_logged"]
        
        return activity_count, raw_score

    async def _count_wardrobe_activities(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Count wardrobe-related activities and calculate weighted score."""
        activity_count = 0
        raw_score = 0
        
        # Count wardrobe items added
        item_query = select(func.count(WardrobeItem.id)).where(
            and_(
                WardrobeItem.user_id == user_id,
                func.date(WardrobeItem.created_at) >= start_date,
                func.date(WardrobeItem.created_at) <= end_date,
            )
        )
        result = await self.session.execute(item_query)
        item_count = result.scalar() or 0
        activity_count += item_count
        raw_score += item_count * ACTIVITY_WEIGHTS["wardrobe_item_added"]
        
        # Count wear logs
        wear_query = select(func.count(WearLog.id)).where(
            and_(
                WearLog.worn_date >= start_date,
                WearLog.worn_date <= end_date,
            )
        ).join(WardrobeItem, WearLog.item_id == WardrobeItem.id).where(
            WardrobeItem.user_id == user_id
        )
        result = await self.session.execute(wear_query)
        wear_count = result.scalar() or 0
        activity_count += wear_count
        raw_score += wear_count * ACTIVITY_WEIGHTS["outfit_worn"]
        
        return activity_count, raw_score

    async def _count_career_activities(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Count career-related activities and calculate weighted score."""
        activity_count = 0
        raw_score = 0
        
        # Count skills added/updated
        skill_query = select(func.count(Skill.id)).where(
            and_(
                Skill.user_id == user_id,
                func.date(Skill.created_at) >= start_date,
                func.date(Skill.created_at) <= end_date,
            )
        )
        result = await self.session.execute(skill_query)
        skill_count = result.scalar() or 0
        activity_count += skill_count
        raw_score += skill_count * ACTIVITY_WEIGHTS["skill_added"]
        
        # Count course progress (courses with activity in period)
        course_query = select(func.count(Course.id)).where(
            and_(
                Course.user_id == user_id,
                func.date(Course.last_activity) >= start_date,
                func.date(Course.last_activity) <= end_date,
            )
        )
        result = await self.session.execute(course_query)
        course_count = result.scalar() or 0
        activity_count += course_count
        raw_score += course_count * ACTIVITY_WEIGHTS["course_progress"]
        
        # Count completed courses
        completed_query = select(func.count(Course.id)).where(
            and_(
                Course.user_id == user_id,
                Course.is_completed == True,
                func.date(Course.updated_at) >= start_date,
                func.date(Course.updated_at) <= end_date,
            )
        )
        result = await self.session.execute(completed_query)
        completed_count = result.scalar() or 0
        raw_score += completed_count * ACTIVITY_WEIGHTS["course_completed"]
        
        # Count job applications
        app_query = select(func.count(JobApplication.id)).where(
            and_(
                JobApplication.user_id == user_id,
                JobApplication.applied_date >= start_date,
                JobApplication.applied_date <= end_date,
            )
        )
        result = await self.session.execute(app_query)
        app_count = result.scalar() or 0
        activity_count += app_count
        raw_score += app_count * ACTIVITY_WEIGHTS["job_application"]
        
        # Count achievements
        achievement_query = select(func.count(Achievement.id)).where(
            and_(
                Achievement.user_id == user_id,
                func.date(Achievement.created_at) >= start_date,
                func.date(Achievement.created_at) <= end_date,
            )
        )
        result = await self.session.execute(achievement_query)
        achievement_count = result.scalar() or 0
        activity_count += achievement_count
        raw_score += achievement_count * ACTIVITY_WEIGHTS["achievement_added"]
        
        return activity_count, raw_score

    async def _count_exam_activities(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Count exam-related activities and calculate weighted score."""
        activity_count = 0
        raw_score = 0
        
        # Count exam bookmarks
        bookmark_query = select(func.count(ExamBookmark.id)).where(
            and_(
                ExamBookmark.user_id == user_id,
                func.date(ExamBookmark.created_at) >= start_date,
                func.date(ExamBookmark.created_at) <= end_date,
            )
        )
        result = await self.session.execute(bookmark_query)
        bookmark_count = result.scalar() or 0
        activity_count += bookmark_count
        raw_score += bookmark_count * ACTIVITY_WEIGHTS["exam_bookmarked"]
        
        # Count exam applications
        app_query = select(func.count(ExamApplication.id)).where(
            and_(
                ExamApplication.user_id == user_id,
                ExamApplication.applied_date >= start_date,
                ExamApplication.applied_date <= end_date,
            )
        )
        result = await self.session.execute(app_query)
        app_count = result.scalar() or 0
        activity_count += app_count
        raw_score += app_count * ACTIVITY_WEIGHTS["exam_applied"]
        
        return activity_count, raw_score

    def _normalize_module_score(
        self,
        raw_score: int,
        module: ModuleType,
        max_raw_score: int = 50,
    ) -> int:
        """Normalize raw score to module's maximum score.
        
        Uses a logarithmic scale to prevent runaway scores from high activity.
        """
        max_module_score = MODULE_MAX_SCORES[module]
        if raw_score <= 0:
            return 0
        # Use log scale: score = max * log(1 + raw) / log(1 + max_raw)
        normalized = max_module_score * math.log(1 + raw_score) / math.log(1 + max_raw_score)
        return min(max_module_score, round(normalized))

    async def calculate_life_score(
        self,
        user_id: uuid.UUID,
        score_date: Optional[date] = None,
        lookback_days: int = 30,
    ) -> LifeScoreCalculationResult:
        """Calculate Life Score for a user.
        
        Requirement 33.1: Calculate Life Score based on activity across all modules
        Requirement 33.2: Weight activities by importance and recency
        
        Args:
            user_id: User's UUID
            score_date: Date to calculate score for (defaults to today)
            lookback_days: Number of days to look back for activities
            
        Returns:
            LifeScoreCalculationResult with total score and breakdown
        """
        if score_date is None:
            score_date = date.today()
        
        start_date = score_date - timedelta(days=lookback_days)
        end_date = score_date
        
        module_scores: dict[str, int] = {}
        module_activities: dict[str, int] = {}
        total_activity_count = 0
        
        # Calculate score for each module
        # Documents
        doc_activities, doc_raw = await self._count_document_activities(
            user_id, start_date, end_date
        )
        module_scores[ModuleType.DOCUMENTS.value] = self._normalize_module_score(
            doc_raw, ModuleType.DOCUMENTS
        )
        module_activities[ModuleType.DOCUMENTS.value] = doc_activities
        total_activity_count += doc_activities
        
        # Money
        money_activities, money_raw = await self._count_money_activities(
            user_id, start_date, end_date
        )
        module_scores[ModuleType.MONEY.value] = self._normalize_module_score(
            money_raw, ModuleType.MONEY
        )
        module_activities[ModuleType.MONEY.value] = money_activities
        total_activity_count += money_activities
        
        # Health
        health_activities, health_raw = await self._count_health_activities(
            user_id, start_date, end_date
        )
        module_scores[ModuleType.HEALTH.value] = self._normalize_module_score(
            health_raw, ModuleType.HEALTH
        )
        module_activities[ModuleType.HEALTH.value] = health_activities
        total_activity_count += health_activities
        
        # Wardrobe
        wardrobe_activities, wardrobe_raw = await self._count_wardrobe_activities(
            user_id, start_date, end_date
        )
        module_scores[ModuleType.WARDROBE.value] = self._normalize_module_score(
            wardrobe_raw, ModuleType.WARDROBE
        )
        module_activities[ModuleType.WARDROBE.value] = wardrobe_activities
        total_activity_count += wardrobe_activities
        
        # Career
        career_activities, career_raw = await self._count_career_activities(
            user_id, start_date, end_date
        )
        module_scores[ModuleType.CAREER.value] = self._normalize_module_score(
            career_raw, ModuleType.CAREER
        )
        module_activities[ModuleType.CAREER.value] = career_activities
        total_activity_count += career_activities
        
        # Exams
        exam_activities, exam_raw = await self._count_exam_activities(
            user_id, start_date, end_date
        )
        module_scores[ModuleType.EXAMS.value] = self._normalize_module_score(
            exam_raw, ModuleType.EXAMS
        )
        module_activities[ModuleType.EXAMS.value] = exam_activities
        total_activity_count += exam_activities
        
        # Calculate total score (sum of module scores, max 100)
        total_score = min(100, sum(module_scores.values()))
        
        # Build breakdown
        breakdown = []
        for module in ModuleType:
            score = module_scores.get(module.value, 0)
            activities = module_activities.get(module.value, 0)
            percentage = Decimal(str(score / total_score * 100)) if total_score > 0 else Decimal("0")
            breakdown.append(ModuleScoreBreakdown(
                module=module,
                score=score,
                activity_count=activities,
                percentage=round(percentage, 2),
            ))
        
        return LifeScoreCalculationResult(
            total_score=total_score,
            module_scores=module_scores,
            activity_count=total_activity_count,
            breakdown=breakdown,
        )

    async def calculate_and_store_score(
        self,
        user_id: uuid.UUID,
        score_date: Optional[date] = None,
    ) -> LifeScore:
        """Calculate and store Life Score for a user.
        
        Requirement 33.1, 33.4
        
        Args:
            user_id: User's UUID
            score_date: Date to calculate score for (defaults to today)
            
        Returns:
            Stored LifeScore model instance
        """
        if score_date is None:
            score_date = date.today()
        
        result = await self.calculate_life_score(user_id, score_date)
        
        life_score = await self.repo.create_or_update_score(
            user_id=user_id,
            score_date=score_date,
            total_score=result.total_score,
            module_scores=result.module_scores,
            activity_count=result.activity_count,
        )
        
        logger.info(
            f"Calculated Life Score for user {user_id}: {result.total_score} "
            f"({result.activity_count} activities)"
        )
        
        return life_score

    async def get_current_score(
        self,
        user_id: uuid.UUID,
    ) -> Optional[LifeScoreDetailResponse]:
        """Get current Life Score with breakdown.
        
        Requirement 33.1, 33.6
        """
        # Calculate fresh score for today
        result = await self.calculate_life_score(user_id)
        
        # Store it
        life_score = await self.repo.create_or_update_score(
            user_id=user_id,
            score_date=date.today(),
            total_score=result.total_score,
            module_scores=result.module_scores,
            activity_count=result.activity_count,
        )
        
        return LifeScoreDetailResponse(
            id=life_score.id,
            user_id=life_score.user_id,
            score_date=life_score.score_date,
            total_score=life_score.total_score,
            activity_count=life_score.activity_count,
            breakdown=result.breakdown,
            created_at=life_score.created_at,
            updated_at=life_score.updated_at,
        )

    async def get_score_trends(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> LifeScoreTrendResponse:
        """Get Life Score trends over time.
        
        Requirement 33.4: Display Life Score trends over time
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        scores = await self.repo.get_scores_in_range(user_id, start_date, end_date)
        
        # Build data points
        data_points = [
            LifeScoreTrendPoint(
                score_date=s.score_date,
                total_score=s.total_score,
                activity_count=s.activity_count,
            )
            for s in scores
        ]
        
        # Calculate metrics
        if scores:
            current_score = scores[-1].total_score
            first_score = scores[0].total_score
            score_change = current_score - first_score
            avg_score = sum(s.total_score for s in scores) / len(scores)
            
            # Determine trend direction
            if score_change > 5:
                trend_direction = "up"
            elif score_change < -5:
                trend_direction = "down"
            else:
                trend_direction = "stable"
        else:
            current_score = 0
            score_change = 0
            avg_score = 0.0
            trend_direction = "stable"
        
        return LifeScoreTrendResponse(
            start_date=start_date,
            end_date=end_date,
            current_score=current_score,
            average_score=Decimal(str(round(avg_score, 2))),
            trend_direction=trend_direction,
            score_change=score_change,
            data_points=data_points,
        )

    async def get_score_history(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 30,
    ) -> PaginatedLifeScoreResponse:
        """Get paginated Life Score history."""
        scores, total = await self.repo.get_scores_paginated(user_id, page, page_size)
        
        items = [LifeScoreResponse.model_validate(s) for s in scores]
        return PaginatedLifeScoreResponse.create(items, total, page, page_size)

    async def compare_scores(
        self,
        user_id: uuid.UUID,
        current_date: Optional[date] = None,
        days_ago: int = 7,
    ) -> LifeScoreComparisonResponse:
        """Compare current score with a previous score.
        
        Requirement 33.4
        """
        if current_date is None:
            current_date = date.today()
        previous_date = current_date - timedelta(days=days_ago)
        
        # Get or calculate current score
        current = await self.repo.get_score_by_date(user_id, current_date)
        if not current:
            await self.calculate_and_store_score(user_id, current_date)
            current = await self.repo.get_score_by_date(user_id, current_date)
        
        # Get previous score
        previous = await self.repo.get_score_by_date(user_id, previous_date)
        
        current_score = current.total_score if current else 0
        previous_score = previous.total_score if previous else 0
        score_change = current_score - previous_score
        
        change_percentage = None
        if previous_score > 0:
            change_percentage = Decimal(str(round(score_change / previous_score * 100, 2)))
        
        return LifeScoreComparisonResponse(
            current_score=current_score,
            previous_score=previous_score,
            score_change=score_change,
            change_percentage=change_percentage,
            current_date=current_date,
            previous_date=previous_date,
        )

    async def calculate_and_store_score_with_notifications(
        self,
        user_id: uuid.UUID,
        score_date: Optional[date] = None,
    ) -> tuple[LifeScore, list, bool]:
        """Calculate, store Life Score, award badges, and send notifications.
        
        Requirement 33.3: Notify users on significant score changes
        Requirement 33.5: Award badges for achievements and milestones
        
        Args:
            user_id: User's UUID
            score_date: Date to calculate score for (defaults to today)
            
        Returns:
            Tuple of (LifeScore, awarded_badges, notification_sent)
        """
        from app.services.badge import BadgeService
        from app.services.notification import NotificationService
        
        if score_date is None:
            score_date = date.today()
        
        # Get previous score for comparison
        previous_score = await self.repo.get_latest_score(user_id)
        previous_score_value = previous_score.total_score if previous_score else 0
        
        # Calculate and store new score
        result = await self.calculate_life_score(user_id, score_date)
        life_score = await self.repo.create_or_update_score(
            user_id=user_id,
            score_date=score_date,
            total_score=result.total_score,
            module_scores=result.module_scores,
            activity_count=result.activity_count,
        )
        
        # Award badges for score milestones
        badge_service = BadgeService(self.session)
        awarded_badges = await badge_service.check_score_milestones(
            user_id,
            result.total_score,
            previous_score_value,
        )
        
        # Also check and award other milestone badges
        other_badges = await badge_service.check_and_award_milestone_badges(user_id)
        awarded_badges.extend(other_badges)
        
        # Check for significant score change and send notification
        notification_sent = False
        if previous_score is not None:
            if await badge_service.check_significant_score_change(
                user_id,
                result.total_score,
                previous_score_value,
            ):
                try:
                    notification_service = NotificationService(self.session)
                    title, body = await badge_service.get_score_change_notification_message(
                        result.total_score,
                        previous_score_value,
                    )
                    await notification_service.send_notification(
                        user_id=user_id,
                        title=title,
                        body=body,
                        channel=NotificationChannel.PUSH,
                    )
                    notification_sent = True
                    logger.info(
                        f"Sent score change notification to user {user_id}: "
                        f"{previous_score_value} -> {result.total_score}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to send score change notification: {e}")
        
        logger.info(
            f"Calculated Life Score for user {user_id}: {result.total_score} "
            f"({result.activity_count} activities), "
            f"awarded {len(awarded_badges)} badges"
        )
        
        return life_score, awarded_badges, notification_sent

    async def get_score_breakdown(
        self,
        user_id: uuid.UUID,
    ) -> LifeScoreDetailResponse:
        """Get Life Score breakdown by module.
        
        Requirement 33.6: Show breakdown of score by module
        
        Args:
            user_id: User's UUID
            
        Returns:
            LifeScoreDetailResponse with module breakdown
        """
        # Calculate fresh score
        result = await self.calculate_life_score(user_id)
        
        # Store it
        life_score = await self.repo.create_or_update_score(
            user_id=user_id,
            score_date=date.today(),
            total_score=result.total_score,
            module_scores=result.module_scores,
            activity_count=result.activity_count,
        )
        
        return LifeScoreDetailResponse(
            id=life_score.id,
            user_id=life_score.user_id,
            score_date=life_score.score_date,
            total_score=life_score.total_score,
            activity_count=life_score.activity_count,
            breakdown=result.breakdown,
            created_at=life_score.created_at,
            updated_at=life_score.updated_at,
        )
