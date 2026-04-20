"""Repository for course database operations.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, LearningSession


class CourseRepository:
    """Repository for Course CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_course(
        self,
        user_id: uuid.UUID,
        title: str,
        platform: Optional[str] = None,
        url: Optional[str] = None,
        total_hours: Decimal = Decimal("0"),
    ) -> Course:
        """Create a new course for a user.
        
        Requirement 25.1: Store course name, platform, URL, and total duration
        """
        course = Course(
            user_id=user_id,
            title=title,
            platform=platform,
            url=url,
            total_hours=total_hours,
            completed_hours=Decimal("0"),
            completion_percentage=0,
            is_completed=False,
        )
        self.session.add(course)
        await self.session.flush()
        return course

    async def get_course_by_id(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Course]:
        """Get a course by ID for a specific user."""
        query = select(Course).where(
            Course.id == course_id,
            Course.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_course_with_sessions(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Course]:
        """Get a course with its learning sessions."""
        query = (
            select(Course)
            .options(selectinload(Course.learning_sessions))
            .where(
                Course.id == course_id,
                Course.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_courses(
        self,
        user_id: uuid.UUID,
        is_completed: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Course], int]:
        """Get courses for a user with optional filtering and pagination."""
        query = select(Course).where(Course.user_id == user_id)
        count_query = select(func.count(Course.id)).where(Course.user_id == user_id)

        if is_completed is not None:
            query = query.where(Course.is_completed == is_completed)
            count_query = count_query.where(Course.is_completed == is_completed)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Course.last_activity_at.desc().nullslast(), Course.created_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        courses = list(result.scalars().all())

        return courses, total

    async def get_all_courses(self, user_id: uuid.UUID) -> list[Course]:
        """Get all courses for a user without pagination."""
        query = (
            select(Course)
            .where(Course.user_id == user_id)
            .order_by(Course.last_activity_at.desc().nullslast())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_course_by_title(
        self,
        user_id: uuid.UUID,
        title: str,
    ) -> Optional[Course]:
        """Get a course by title for a specific user (case-insensitive)."""
        query = select(Course).where(
            Course.user_id == user_id,
            func.lower(Course.title) == func.lower(title),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_course(
        self,
        course: Course,
        **kwargs,
    ) -> Course:
        """Update a course's attributes."""
        for key, value in kwargs.items():
            if value is not None and hasattr(course, key):
                setattr(course, key, value)
        await self.session.flush()
        return course

    async def delete_course(self, course: Course) -> None:
        """Delete a course."""
        await self.session.delete(course)
        await self.session.flush()

    async def get_inactive_courses(
        self,
        user_id: uuid.UUID,
        inactive_days: int = 7,
    ) -> list[Course]:
        """Get courses with no activity in the specified number of days.
        
        Requirement 25.5: Identify courses with no progress in 7 days
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=inactive_days)
        
        query = (
            select(Course)
            .where(
                Course.user_id == user_id,
                Course.is_completed == False,
                (Course.last_activity_at < cutoff_date) | (Course.last_activity_at.is_(None)),
            )
            .order_by(Course.last_activity_at.asc().nullsfirst())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class LearningSessionRepository:
    """Repository for LearningSession operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        course_id: uuid.UUID,
        session_date: date,
        duration_minutes: int,
        notes: Optional[str] = None,
    ) -> LearningSession:
        """Create a learning session.
        
        Requirement 25.2: Log progress updates
        """
        learning_session = LearningSession(
            course_id=course_id,
            session_date=session_date,
            duration_minutes=duration_minutes,
            notes=notes,
        )
        self.session.add(learning_session)
        await self.session.flush()
        return learning_session

    async def get_sessions_for_course(
        self,
        course_id: uuid.UUID,
    ) -> list[LearningSession]:
        """Get all learning sessions for a course."""
        query = (
            select(LearningSession)
            .where(LearningSession.course_id == course_id)
            .order_by(LearningSession.session_date.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_sessions_for_user(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[LearningSession]:
        """Get all learning sessions for a user within a date range."""
        query = (
            select(LearningSession)
            .join(Course)
            .where(Course.user_id == user_id)
        )
        
        if start_date:
            query = query.where(LearningSession.session_date >= start_date)
        if end_date:
            query = query.where(LearningSession.session_date <= end_date)
        
        query = query.order_by(LearningSession.session_date.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_hours_for_user(
        self,
        user_id: uuid.UUID,
    ) -> Decimal:
        """Get total hours invested by a user across all courses.
        
        Requirement 25.3: Calculate total hours invested
        """
        query = (
            select(func.coalesce(func.sum(LearningSession.duration_minutes), 0))
            .join(Course)
            .where(Course.user_id == user_id)
        )
        result = await self.session.execute(query)
        total_minutes = result.scalar() or 0
        return Decimal(str(total_minutes)) / Decimal("60")

    async def get_unique_session_dates(
        self,
        user_id: uuid.UUID,
    ) -> list[date]:
        """Get all unique dates with learning sessions for a user.
        
        Used for calculating learning streak.
        """
        query = (
            select(LearningSession.session_date)
            .join(Course)
            .where(Course.user_id == user_id)
            .distinct()
            .order_by(LearningSession.session_date.desc())
        )
        result = await self.session.execute(query)
        return [row[0] for row in result.all()]

    async def delete_session(self, session: LearningSession) -> None:
        """Delete a learning session."""
        await self.session.delete(session)
        await self.session.flush()
