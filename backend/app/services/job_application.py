"""Service for job application tracking.

Validates: Requirements 27.1, 27.2, 27.3, 27.4, 27.5, 27.6
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_application import (
    ApplicationFollowUpReminder,
    ApplicationSource,
    ApplicationStatus,
    ApplicationStatusHistory,
    JobApplication,
)
from app.models.notification import NotificationChannel
from app.repositories.job_application import (
    ApplicationFollowUpReminderRepository,
    ApplicationStatusHistoryRepository,
    JobApplicationRepository,
)
from app.schemas.job_application import (
    ApplicationStatisticsResponse,
    FollowUpReminderCreate,
    FollowUpReminderResponse,
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
    JobApplicationWithHistoryResponse,
    KanbanBoardResponse,
    KanbanColumnResponse,
    PaginatedJobApplicationResponse,
    StaleApplicationResponse,
    StatusUpdateRequest,
)
from app.services.notification import NotificationService


class JobApplicationService:
    """Service for job application tracking.
    
    Implements Requirements 27.1-27.6 for job application management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.app_repo = JobApplicationRepository(session)
        self.history_repo = ApplicationStatusHistoryRepository(session)
        self.reminder_repo = ApplicationFollowUpReminderRepository(session)

    async def add_application(
        self,
        user_id: uuid.UUID,
        data: JobApplicationCreate,
    ) -> JobApplication:
        """Add a new job application.
        
        Requirement 27.1: Store company, role, date, source, and status
        """
        application = await self.app_repo.create_application(
            user_id=user_id,
            company=data.company,
            role=data.role,
            url=data.url,
            source=data.source,
            status=data.status,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            applied_date=data.applied_date,
            notes=data.notes,
            location=data.location,
            is_remote=data.is_remote,
        )

        # Create initial status history entry
        await self.history_repo.create_history_entry(
            application_id=application.id,
            previous_status=None,
            new_status=data.status,
            notes="Application created",
        )

        # Schedule automatic follow-up reminder for 14 days
        reminder_date = data.applied_date + timedelta(days=14)
        await self.reminder_repo.create_reminder(
            application_id=application.id,
            reminder_date=reminder_date,
            notes="Automatic follow-up reminder",
        )

        return application

    async def get_application(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[JobApplication]:
        """Get an application by ID."""
        return await self.app_repo.get_application_by_id(application_id, user_id)

    async def get_application_with_history(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[JobApplicationWithHistoryResponse]:
        """Get an application with its status history and reminders."""
        application = await self.app_repo.get_application_with_history(
            application_id, user_id
        )
        if not application:
            return None
        return JobApplicationWithHistoryResponse.model_validate(application)

    async def get_applications(
        self,
        user_id: uuid.UUID,
        status: Optional[ApplicationStatus] = None,
        source: Optional[ApplicationSource] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedJobApplicationResponse:
        """Get applications for a user with optional filtering."""
        applications, total = await self.app_repo.get_applications(
            user_id=user_id,
            status=status,
            source=source,
            page=page,
            page_size=page_size,
        )
        
        items = [JobApplicationResponse.model_validate(app) for app in applications]
        return PaginatedJobApplicationResponse.create(items, total, page, page_size)

    async def update_application(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        data: JobApplicationUpdate,
    ) -> Optional[JobApplication]:
        """Update an application."""
        application = await self.app_repo.get_application_by_id(application_id, user_id)
        if not application:
            return None

        update_data = data.model_dump(exclude_unset=True)
        application = await self.app_repo.update_application(application, **update_data)
        return application

    async def update_status(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        data: StatusUpdateRequest,
    ) -> Optional[JobApplication]:
        """Update application status and record the change.
        
        Requirement 27.2, 27.3: Update status and record change with timestamp
        """
        application = await self.app_repo.get_application_by_id(application_id, user_id)
        if not application:
            return None

        previous_status = application.status
        
        # Don't create history if status hasn't changed
        if previous_status == data.status:
            return application

        # Update application status
        now = datetime.now(timezone.utc)
        await self.app_repo.update_application(
            application,
            status=data.status,
            last_status_update=now,
        )

        # Create status history entry
        await self.history_repo.create_history_entry(
            application_id=application_id,
            previous_status=previous_status,
            new_status=data.status,
            notes=data.notes,
        )

        # If status changed to a terminal state, cancel pending reminders
        terminal_statuses = [
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ]
        if data.status in terminal_statuses:
            # Mark all pending reminders as sent (effectively canceling them)
            reminders = await self.reminder_repo.get_reminders_for_application(
                application_id
            )
            for reminder in reminders:
                if not reminder.is_sent:
                    await self.reminder_repo.mark_reminder_sent(reminder)

        return application

    async def delete_application(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an application."""
        application = await self.app_repo.get_application_by_id(application_id, user_id)
        if not application:
            return False
        await self.app_repo.delete_application(application)
        return True

    async def get_kanban_board(
        self,
        user_id: uuid.UUID,
    ) -> KanbanBoardResponse:
        """Get applications organized as a kanban board.
        
        Requirement 27.4: Display applications in kanban board view by status
        """
        grouped = await self.app_repo.get_applications_by_status(user_id)
        
        columns = []
        total = 0
        
        # Define the order of columns for the kanban board
        status_order = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.SCREENING,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ]
        
        for status in status_order:
            apps = grouped.get(status, [])
            columns.append(KanbanColumnResponse(
                status=status,
                applications=[JobApplicationResponse.model_validate(app) for app in apps],
                count=len(apps),
            ))
            total += len(apps)

        return KanbanBoardResponse(
            columns=columns,
            total_applications=total,
        )

    async def get_statistics(
        self,
        user_id: uuid.UUID,
    ) -> ApplicationStatisticsResponse:
        """Get application statistics.
        
        Requirement 27.6: Track application statistics including response rate and time to response
        """
        stats = await self.app_repo.get_application_statistics(user_id)
        
        # Get average response time
        avg_response_time = await self.history_repo.get_average_response_time(user_id)
        
        # Get applications this month
        today = date.today()
        month_start = today.replace(day=1)
        applications_this_month = await self.app_repo.count_applications_in_period(
            user_id, month_start, today
        )
        
        # Get applications this week
        week_start = today - timedelta(days=today.weekday())
        applications_this_week = await self.app_repo.count_applications_in_period(
            user_id, week_start, today
        )

        return ApplicationStatisticsResponse(
            total_applications=stats["total"],
            by_status=stats["by_status"],
            response_rate=stats["response_rate"],
            average_days_to_response=avg_response_time,
            applications_this_month=applications_this_month,
            applications_this_week=applications_this_week,
            offer_rate=stats["offer_rate"],
            rejection_rate=stats["rejection_rate"],
        )

    async def get_stale_applications(
        self,
        user_id: uuid.UUID,
        stale_days: int = 14,
    ) -> list[StaleApplicationResponse]:
        """Get applications needing follow-up.
        
        Requirement 27.5: Identify applications with no update in 14 days
        """
        applications = await self.app_repo.get_stale_applications(user_id, stale_days)
        now = datetime.now(timezone.utc)
        
        result = []
        for app in applications:
            days_since_update = (now - app.last_status_update).days
            result.append(StaleApplicationResponse(
                application_id=app.id,
                company=app.company,
                role=app.role,
                status=app.status,
                days_since_update=days_since_update,
                last_status_update=app.last_status_update,
                applied_date=app.applied_date,
            ))
        
        return result

    async def add_follow_up_reminder(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        data: FollowUpReminderCreate,
    ) -> Optional[ApplicationFollowUpReminder]:
        """Add a follow-up reminder for an application."""
        application = await self.app_repo.get_application_by_id(application_id, user_id)
        if not application:
            return None

        reminder = await self.reminder_repo.create_reminder(
            application_id=application_id,
            reminder_date=data.reminder_date,
            notes=data.notes,
        )
        return reminder

    async def send_follow_up_reminders(
        self,
        user_id: uuid.UUID,
    ) -> int:
        """Send pending follow-up reminders.
        
        Requirement 27.5: Send follow-up reminders
        
        Returns:
            Number of reminders sent
        """
        pending_reminders = await self.reminder_repo.get_pending_reminders(user_id)
        
        if not pending_reminders:
            return 0

        notification_service = NotificationService(self.session)
        reminders_sent = 0

        for reminder in pending_reminders:
            # Get the application details
            application = await self.app_repo.get_application_by_id(
                reminder.application_id, user_id
            )
            if not application:
                continue

            # Skip if application is in a terminal state
            terminal_statuses = [
                ApplicationStatus.OFFER,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            ]
            if application.status in terminal_statuses:
                await self.reminder_repo.mark_reminder_sent(reminder)
                continue

            title = "Job Application Follow-up Reminder"
            body = (
                f"Time to follow up on your application to {application.company} "
                f"for the {application.role} position. "
                f"Current status: {application.status.value.title()}."
            )
            
            result = await notification_service.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel=NotificationChannel.PUSH,
            )
            
            if result.success:
                await self.reminder_repo.mark_reminder_sent(reminder)
                reminders_sent += 1

        return reminders_sent

    async def send_stale_application_reminders(
        self,
        user_id: uuid.UUID,
        stale_days: int = 14,
    ) -> int:
        """Send reminders for stale applications.
        
        Requirement 27.5: Prompt user to follow up when application has no update in 14 days
        
        Returns:
            Number of reminders sent
        """
        stale_apps = await self.get_stale_applications(user_id, stale_days)
        
        if not stale_apps:
            return 0

        notification_service = NotificationService(self.session)
        reminders_sent = 0

        for app in stale_apps:
            title = "Application Follow-up Needed"
            body = (
                f"Your application to {app.company} for {app.role} "
                f"hasn't been updated in {app.days_since_update} days. "
                f"Consider following up!"
            )
            
            result = await notification_service.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel=NotificationChannel.PUSH,
            )
            
            if result.success:
                reminders_sent += 1

        return reminders_sent
