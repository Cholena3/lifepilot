"""Weekly Summary service for generating and managing weekly activity summaries.

Requirement 34: Weekly Summary
- Generate summary of activities across all modules
- Include expenses total, documents added, health records logged, and career progress
- Compare metrics with previous week
- Send via user's preferred channel
- Store past summaries for viewing
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement
from app.models.course import Course
from app.models.document import Document
from app.models.exam import ExamBookmark, ExamApplication
from app.models.expense import Expense
from app.models.health import HealthRecord
from app.models.job_application import JobApplication
from app.models.life_score import LifeScore
from app.models.medicine import Medicine, MedicineDose
from app.models.notification import NotificationChannel
from app.models.skill import Skill
from app.models.vital import Vital
from app.models.wardrobe import WardrobeItem, WearLog
from app.models.weekly_summary import WeeklySummary
from app.repositories.weekly_summary import WeeklySummaryRepository
from app.schemas.weekly_summary import (
    WeeklySummaryComparisons,
    WeeklySummaryListResponse,
    WeeklySummaryMetrics,
    WeeklySummaryNotificationContent,
    WeeklySummaryResponse,
)

logger = logging.getLogger(__name__)


def get_week_boundaries(reference_date: date) -> tuple[date, date]:
    """Get the Monday and Sunday of the week containing the reference date.
    
    Args:
        reference_date: Any date within the desired week
        
    Returns:
        Tuple of (week_start (Monday), week_end (Sunday))
    """
    # Monday is weekday 0, Sunday is weekday 6
    days_since_monday = reference_date.weekday()
    week_start = reference_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_last_completed_week() -> tuple[date, date]:
    """Get the boundaries of the last completed week (previous Monday to Sunday).
    
    Returns:
        Tuple of (week_start, week_end) for the last completed week
    """
    today = date.today()
    # Get this week's Monday
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    # Last week's Monday is 7 days before this Monday
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday


class WeeklySummaryService:
    """Service for weekly summary generation and management.
    
    Validates: Requirements 34.1, 34.2, 34.3, 34.4, 34.5
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WeeklySummaryRepository(session)

    async def _count_expenses(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[Decimal, int]:
        """Count expenses and total amount for a period."""
        query = select(
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
            func.count(Expense.id).label("count"),
        ).where(
            and_(
                Expense.user_id == user_id,
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date,
            )
        )
        result = await self.session.execute(query)
        row = result.one()
        return Decimal(str(row.total)), row.count

    async def _count_documents(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count documents added in a period."""
        query = select(func.count(Document.id)).where(
            and_(
                Document.user_id == user_id,
                func.date(Document.created_at) >= start_date,
                func.date(Document.created_at) <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_health_records(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count health records logged in a period."""
        query = select(func.count(HealthRecord.id)).where(
            and_(
                HealthRecord.user_id == user_id,
                func.date(HealthRecord.created_at) >= start_date,
                func.date(HealthRecord.created_at) <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_medicine_doses(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count medicine doses taken in a period."""
        query = select(func.count(MedicineDose.id)).where(
            and_(
                MedicineDose.status == "taken",
                func.date(MedicineDose.taken_time) >= start_date,
                func.date(MedicineDose.taken_time) <= end_date,
            )
        ).join(Medicine, MedicineDose.medicine_id == Medicine.id).where(
            Medicine.user_id == user_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_vitals(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count vitals logged in a period."""
        query = select(func.count(Vital.id)).where(
            and_(
                Vital.user_id == user_id,
                func.date(Vital.recorded_at) >= start_date,
                func.date(Vital.recorded_at) <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_wardrobe_items(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count wardrobe items added in a period."""
        query = select(func.count(WardrobeItem.id)).where(
            and_(
                WardrobeItem.user_id == user_id,
                func.date(WardrobeItem.created_at) >= start_date,
                func.date(WardrobeItem.created_at) <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_outfits_worn(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count outfits worn in a period."""
        query = select(func.count(WearLog.id)).where(
            and_(
                WearLog.worn_date >= start_date,
                WearLog.worn_date <= end_date,
            )
        ).join(WardrobeItem, WearLog.item_id == WardrobeItem.id).where(
            WardrobeItem.user_id == user_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_skills_updated(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count skills added or updated in a period."""
        # Count skills created in period
        created_query = select(func.count(Skill.id)).where(
            and_(
                Skill.user_id == user_id,
                func.date(Skill.created_at) >= start_date,
                func.date(Skill.created_at) <= end_date,
            )
        )
        created_result = await self.session.execute(created_query)
        created_count = created_result.scalar() or 0
        
        # Count skills updated (but not created) in period
        updated_query = select(func.count(Skill.id)).where(
            and_(
                Skill.user_id == user_id,
                func.date(Skill.updated_at) >= start_date,
                func.date(Skill.updated_at) <= end_date,
                func.date(Skill.created_at) < start_date,  # Not created in this period
            )
        )
        updated_result = await self.session.execute(updated_query)
        updated_count = updated_result.scalar() or 0
        
        return created_count + updated_count

    async def _get_course_progress_hours(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Get total course progress hours in a period."""
        # Get courses with activity in the period
        query = select(
            func.coalesce(func.sum(Course.completed_hours), 0)
        ).where(
            and_(
                Course.user_id == user_id,
                func.date(Course.last_activity) >= start_date,
                func.date(Course.last_activity) <= end_date,
            )
        )
        result = await self.session.execute(query)
        # This is a simplification - ideally we'd track incremental progress
        return Decimal(str(result.scalar() or 0))

    async def _count_job_applications(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count job applications submitted in a period."""
        query = select(func.count(JobApplication.id)).where(
            and_(
                JobApplication.user_id == user_id,
                JobApplication.applied_date >= start_date,
                JobApplication.applied_date <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_achievements(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count achievements added in a period."""
        query = select(func.count(Achievement.id)).where(
            and_(
                Achievement.user_id == user_id,
                func.date(Achievement.created_at) >= start_date,
                func.date(Achievement.created_at) <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_exams_bookmarked(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count exams bookmarked in a period."""
        query = select(func.count(ExamBookmark.id)).where(
            and_(
                ExamBookmark.user_id == user_id,
                func.date(ExamBookmark.created_at) >= start_date,
                func.date(ExamBookmark.created_at) <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_exams_applied(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count exams applied to in a period."""
        query = select(func.count(ExamApplication.id)).where(
            and_(
                ExamApplication.user_id == user_id,
                ExamApplication.applied_date >= start_date,
                ExamApplication.applied_date <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_life_score(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> int:
        """Get life score for a specific date (or closest available)."""
        query = (
            select(LifeScore.total_score)
            .where(
                and_(
                    LifeScore.user_id == user_id,
                    LifeScore.score_date <= target_date,
                )
            )
            .order_by(LifeScore.score_date.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        score = result.scalar()
        return score if score is not None else 0

    async def _collect_metrics(
        self,
        user_id: uuid.UUID,
        week_start: date,
        week_end: date,
    ) -> WeeklySummaryMetrics:
        """Collect all metrics for a week.
        
        Validates: Requirements 34.2
        """
        # Money module
        expenses_total, expenses_count = await self._count_expenses(
            user_id, week_start, week_end
        )
        
        # Documents module
        documents_added = await self._count_documents(user_id, week_start, week_end)
        
        # Health module
        health_records_logged = await self._count_health_records(
            user_id, week_start, week_end
        )
        medicine_doses_taken = await self._count_medicine_doses(
            user_id, week_start, week_end
        )
        vitals_logged = await self._count_vitals(user_id, week_start, week_end)
        
        # Wardrobe module
        wardrobe_items_added = await self._count_wardrobe_items(
            user_id, week_start, week_end
        )
        outfits_worn = await self._count_outfits_worn(user_id, week_start, week_end)
        
        # Career module
        skills_updated = await self._count_skills_updated(user_id, week_start, week_end)
        courses_progress_hours = await self._get_course_progress_hours(
            user_id, week_start, week_end
        )
        job_applications = await self._count_job_applications(
            user_id, week_start, week_end
        )
        achievements_added = await self._count_achievements(
            user_id, week_start, week_end
        )
        
        # Exams module
        exams_bookmarked = await self._count_exams_bookmarked(
            user_id, week_start, week_end
        )
        exams_applied = await self._count_exams_applied(user_id, week_start, week_end)
        
        # Life score at end of week
        life_score = await self._get_life_score(user_id, week_end)
        
        # Calculate total activities
        total_activities = (
            expenses_count +
            documents_added +
            health_records_logged +
            medicine_doses_taken +
            vitals_logged +
            wardrobe_items_added +
            outfits_worn +
            skills_updated +
            job_applications +
            achievements_added +
            exams_bookmarked +
            exams_applied
        )
        
        return WeeklySummaryMetrics(
            expenses_total=expenses_total,
            expenses_count=expenses_count,
            documents_added=documents_added,
            health_records_logged=health_records_logged,
            medicine_doses_taken=medicine_doses_taken,
            vitals_logged=vitals_logged,
            wardrobe_items_added=wardrobe_items_added,
            outfits_worn=outfits_worn,
            skills_updated=skills_updated,
            courses_progress_hours=courses_progress_hours,
            job_applications=job_applications,
            achievements_added=achievements_added,
            exams_bookmarked=exams_bookmarked,
            exams_applied=exams_applied,
            life_score=life_score,
            total_activities=total_activities,
        )

    def _calculate_comparisons(
        self,
        current: WeeklySummaryMetrics,
        previous: WeeklySummaryMetrics,
    ) -> WeeklySummaryComparisons:
        """Calculate comparison metrics between current and previous week.
        
        Validates: Requirements 34.3
        """
        def calc_percent_change(current_val: Decimal, previous_val: Decimal) -> Optional[Decimal]:
            if previous_val == 0:
                return None
            return round((current_val - previous_val) / previous_val * 100, 2)
        
        return WeeklySummaryComparisons(
            # Money
            expenses_total_change=current.expenses_total - previous.expenses_total,
            expenses_total_change_percent=calc_percent_change(
                current.expenses_total, previous.expenses_total
            ),
            expenses_count_change=current.expenses_count - previous.expenses_count,
            
            # Documents
            documents_added_change=current.documents_added - previous.documents_added,
            
            # Health
            health_records_logged_change=current.health_records_logged - previous.health_records_logged,
            medicine_doses_taken_change=current.medicine_doses_taken - previous.medicine_doses_taken,
            vitals_logged_change=current.vitals_logged - previous.vitals_logged,
            
            # Wardrobe
            wardrobe_items_added_change=current.wardrobe_items_added - previous.wardrobe_items_added,
            outfits_worn_change=current.outfits_worn - previous.outfits_worn,
            
            # Career
            skills_updated_change=current.skills_updated - previous.skills_updated,
            courses_progress_hours_change=current.courses_progress_hours - previous.courses_progress_hours,
            job_applications_change=current.job_applications - previous.job_applications,
            achievements_added_change=current.achievements_added - previous.achievements_added,
            
            # Exams
            exams_bookmarked_change=current.exams_bookmarked - previous.exams_bookmarked,
            exams_applied_change=current.exams_applied - previous.exams_applied,
            
            # Overall
            life_score_change=current.life_score - previous.life_score,
            total_activities_change=current.total_activities - previous.total_activities,
        )

    async def generate_weekly_summary(
        self,
        user_id: uuid.UUID,
        week_start: Optional[date] = None,
    ) -> WeeklySummary:
        """Generate a weekly summary for a user.
        
        Validates: Requirements 34.1, 34.2, 34.3
        
        Args:
            user_id: User's UUID
            week_start: Start of the week (Monday). Defaults to last completed week.
            
        Returns:
            Generated WeeklySummary model instance
        """
        # Determine week boundaries
        if week_start is None:
            week_start, week_end = get_last_completed_week()
        else:
            week_start, week_end = get_week_boundaries(week_start)
        
        # Collect current week metrics
        current_metrics = await self._collect_metrics(user_id, week_start, week_end)
        
        # Collect previous week metrics for comparison
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_end - timedelta(days=7)
        previous_metrics = await self._collect_metrics(
            user_id, prev_week_start, prev_week_end
        )
        
        # Calculate comparisons
        comparisons = self._calculate_comparisons(current_metrics, previous_metrics)
        
        # Store the summary
        generated_at = datetime.now(timezone.utc)
        summary = await self.repo.create_or_update_summary(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            metrics=current_metrics.model_dump(mode="json"),
            comparisons=comparisons.model_dump(mode="json"),
            generated_at=generated_at,
        )
        
        logger.info(
            f"Generated weekly summary for user {user_id}: "
            f"week {week_start} to {week_end}, "
            f"{current_metrics.total_activities} activities"
        )
        
        return summary

    def _build_notification_content(
        self,
        summary: WeeklySummary,
    ) -> WeeklySummaryNotificationContent:
        """Build notification content for a weekly summary.
        
        Validates: Requirements 34.4
        """
        metrics = WeeklySummaryMetrics(**summary.metrics)
        comparisons = WeeklySummaryComparisons(**summary.comparisons)
        
        # Build title
        title = f"Your Week in Review ({summary.week_start.strftime('%b %d')} - {summary.week_end.strftime('%b %d')})"
        
        # Build body with highlights
        highlights = []
        
        # Expenses
        if metrics.expenses_count > 0:
            change_str = ""
            if comparisons.expenses_total_change_percent is not None:
                sign = "+" if comparisons.expenses_total_change > 0 else ""
                change_str = f" ({sign}{comparisons.expenses_total_change_percent}%)"
            highlights.append(
                f"💰 Spent ${metrics.expenses_total:.2f} across {metrics.expenses_count} expenses{change_str}"
            )
        
        # Documents
        if metrics.documents_added > 0:
            highlights.append(f"📄 Added {metrics.documents_added} document(s)")
        
        # Health
        health_activities = (
            metrics.health_records_logged +
            metrics.medicine_doses_taken +
            metrics.vitals_logged
        )
        if health_activities > 0:
            highlights.append(f"🏥 {health_activities} health activities logged")
        
        # Career
        career_activities = (
            metrics.skills_updated +
            metrics.job_applications +
            metrics.achievements_added
        )
        if career_activities > 0:
            highlights.append(f"💼 {career_activities} career activities")
        
        # Life score
        score_change = comparisons.life_score_change
        if score_change != 0:
            direction = "📈" if score_change > 0 else "📉"
            sign = "+" if score_change > 0 else ""
            highlights.append(
                f"{direction} Life Score: {metrics.life_score} ({sign}{score_change})"
            )
        else:
            highlights.append(f"⭐ Life Score: {metrics.life_score}")
        
        body = "\n".join(highlights) if highlights else "No activities this week. Start tracking to see your progress!"
        
        return WeeklySummaryNotificationContent(
            title=title,
            body=body,
            summary_id=summary.id,
        )

    async def generate_and_send_summary(
        self,
        user_id: uuid.UUID,
        week_start: Optional[date] = None,
    ) -> tuple[WeeklySummary, bool]:
        """Generate a weekly summary and send notification.
        
        Validates: Requirements 34.1, 34.4
        
        Args:
            user_id: User's UUID
            week_start: Start of the week (Monday). Defaults to last completed week.
            
        Returns:
            Tuple of (WeeklySummary, notification_sent)
        """
        from app.services.notification import NotificationService
        
        # Generate the summary
        summary = await self.generate_weekly_summary(user_id, week_start)
        
        # Build notification content
        notification_content = self._build_notification_content(summary)
        
        # Send notification via user's preferred channel
        notification_sent = False
        try:
            notification_service = NotificationService(self.session)
            
            # Get user's preferred channels
            preferences = await notification_service.get_preferences(user_id)
            
            # Determine channels to use (prefer push, fallback to email)
            channels = []
            if preferences.push_enabled:
                channels.append(NotificationChannel.PUSH)
            if preferences.email_enabled:
                channels.append(NotificationChannel.EMAIL)
            
            if not channels:
                # Default to push if no preferences set
                channels = [NotificationChannel.PUSH]
            
            # Send with fallback
            result = await notification_service.send_with_fallback(
                user_id=user_id,
                title=notification_content.title,
                body=notification_content.body,
                channels=channels,
            )
            notification_sent = result.success
            
            if notification_sent:
                logger.info(
                    f"Sent weekly summary notification to user {user_id} "
                    f"via {result.channel_used}"
                )
            else:
                logger.warning(
                    f"Failed to send weekly summary notification to user {user_id}: "
                    f"{result.error}"
                )
                
        except Exception as e:
            logger.exception(f"Error sending weekly summary notification: {e}")
        
        return summary, notification_sent

    async def get_summary(
        self,
        user_id: uuid.UUID,
        week_start: date,
    ) -> Optional[WeeklySummaryResponse]:
        """Get a specific weekly summary.
        
        Validates: Requirements 34.5
        """
        summary = await self.repo.get_summary_by_week(user_id, week_start)
        if not summary:
            return None
        
        return self._to_response(summary)

    async def get_latest_summary(
        self,
        user_id: uuid.UUID,
    ) -> Optional[WeeklySummaryResponse]:
        """Get the most recent weekly summary.
        
        Validates: Requirements 34.5
        """
        summary = await self.repo.get_latest_summary(user_id)
        if not summary:
            return None
        
        return self._to_response(summary)

    async def get_past_summaries(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> WeeklySummaryListResponse:
        """Get paginated list of past weekly summaries.
        
        Validates: Requirements 34.5
        """
        summaries, total = await self.repo.get_summaries_paginated(
            user_id, page, page_size
        )
        
        return WeeklySummaryListResponse(
            summaries=[self._to_response(s) for s in summaries],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    def _to_response(self, summary: WeeklySummary) -> WeeklySummaryResponse:
        """Convert WeeklySummary model to response schema."""
        return WeeklySummaryResponse(
            id=summary.id,
            user_id=summary.user_id,
            week_start=summary.week_start,
            week_end=summary.week_end,
            metrics=WeeklySummaryMetrics(**summary.metrics),
            comparisons=WeeklySummaryComparisons(**summary.comparisons),
            generated_at=summary.generated_at,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )
