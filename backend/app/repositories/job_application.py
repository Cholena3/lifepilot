"""Repository for job application database operations.

Validates: Requirements 27.1, 27.2, 27.3, 27.4, 27.5, 27.6
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job_application import (
    ApplicationFollowUpReminder,
    ApplicationSource,
    ApplicationStatus,
    ApplicationStatusHistory,
    JobApplication,
)


class JobApplicationRepository:
    """Repository for JobApplication CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_application(
        self,
        user_id: uuid.UUID,
        company: str,
        role: str,
        url: Optional[str] = None,
        source: ApplicationSource = ApplicationSource.OTHER,
        status: ApplicationStatus = ApplicationStatus.APPLIED,
        salary_min: Optional[Decimal] = None,
        salary_max: Optional[Decimal] = None,
        applied_date: Optional[date] = None,
        notes: Optional[str] = None,
        location: Optional[str] = None,
        is_remote: bool = False,
    ) -> JobApplication:
        """Create a new job application.
        
        Requirement 27.1: Store company, role, date, source, and status
        """
        application = JobApplication(
            user_id=user_id,
            company=company,
            role=role,
            url=url,
            source=source,
            status=status,
            salary_min=salary_min,
            salary_max=salary_max,
            applied_date=applied_date or date.today(),
            notes=notes,
            location=location,
            is_remote=is_remote,
        )
        self.session.add(application)
        await self.session.flush()
        return application

    async def get_application_by_id(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[JobApplication]:
        """Get an application by ID for a specific user."""
        query = select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_application_with_history(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[JobApplication]:
        """Get an application with its status history and reminders."""
        query = (
            select(JobApplication)
            .options(
                selectinload(JobApplication.status_history),
                selectinload(JobApplication.follow_up_reminders),
            )
            .where(
                JobApplication.id == application_id,
                JobApplication.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_applications(
        self,
        user_id: uuid.UUID,
        status: Optional[ApplicationStatus] = None,
        source: Optional[ApplicationSource] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[JobApplication], int]:
        """Get applications for a user with optional filtering and pagination."""
        query = select(JobApplication).where(JobApplication.user_id == user_id)
        count_query = select(func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id
        )

        if status is not None:
            query = query.where(JobApplication.status == status)
            count_query = count_query.where(JobApplication.status == status)

        if source is not None:
            query = query.where(JobApplication.source == source)
            count_query = count_query.where(JobApplication.source == source)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(
            JobApplication.last_status_update.desc(),
            JobApplication.applied_date.desc(),
        )
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        applications = list(result.scalars().all())

        return applications, total

    async def get_all_applications(self, user_id: uuid.UUID) -> list[JobApplication]:
        """Get all applications for a user without pagination."""
        query = (
            select(JobApplication)
            .where(JobApplication.user_id == user_id)
            .order_by(JobApplication.applied_date.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_applications_by_status(
        self,
        user_id: uuid.UUID,
    ) -> dict[ApplicationStatus, list[JobApplication]]:
        """Get applications grouped by status for kanban view.
        
        Requirement 27.4: Display applications in kanban board view by status
        """
        query = (
            select(JobApplication)
            .where(JobApplication.user_id == user_id)
            .order_by(JobApplication.last_status_update.desc())
        )
        result = await self.session.execute(query)
        applications = list(result.scalars().all())

        # Group by status
        grouped: dict[ApplicationStatus, list[JobApplication]] = {
            status: [] for status in ApplicationStatus
        }
        for app in applications:
            grouped[app.status].append(app)

        return grouped

    async def update_application(
        self,
        application: JobApplication,
        **kwargs,
    ) -> JobApplication:
        """Update an application's attributes."""
        for key, value in kwargs.items():
            if value is not None and hasattr(application, key):
                setattr(application, key, value)
        await self.session.flush()
        return application

    async def delete_application(self, application: JobApplication) -> None:
        """Delete an application."""
        await self.session.delete(application)
        await self.session.flush()

    async def get_stale_applications(
        self,
        user_id: uuid.UUID,
        stale_days: int = 14,
    ) -> list[JobApplication]:
        """Get applications with no status update in the specified number of days.
        
        Requirement 27.5: Identify applications needing follow-up
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=stale_days)
        
        # Only consider active applications (not rejected, withdrawn, or offer)
        active_statuses = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.SCREENING,
            ApplicationStatus.INTERVIEW,
        ]
        
        query = (
            select(JobApplication)
            .where(
                JobApplication.user_id == user_id,
                JobApplication.status.in_(active_statuses),
                JobApplication.last_status_update < cutoff_date,
            )
            .order_by(JobApplication.last_status_update.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_application_statistics(
        self,
        user_id: uuid.UUID,
    ) -> dict:
        """Get application statistics for a user.
        
        Requirement 27.6: Track application statistics
        """
        # Get all applications
        applications = await self.get_all_applications(user_id)
        
        if not applications:
            return {
                "total": 0,
                "by_status": {},
                "response_rate": 0.0,
                "offer_rate": 0.0,
                "rejection_rate": 0.0,
            }

        total = len(applications)
        
        # Count by status
        by_status = {}
        for status in ApplicationStatus:
            count = sum(1 for app in applications if app.status == status)
            by_status[status.value] = count

        # Calculate response rate (applications that moved past "Applied" status)
        responded = sum(
            1 for app in applications 
            if app.status != ApplicationStatus.APPLIED
        )
        response_rate = (responded / total) * 100 if total > 0 else 0.0

        # Calculate offer rate
        offers = by_status.get(ApplicationStatus.OFFER.value, 0)
        offer_rate = (offers / total) * 100 if total > 0 else 0.0

        # Calculate rejection rate
        rejections = by_status.get(ApplicationStatus.REJECTED.value, 0)
        rejection_rate = (rejections / total) * 100 if total > 0 else 0.0

        return {
            "total": total,
            "by_status": by_status,
            "response_rate": response_rate,
            "offer_rate": offer_rate,
            "rejection_rate": rejection_rate,
        }

    async def count_applications_in_period(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count applications submitted within a date range."""
        query = select(func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id,
            JobApplication.applied_date >= start_date,
            JobApplication.applied_date <= end_date,
        )
        result = await self.session.execute(query)
        return result.scalar() or 0


class ApplicationStatusHistoryRepository:
    """Repository for ApplicationStatusHistory operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_history_entry(
        self,
        application_id: uuid.UUID,
        previous_status: Optional[ApplicationStatus],
        new_status: ApplicationStatus,
        notes: Optional[str] = None,
    ) -> ApplicationStatusHistory:
        """Create a status history entry.
        
        Requirement 27.3: Record status changes with timestamp
        """
        history = ApplicationStatusHistory(
            application_id=application_id,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
        )
        self.session.add(history)
        await self.session.flush()
        return history

    async def get_history_for_application(
        self,
        application_id: uuid.UUID,
    ) -> list[ApplicationStatusHistory]:
        """Get all status history for an application."""
        query = (
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == application_id)
            .order_by(ApplicationStatusHistory.changed_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_first_response_time(
        self,
        application_id: uuid.UUID,
    ) -> Optional[datetime]:
        """Get the timestamp of the first status change (response) for an application."""
        query = (
            select(ApplicationStatusHistory.changed_at)
            .where(
                ApplicationStatusHistory.application_id == application_id,
                ApplicationStatusHistory.previous_status == ApplicationStatus.APPLIED,
            )
            .order_by(ApplicationStatusHistory.changed_at.asc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_average_response_time(
        self,
        user_id: uuid.UUID,
    ) -> Optional[float]:
        """Calculate average days from application to first response.
        
        Requirement 27.6: Track time to response
        """
        # Get all applications with their first response times
        query = (
            select(
                JobApplication.applied_date,
                func.min(ApplicationStatusHistory.changed_at).label("first_response"),
            )
            .join(
                ApplicationStatusHistory,
                ApplicationStatusHistory.application_id == JobApplication.id,
            )
            .where(
                JobApplication.user_id == user_id,
                ApplicationStatusHistory.previous_status == ApplicationStatus.APPLIED,
            )
            .group_by(JobApplication.id, JobApplication.applied_date)
        )
        result = await self.session.execute(query)
        rows = result.all()

        if not rows:
            return None

        total_days = 0.0
        count = 0
        for applied_date, first_response in rows:
            if first_response:
                # Convert applied_date to datetime for comparison
                applied_datetime = datetime.combine(
                    applied_date, 
                    datetime.min.time(),
                    tzinfo=timezone.utc
                )
                days = (first_response - applied_datetime).days
                total_days += days
                count += 1

        return total_days / count if count > 0 else None


class ApplicationFollowUpReminderRepository:
    """Repository for ApplicationFollowUpReminder operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_reminder(
        self,
        application_id: uuid.UUID,
        reminder_date: date,
        notes: Optional[str] = None,
    ) -> ApplicationFollowUpReminder:
        """Create a follow-up reminder."""
        reminder = ApplicationFollowUpReminder(
            application_id=application_id,
            reminder_date=reminder_date,
            notes=notes,
        )
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get_pending_reminders(
        self,
        user_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> list[ApplicationFollowUpReminder]:
        """Get pending reminders for a user.
        
        Requirement 27.5: Get reminders that need to be sent
        """
        if as_of_date is None:
            as_of_date = date.today()

        query = (
            select(ApplicationFollowUpReminder)
            .join(JobApplication)
            .where(
                JobApplication.user_id == user_id,
                ApplicationFollowUpReminder.is_sent == False,
                ApplicationFollowUpReminder.reminder_date <= as_of_date,
            )
            .order_by(ApplicationFollowUpReminder.reminder_date.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_reminder_sent(
        self,
        reminder: ApplicationFollowUpReminder,
    ) -> ApplicationFollowUpReminder:
        """Mark a reminder as sent."""
        reminder.is_sent = True
        reminder.sent_at = datetime.now(timezone.utc)
        await self.session.flush()
        return reminder

    async def delete_reminder(self, reminder: ApplicationFollowUpReminder) -> None:
        """Delete a reminder."""
        await self.session.delete(reminder)
        await self.session.flush()

    async def get_reminders_for_application(
        self,
        application_id: uuid.UUID,
    ) -> list[ApplicationFollowUpReminder]:
        """Get all reminders for an application."""
        query = (
            select(ApplicationFollowUpReminder)
            .where(ApplicationFollowUpReminder.application_id == application_id)
            .order_by(ApplicationFollowUpReminder.reminder_date.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
