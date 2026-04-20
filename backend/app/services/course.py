"""Service for learning progress tracking.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, LearningSession
from app.models.notification import NotificationChannel
from app.repositories.course import CourseRepository, LearningSessionRepository
from app.schemas.course import (
    CourseCreate,
    CourseProgressUpdate,
    CourseResponse,
    CourseUpdate,
    CourseWithSessionsResponse,
    InactiveCourseResponse,
    LearningSessionCreate,
    LearningSessionResponse,
    LearningStatsResponse,
    PaginatedCourseResponse,
)
from app.services.notification import NotificationService


class CourseService:
    """Service for learning progress tracking.
    
    Implements Requirements 25.1-25.5 for course tracking and reminders.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.course_repo = CourseRepository(session)
        self.session_repo = LearningSessionRepository(session)

    async def add_course(
        self,
        user_id: uuid.UUID,
        data: CourseCreate,
    ) -> Course:
        """Add a new course for a user.
        
        Requirement 25.1: Store course name, platform, URL, and total duration
        
        Raises:
            ValueError: If course with same title already exists
        """
        # Check for duplicate course title
        existing = await self.course_repo.get_course_by_title(user_id, data.title)
        if existing:
            raise ValueError(f"Course '{data.title}' already exists")

        course = await self.course_repo.create_course(
            user_id=user_id,
            title=data.title,
            platform=data.platform,
            url=data.url,
            total_hours=data.total_hours,
        )
        return course

    async def get_course(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Course]:
        """Get a course by ID."""
        return await self.course_repo.get_course_by_id(course_id, user_id)

    async def get_course_with_sessions(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CourseWithSessionsResponse]:
        """Get a course with its learning sessions."""
        course = await self.course_repo.get_course_with_sessions(course_id, user_id)
        if not course:
            return None
        return CourseWithSessionsResponse.model_validate(course)

    async def get_courses(
        self,
        user_id: uuid.UUID,
        is_completed: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedCourseResponse:
        """Get courses for a user with optional filtering."""
        courses, total = await self.course_repo.get_courses(
            user_id=user_id,
            is_completed=is_completed,
            page=page,
            page_size=page_size,
        )
        
        items = [CourseResponse.model_validate(c) for c in courses]
        return PaginatedCourseResponse.create(items, total, page, page_size)

    async def update_course(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        data: CourseUpdate,
    ) -> Optional[Course]:
        """Update a course."""
        course = await self.course_repo.get_course_by_id(course_id, user_id)
        if not course:
            return None

        # Check for duplicate title if title is being updated
        if data.title and data.title.lower() != course.title.lower():
            existing = await self.course_repo.get_course_by_title(user_id, data.title)
            if existing:
                raise ValueError(f"Course '{data.title}' already exists")

        # Update course
        update_data = data.model_dump(exclude_unset=True)
        
        # Recalculate completion percentage if total_hours changed
        if "total_hours" in update_data and update_data["total_hours"] is not None:
            new_total = update_data["total_hours"]
            if new_total > 0:
                completion = int((course.completed_hours / new_total) * 100)
                update_data["completion_percentage"] = min(completion, 100)
            else:
                update_data["completion_percentage"] = 0
        
        course = await self.course_repo.update_course(course, **update_data)
        return course

    async def delete_course(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a course."""
        course = await self.course_repo.get_course_by_id(course_id, user_id)
        if not course:
            return False
        await self.course_repo.delete_course(course)
        return True

    async def log_learning_session(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        data: LearningSessionCreate,
    ) -> tuple[LearningSession, Course]:
        """Log a learning session and update course progress.
        
        Requirement 25.2: Log progress and update completion percentage
        
        Returns:
            Tuple of (LearningSession, updated Course)
        """
        course = await self.course_repo.get_course_by_id(course_id, user_id)
        if not course:
            raise ValueError("Course not found")

        # Create learning session
        session = await self.session_repo.create_session(
            course_id=course_id,
            session_date=data.session_date,
            duration_minutes=data.duration_minutes,
            notes=data.notes,
        )

        # Update course progress
        hours_added = Decimal(str(data.duration_minutes)) / Decimal("60")
        new_completed_hours = course.completed_hours + hours_added
        
        # Calculate new completion percentage
        if course.total_hours > 0:
            completion = int((new_completed_hours / course.total_hours) * 100)
            completion = min(completion, 100)
        else:
            completion = 0

        # Update course
        now = datetime.now(timezone.utc)
        await self.course_repo.update_course(
            course,
            completed_hours=new_completed_hours,
            completion_percentage=completion,
            last_activity_at=now,
        )

        return session, course

    async def update_progress(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        data: CourseProgressUpdate,
    ) -> Optional[Course]:
        """Update course completion percentage directly.
        
        Requirement 25.2: Update completion percentage
        """
        course = await self.course_repo.get_course_by_id(course_id, user_id)
        if not course:
            return None

        # Calculate completed hours based on percentage
        if course.total_hours > 0:
            completed_hours = (Decimal(str(data.completion_percentage)) / Decimal("100")) * course.total_hours
        else:
            completed_hours = Decimal("0")

        now = datetime.now(timezone.utc)
        await self.course_repo.update_course(
            course,
            completion_percentage=data.completion_percentage,
            completed_hours=completed_hours,
            last_activity_at=now,
        )

        return course

    async def mark_course_complete(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Course]:
        """Mark a course as complete.
        
        Requirement 25.4: Mark course complete and prompt for skill update
        
        Returns:
            Updated course or None if not found
        """
        course = await self.course_repo.get_course_by_id(course_id, user_id)
        if not course:
            return None

        now = datetime.now(timezone.utc)
        await self.course_repo.update_course(
            course,
            is_completed=True,
            completion_percentage=100,
            completed_hours=course.total_hours,
            last_activity_at=now,
        )

        return course

    async def get_learning_stats(
        self,
        user_id: uuid.UUID,
    ) -> LearningStatsResponse:
        """Get learning statistics for a user.
        
        Requirement 25.3: Display learning streak and total hours invested
        """
        courses = await self.course_repo.get_all_courses(user_id)
        
        total_courses = len(courses)
        completed_courses = sum(1 for c in courses if c.is_completed)
        in_progress_courses = total_courses - completed_courses
        
        # Get total hours invested
        total_hours = await self.session_repo.get_total_hours_for_user(user_id)
        
        # Calculate learning streak
        session_dates = await self.session_repo.get_unique_session_dates(user_id)
        current_streak, longest_streak = self._calculate_streaks(session_dates)
        
        return LearningStatsResponse(
            total_courses=total_courses,
            completed_courses=completed_courses,
            in_progress_courses=in_progress_courses,
            total_hours_invested=total_hours,
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
        )

    def _calculate_streaks(self, session_dates: list[date]) -> tuple[int, int]:
        """Calculate current and longest learning streaks.
        
        Requirement 25.3: Calculate learning streak (consecutive days with activity)
        """
        if not session_dates:
            return 0, 0

        today = date.today()
        dates_set = set(session_dates)
        
        # Calculate current streak
        current_streak = 0
        check_date = today
        
        # Allow for today or yesterday to start the streak
        if check_date not in dates_set:
            check_date = today - timedelta(days=1)
        
        while check_date in dates_set:
            current_streak += 1
            check_date -= timedelta(days=1)
        
        # Calculate longest streak
        sorted_dates = sorted(dates_set)
        longest_streak = 0
        current_run = 1
        
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current_run += 1
            else:
                longest_streak = max(longest_streak, current_run)
                current_run = 1
        
        longest_streak = max(longest_streak, current_run)
        
        return current_streak, longest_streak

    async def get_inactive_courses(
        self,
        user_id: uuid.UUID,
        inactive_days: int = 7,
    ) -> list[InactiveCourseResponse]:
        """Get courses with no activity in the specified number of days.
        
        Requirement 25.5: Identify courses with no progress in 7 days
        """
        courses = await self.course_repo.get_inactive_courses(user_id, inactive_days)
        now = datetime.now(timezone.utc)
        
        result = []
        for course in courses:
            if course.last_activity_at:
                days_inactive = (now - course.last_activity_at).days
            else:
                days_inactive = (now.date() - course.created_at.date()).days
            
            result.append(InactiveCourseResponse(
                course_id=course.id,
                title=course.title,
                platform=course.platform,
                days_inactive=days_inactive,
                last_activity_at=course.last_activity_at,
                completion_percentage=course.completion_percentage,
            ))
        
        return result

    async def send_inactive_course_reminders(
        self,
        user_id: uuid.UUID,
        inactive_days: int = 7,
    ) -> int:
        """Send reminders for inactive courses.
        
        Requirement 25.5: Send reminders for courses with no progress in 7 days
        
        Returns:
            Number of reminders sent
        """
        inactive_courses = await self.get_inactive_courses(user_id, inactive_days)
        
        if not inactive_courses:
            return 0

        notification_service = NotificationService(self.session)
        reminders_sent = 0

        for course in inactive_courses:
            title = "Course Reminder"
            body = (
                f"You haven't made progress on '{course.title}' in {course.days_inactive} days. "
                f"Current progress: {course.completion_percentage}%. Keep learning!"
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
