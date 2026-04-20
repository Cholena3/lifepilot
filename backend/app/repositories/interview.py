"""Repository for interview preparation database operations.

Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interview import (
    InterviewNote,
    InterviewPreparationReminder,
    InterviewType,
    QuestionAnswer,
)
from app.models.job_application import JobApplication


class InterviewNoteRepository:
    """Repository for InterviewNote CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_interview_note(
        self,
        application_id: uuid.UUID,
        interview_type: InterviewType = InterviewType.OTHER,
        interview_date: Optional[date] = None,
        interview_time: Optional[str] = None,
        company_research: Optional[str] = None,
        questions_asked: Optional[list[str]] = None,
        answers_prepared: Optional[list[str]] = None,
    ) -> InterviewNote:
        """Create a new interview note.
        
        Requirement 28.1: Associate interview notes with a job application
        Requirement 28.2: Store company research, questions asked, and answers prepared
        """
        note = InterviewNote(
            application_id=application_id,
            interview_type=interview_type,
            interview_date=interview_date,
            interview_time=interview_time,
            company_research=company_research,
            questions_asked=questions_asked or [],
            answers_prepared=answers_prepared or [],
        )
        self.session.add(note)
        await self.session.flush()
        return note

    async def get_interview_note_by_id(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[InterviewNote]:
        """Get an interview note by ID for a specific user."""
        query = (
            select(InterviewNote)
            .join(JobApplication)
            .where(
                InterviewNote.id == note_id,
                JobApplication.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_interview_note_with_details(
        self,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[InterviewNote]:
        """Get an interview note with reminders and Q&A entries."""
        query = (
            select(InterviewNote)
            .options(
                selectinload(InterviewNote.preparation_reminders),
                selectinload(InterviewNote.qa_entries),
            )
            .join(JobApplication)
            .where(
                InterviewNote.id == note_id,
                JobApplication.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_interview_notes_for_application(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[InterviewNote]:
        """Get all interview notes for a job application."""
        query = (
            select(InterviewNote)
            .join(JobApplication)
            .where(
                InterviewNote.application_id == application_id,
                JobApplication.user_id == user_id,
            )
            .order_by(InterviewNote.interview_date.desc().nullslast())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_interview_notes_for_user(
        self,
        user_id: uuid.UUID,
        interview_type: Optional[InterviewType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InterviewNote], int]:
        """Get all interview notes for a user with optional filtering."""
        query = (
            select(InterviewNote)
            .join(JobApplication)
            .where(JobApplication.user_id == user_id)
        )
        count_query = (
            select(func.count(InterviewNote.id))
            .join(JobApplication)
            .where(JobApplication.user_id == user_id)
        )

        if interview_type is not None:
            query = query.where(InterviewNote.interview_type == interview_type)
            count_query = count_query.where(InterviewNote.interview_type == interview_type)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(
            InterviewNote.interview_date.desc().nullslast(),
            InterviewNote.created_at.desc(),
        )
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        notes = list(result.scalars().all())

        return notes, total

    async def update_interview_note(
        self,
        note: InterviewNote,
        **kwargs,
    ) -> InterviewNote:
        """Update an interview note's attributes."""
        for key, value in kwargs.items():
            if value is not None and hasattr(note, key):
                setattr(note, key, value)
        await self.session.flush()
        return note

    async def delete_interview_note(self, note: InterviewNote) -> None:
        """Delete an interview note."""
        await self.session.delete(note)
        await self.session.flush()

    async def get_upcoming_interviews(
        self,
        user_id: uuid.UUID,
        days_ahead: int = 7,
    ) -> list[InterviewNote]:
        """Get interviews scheduled within the next N days.
        
        Requirement 28.3: For sending preparation reminders
        """
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        query = (
            select(InterviewNote)
            .join(JobApplication)
            .where(
                JobApplication.user_id == user_id,
                InterviewNote.interview_date >= today,
                InterviewNote.interview_date <= end_date,
            )
            .order_by(InterviewNote.interview_date.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


    async def get_interview_history(
        self,
        user_id: uuid.UUID,
    ) -> list[tuple[InterviewNote, JobApplication]]:
        """Get interview history with application details.
        
        Requirement 28.5: Display interview history with outcomes
        """
        query = (
            select(InterviewNote, JobApplication)
            .join(JobApplication)
            .where(JobApplication.user_id == user_id)
            .order_by(InterviewNote.interview_date.desc().nullslast())
        )
        result = await self.session.execute(query)
        return list(result.all())

    async def get_interview_statistics(
        self,
        user_id: uuid.UUID,
    ) -> dict:
        """Get interview statistics for a user.
        
        Requirement 28.5: Pattern analysis from interview history
        """
        # Get all interview notes for the user
        query = (
            select(InterviewNote)
            .join(JobApplication)
            .where(JobApplication.user_id == user_id)
        )
        result = await self.session.execute(query)
        notes = list(result.scalars().all())

        if not notes:
            return {
                "total": 0,
                "by_type": {},
                "by_outcome": {},
                "average_rating": None,
                "pass_rate": 0.0,
            }

        total = len(notes)
        
        # Count by type
        by_type = {}
        for note in notes:
            type_value = note.interview_type.value
            by_type[type_value] = by_type.get(type_value, 0) + 1

        # Count by outcome
        by_outcome = {}
        passed_count = 0
        outcome_count = 0
        for note in notes:
            if note.outcome:
                outcome_count += 1
                by_outcome[note.outcome] = by_outcome.get(note.outcome, 0) + 1
                if note.outcome.lower() in ["passed", "pass", "success"]:
                    passed_count += 1

        # Calculate average rating
        ratings = [n.performance_rating for n in notes if n.performance_rating is not None]
        average_rating = sum(ratings) / len(ratings) if ratings else None

        # Calculate pass rate
        pass_rate = (passed_count / outcome_count * 100) if outcome_count > 0 else 0.0

        return {
            "total": total,
            "by_type": by_type,
            "by_outcome": by_outcome,
            "average_rating": average_rating,
            "pass_rate": pass_rate,
        }

    async def count_interviews_in_period(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count interviews within a date range."""
        query = (
            select(func.count(InterviewNote.id))
            .join(JobApplication)
            .where(
                JobApplication.user_id == user_id,
                InterviewNote.interview_date >= start_date,
                InterviewNote.interview_date <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0


class InterviewPreparationReminderRepository:
    """Repository for InterviewPreparationReminder operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_reminder(
        self,
        interview_note_id: uuid.UUID,
        reminder_date: date,
        reminder_time: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> InterviewPreparationReminder:
        """Create a preparation reminder.
        
        Requirement 28.3: Send preparation reminders
        """
        reminder = InterviewPreparationReminder(
            interview_note_id=interview_note_id,
            reminder_date=reminder_date,
            reminder_time=reminder_time,
            notes=notes,
        )
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get_pending_reminders(
        self,
        user_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> list[InterviewPreparationReminder]:
        """Get pending reminders for a user.
        
        Requirement 28.3: Get reminders that need to be sent
        """
        if as_of_date is None:
            as_of_date = date.today()

        query = (
            select(InterviewPreparationReminder)
            .join(InterviewNote)
            .join(JobApplication)
            .where(
                JobApplication.user_id == user_id,
                InterviewPreparationReminder.is_sent == False,
                InterviewPreparationReminder.reminder_date <= as_of_date,
            )
            .order_by(InterviewPreparationReminder.reminder_date.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_reminder_sent(
        self,
        reminder: InterviewPreparationReminder,
    ) -> InterviewPreparationReminder:
        """Mark a reminder as sent."""
        reminder.is_sent = True
        reminder.sent_at = datetime.now(timezone.utc)
        await self.session.flush()
        return reminder

    async def get_reminders_for_interview(
        self,
        interview_note_id: uuid.UUID,
    ) -> list[InterviewPreparationReminder]:
        """Get all reminders for an interview note."""
        query = (
            select(InterviewPreparationReminder)
            .where(InterviewPreparationReminder.interview_note_id == interview_note_id)
            .order_by(InterviewPreparationReminder.reminder_date.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_reminder(self, reminder: InterviewPreparationReminder) -> None:
        """Delete a reminder."""
        await self.session.delete(reminder)
        await self.session.flush()


class QuestionAnswerRepository:
    """Repository for QuestionAnswer operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_qa(
        self,
        interview_note_id: uuid.UUID,
        question: str,
        answer: Optional[str] = None,
        category: Optional[str] = None,
        is_asked: bool = False,
        notes: Optional[str] = None,
    ) -> QuestionAnswer:
        """Create a Q&A entry.
        
        Requirement 28.2: Store questions asked and answers prepared
        """
        qa = QuestionAnswer(
            interview_note_id=interview_note_id,
            question=question,
            answer=answer,
            category=category,
            is_asked=is_asked,
            notes=notes,
        )
        self.session.add(qa)
        await self.session.flush()
        return qa

    async def get_qa_by_id(
        self,
        qa_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[QuestionAnswer]:
        """Get a Q&A entry by ID."""
        query = (
            select(QuestionAnswer)
            .join(InterviewNote)
            .join(JobApplication)
            .where(
                QuestionAnswer.id == qa_id,
                JobApplication.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_qa_for_interview(
        self,
        interview_note_id: uuid.UUID,
    ) -> list[QuestionAnswer]:
        """Get all Q&A entries for an interview note."""
        query = (
            select(QuestionAnswer)
            .where(QuestionAnswer.interview_note_id == interview_note_id)
            .order_by(QuestionAnswer.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_qa(
        self,
        qa: QuestionAnswer,
        **kwargs,
    ) -> QuestionAnswer:
        """Update a Q&A entry."""
        for key, value in kwargs.items():
            if value is not None and hasattr(qa, key):
                setattr(qa, key, value)
        await self.session.flush()
        return qa

    async def delete_qa(self, qa: QuestionAnswer) -> None:
        """Delete a Q&A entry."""
        await self.session.delete(qa)
        await self.session.flush()
