"""Service for interview preparation.

Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import (
    InterviewNote,
    InterviewPreparationReminder,
    InterviewType,
    QuestionAnswer,
)
from app.models.notification import NotificationChannel
from app.repositories.interview import (
    InterviewNoteRepository,
    InterviewPreparationReminderRepository,
    QuestionAnswerRepository,
)
from app.repositories.job_application import JobApplicationRepository
from app.schemas.interview import (
    InterviewHistoryResponse,
    InterviewNoteCreate,
    InterviewNoteResponse,
    InterviewNoteUpdate,
    InterviewNoteWithQAResponse,
    InterviewStatisticsResponse,
    PaginatedInterviewNoteResponse,
    PerformanceRatingUpdate,
    PreparationReminderCreate,
    PreparationReminderResponse,
    QuestionAnswerCreate,
    QuestionAnswerResponse,
    QuestionAnswerUpdate,
)
from app.services.notification import NotificationService


class InterviewService:
    """Service for interview preparation.
    
    Implements Requirements 28.1-28.5 for interview preparation management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.note_repo = InterviewNoteRepository(session)
        self.reminder_repo = InterviewPreparationReminderRepository(session)
        self.qa_repo = QuestionAnswerRepository(session)
        self.app_repo = JobApplicationRepository(session)

    async def add_interview_note(
        self,
        user_id: uuid.UUID,
        data: InterviewNoteCreate,
    ) -> Optional[InterviewNote]:
        """Add interview notes for a job application.
        
        Requirement 28.1: Associate interview notes with a job application
        Requirement 28.2: Store company research, questions asked, and answers prepared
        """
        # Verify the application belongs to the user
        application = await self.app_repo.get_application_by_id(
            data.application_id, user_id
        )
        if not application:
            return None

        note = await self.note_repo.create_interview_note(
            application_id=data.application_id,
            interview_type=data.interview_type,
            interview_date=data.interview_date,
            interview_time=data.interview_time,
            company_research=data.company_research,
            questions_asked=data.questions_asked,
            answers_prepared=data.answers_prepared,
        )

        # Schedule preparation reminders if interview date is set
        if data.interview_date:
            await self._schedule_preparation_reminders(note)

        return note

    async def _schedule_preparation_reminders(
        self,
        note: InterviewNote,
    ) -> None:
        """Schedule preparation reminders for an interview.
        
        Requirement 28.3: Send preparation reminders when interview is scheduled
        """
        if not note.interview_date:
            return

        today = date.today()
        interview_date = note.interview_date

        # Schedule reminders at 3 days, 1 day, and same day before interview
        reminder_days = [3, 1, 0]
        
        for days_before in reminder_days:
            reminder_date = interview_date - timedelta(days=days_before)
            if reminder_date >= today:
                await self.reminder_repo.create_reminder(
                    interview_note_id=note.id,
                    reminder_date=reminder_date,
                    notes=f"Interview preparation reminder - {days_before} day(s) before",
                )

    async def get_interview_note(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[InterviewNote]:
        """Get an interview note by ID."""
        return await self.note_repo.get_interview_note_by_id(note_id, user_id)

    async def get_interview_note_with_details(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[InterviewNoteWithQAResponse]:
        """Get an interview note with Q&A entries and reminders."""
        note = await self.note_repo.get_interview_note_with_details(note_id, user_id)
        if not note:
            return None
        return InterviewNoteWithQAResponse.model_validate(note)

    async def get_interview_notes_for_application(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[InterviewNoteResponse]:
        """Get all interview notes for a job application."""
        notes = await self.note_repo.get_interview_notes_for_application(
            application_id, user_id
        )
        return [InterviewNoteResponse.model_validate(n) for n in notes]

    async def get_interview_notes(
        self,
        user_id: uuid.UUID,
        interview_type: Optional[InterviewType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedInterviewNoteResponse:
        """Get all interview notes for a user with optional filtering."""
        notes, total = await self.note_repo.get_interview_notes_for_user(
            user_id=user_id,
            interview_type=interview_type,
            page=page,
            page_size=page_size,
        )
        
        items = [InterviewNoteResponse.model_validate(n) for n in notes]
        return PaginatedInterviewNoteResponse.create(items, total, page, page_size)

    async def update_interview_note(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        data: InterviewNoteUpdate,
    ) -> Optional[InterviewNote]:
        """Update an interview note."""
        note = await self.note_repo.get_interview_note_by_id(note_id, user_id)
        if not note:
            return None

        update_data = data.model_dump(exclude_unset=True)
        
        # If interview date changed, reschedule reminders
        old_date = note.interview_date
        note = await self.note_repo.update_interview_note(note, **update_data)
        
        if data.interview_date and data.interview_date != old_date:
            # Cancel existing reminders and schedule new ones
            reminders = await self.reminder_repo.get_reminders_for_interview(note.id)
            for reminder in reminders:
                if not reminder.is_sent:
                    await self.reminder_repo.delete_reminder(reminder)
            await self._schedule_preparation_reminders(note)

        return note

    async def update_performance_rating(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PerformanceRatingUpdate,
    ) -> Optional[InterviewNote]:
        """Update interview performance rating.
        
        Requirement 28.4: Allow users to rate their interview performance
        """
        note = await self.note_repo.get_interview_note_by_id(note_id, user_id)
        if not note:
            return None

        return await self.note_repo.update_interview_note(
            note,
            performance_rating=data.performance_rating,
            feedback=data.feedback,
            outcome=data.outcome,
        )

    async def delete_interview_note(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an interview note."""
        note = await self.note_repo.get_interview_note_by_id(note_id, user_id)
        if not note:
            return False
        await self.note_repo.delete_interview_note(note)
        return True


    async def get_interview_history(
        self,
        user_id: uuid.UUID,
    ) -> list[InterviewHistoryResponse]:
        """Get interview history with outcomes.
        
        Requirement 28.5: Display interview history with outcomes for pattern analysis
        """
        history = await self.note_repo.get_interview_history(user_id)
        
        result = []
        for note, application in history:
            result.append(InterviewHistoryResponse(
                id=note.id,
                application_id=note.application_id,
                company=application.company,
                role=application.role,
                interview_type=note.interview_type,
                interview_date=note.interview_date,
                performance_rating=note.performance_rating,
                outcome=note.outcome,
                created_at=note.created_at,
            ))
        
        return result

    async def get_interview_statistics(
        self,
        user_id: uuid.UUID,
    ) -> InterviewStatisticsResponse:
        """Get interview statistics.
        
        Requirement 28.5: Pattern analysis from interview history
        """
        stats = await self.note_repo.get_interview_statistics(user_id)
        
        # Get interviews this month
        today = date.today()
        month_start = today.replace(day=1)
        interviews_this_month = await self.note_repo.count_interviews_in_period(
            user_id, month_start, today
        )

        return InterviewStatisticsResponse(
            total_interviews=stats["total"],
            by_type=stats["by_type"],
            by_outcome=stats["by_outcome"],
            average_rating=stats["average_rating"],
            interviews_this_month=interviews_this_month,
            pass_rate=stats["pass_rate"],
        )

    async def add_preparation_reminder(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PreparationReminderCreate,
    ) -> Optional[InterviewPreparationReminder]:
        """Add a preparation reminder for an interview.
        
        Requirement 28.3: Send preparation reminders
        """
        note = await self.note_repo.get_interview_note_by_id(note_id, user_id)
        if not note:
            return None

        return await self.reminder_repo.create_reminder(
            interview_note_id=note_id,
            reminder_date=data.reminder_date,
            reminder_time=data.reminder_time,
            notes=data.notes,
        )

    async def send_preparation_reminders(
        self,
        user_id: uuid.UUID,
    ) -> int:
        """Send pending preparation reminders.
        
        Requirement 28.3: Send preparation reminders when interview is scheduled
        
        Returns:
            Number of reminders sent
        """
        pending_reminders = await self.reminder_repo.get_pending_reminders(user_id)
        
        if not pending_reminders:
            return 0

        notification_service = NotificationService(self.session)
        reminders_sent = 0

        for reminder in pending_reminders:
            # Get the interview note details
            note = await self.note_repo.get_interview_note_by_id(
                reminder.interview_note_id, user_id
            )
            if not note:
                continue

            # Get the application details
            application = await self.app_repo.get_application_by_id(
                note.application_id, user_id
            )
            if not application:
                continue

            title = "Interview Preparation Reminder"
            body = (
                f"Reminder: You have an interview scheduled with {application.company} "
                f"for the {application.role} position"
            )
            if note.interview_date:
                body += f" on {note.interview_date.strftime('%B %d, %Y')}"
            if note.interview_time:
                body += f" at {note.interview_time}"
            body += ". Time to prepare!"
            
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

    # Q&A Management
    async def add_qa_entry(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        data: QuestionAnswerCreate,
    ) -> Optional[QuestionAnswer]:
        """Add a Q&A entry to an interview note.
        
        Requirement 28.2: Store questions asked and answers prepared
        """
        note = await self.note_repo.get_interview_note_by_id(note_id, user_id)
        if not note:
            return None

        return await self.qa_repo.create_qa(
            interview_note_id=note_id,
            question=data.question,
            answer=data.answer,
            category=data.category,
            is_asked=data.is_asked,
            notes=data.notes,
        )

    async def get_qa_entries(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[QuestionAnswerResponse]:
        """Get all Q&A entries for an interview note."""
        note = await self.note_repo.get_interview_note_by_id(note_id, user_id)
        if not note:
            return []

        qa_entries = await self.qa_repo.get_qa_for_interview(note_id)
        return [QuestionAnswerResponse.model_validate(qa) for qa in qa_entries]

    async def update_qa_entry(
        self,
        qa_id: uuid.UUID,
        user_id: uuid.UUID,
        data: QuestionAnswerUpdate,
    ) -> Optional[QuestionAnswer]:
        """Update a Q&A entry."""
        qa = await self.qa_repo.get_qa_by_id(qa_id, user_id)
        if not qa:
            return None

        update_data = data.model_dump(exclude_unset=True)
        return await self.qa_repo.update_qa(qa, **update_data)

    async def delete_qa_entry(
        self,
        qa_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a Q&A entry."""
        qa = await self.qa_repo.get_qa_by_id(qa_id, user_id)
        if not qa:
            return False
        await self.qa_repo.delete_qa(qa)
        return True

    async def get_upcoming_interviews(
        self,
        user_id: uuid.UUID,
        days_ahead: int = 7,
    ) -> list[InterviewNoteResponse]:
        """Get upcoming interviews within the next N days."""
        notes = await self.note_repo.get_upcoming_interviews(user_id, days_ahead)
        return [InterviewNoteResponse.model_validate(n) for n in notes]
