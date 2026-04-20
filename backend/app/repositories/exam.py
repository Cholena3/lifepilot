"""Repository for exam database operations.

Implements Requirements 3.1-3.8 for exam feed, filtering, and tracking.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam import (
    ApplicationStatus,
    Exam,
    ExamApplication,
    ExamBookmark,
    ExamType,
)


class ExamRepository:
    """Repository for Exam CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_exams_with_deadline_on_date(
        self,
        target_date: date,
    ) -> list[Exam]:
        """Get active exams with registration_end on a specific date.
        
        Validates: Requirements 3.7
        
        Args:
            target_date: The date to check for deadlines
            
        Returns:
            List of exams with registration_end matching target_date
        """
        query = select(Exam).where(
            Exam.is_active == True,
            Exam.registration_end == target_date,
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_exam(
        self,
        name: str,
        organization: str,
        exam_type: ExamType,
        **kwargs,
    ) -> Exam:
        """Create a new exam."""
        exam = Exam(
            name=name,
            organization=organization,
            exam_type=exam_type,
            **kwargs,
        )
        self.session.add(exam)
        await self.session.flush()
        return exam

    async def get_exam_by_id(self, exam_id: uuid.UUID) -> Optional[Exam]:
        """Get an exam by ID."""
        query = select(Exam).where(Exam.id == exam_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_exam_feed(
        self,
        user_id: uuid.UUID,
        exam_type: Optional[ExamType] = None,
        degree: Optional[str] = None,
        branch: Optional[str] = None,
        graduation_year: Optional[int] = None,
        user_cgpa: Optional[Decimal] = None,
        user_backlogs: Optional[int] = None,
        search: Optional[str] = None,
        upcoming_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Exam], int]:
        """Get exam feed with eligibility filtering.
        
        Requirement 3.1: Filter by degree, branch, graduation year
        Requirement 3.2: Apply CGPA filter
        Requirement 3.3: Apply backlog filter
        Requirement 3.4: Filter by exam type
        """
        # Base query for active exams
        query = select(Exam).where(Exam.is_active == True)
        count_query = select(func.count(Exam.id)).where(Exam.is_active == True)

        # Filter by exam type
        if exam_type:
            query = query.where(Exam.exam_type == exam_type)
            count_query = count_query.where(Exam.exam_type == exam_type)

        # Filter by degree eligibility
        # Requirement 3.1: Exams with matching degree or no degree restriction
        if degree:
            degree_filter = or_(
                Exam.eligible_degrees == None,
                Exam.eligible_degrees == [],
                func.jsonb_exists(Exam.eligible_degrees, degree),
            )
            query = query.where(degree_filter)
            count_query = count_query.where(degree_filter)

        # Filter by branch eligibility
        # Requirement 3.1: Exams with matching branch or no branch restriction
        if branch:
            branch_filter = or_(
                Exam.eligible_branches == None,
                Exam.eligible_branches == [],
                func.jsonb_exists(Exam.eligible_branches, branch),
            )
            query = query.where(branch_filter)
            count_query = count_query.where(branch_filter)

        # Filter by graduation year
        # Requirement 3.1: Exams where user's graduation year is within range
        if graduation_year:
            grad_year_filter = and_(
                or_(Exam.graduation_year_min == None, Exam.graduation_year_min <= graduation_year),
                or_(Exam.graduation_year_max == None, Exam.graduation_year_max >= graduation_year),
            )
            query = query.where(grad_year_filter)
            count_query = count_query.where(grad_year_filter)

        # Filter by CGPA eligibility
        # Requirement 3.2: Exclude exams requiring higher CGPA than user's
        if user_cgpa is not None:
            cgpa_filter = or_(
                Exam.min_cgpa == None,
                Exam.min_cgpa <= user_cgpa,
            )
            query = query.where(cgpa_filter)
            count_query = count_query.where(cgpa_filter)

        # Filter by backlog eligibility
        # Requirement 3.3: Exclude exams that don't allow user's backlog count
        if user_backlogs is not None:
            backlog_filter = or_(
                Exam.max_backlogs == None,
                Exam.max_backlogs >= user_backlogs,
            )
            query = query.where(backlog_filter)
            count_query = count_query.where(backlog_filter)

        # Search filter
        if search:
            search_pattern = f"%{search}%"
            search_filter = or_(
                Exam.name.ilike(search_pattern),
                Exam.organization.ilike(search_pattern),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Upcoming only filter
        if upcoming_only:
            today = date.today()
            upcoming_filter = or_(
                Exam.registration_end == None,
                Exam.registration_end >= today,
            )
            query = query.where(upcoming_filter)
            count_query = count_query.where(upcoming_filter)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Exam.registration_end.asc().nullslast(), Exam.name.asc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        exams = list(result.scalars().all())

        return exams, total

    async def get_exams_by_type(
        self,
        user_id: uuid.UUID,
        degree: Optional[str] = None,
        branch: Optional[str] = None,
        graduation_year: Optional[int] = None,
        user_cgpa: Optional[Decimal] = None,
        user_backlogs: Optional[int] = None,
    ) -> dict[ExamType, list[Exam]]:
        """Get exams grouped by type with eligibility filtering.
        
        Requirement 3.4: Categorize exams by type
        """
        # Build base filter conditions
        conditions = [Exam.is_active == True]

        if degree:
            conditions.append(or_(
                Exam.eligible_degrees == None,
                Exam.eligible_degrees == [],
                func.jsonb_exists(Exam.eligible_degrees, degree),
            ))

        if branch:
            conditions.append(or_(
                Exam.eligible_branches == None,
                Exam.eligible_branches == [],
                func.jsonb_exists(Exam.eligible_branches, branch),
            ))

        if graduation_year:
            conditions.append(and_(
                or_(Exam.graduation_year_min == None, Exam.graduation_year_min <= graduation_year),
                or_(Exam.graduation_year_max == None, Exam.graduation_year_max >= graduation_year),
            ))

        if user_cgpa is not None:
            conditions.append(or_(
                Exam.min_cgpa == None,
                Exam.min_cgpa <= user_cgpa,
            ))

        if user_backlogs is not None:
            conditions.append(or_(
                Exam.max_backlogs == None,
                Exam.max_backlogs >= user_backlogs,
            ))

        query = select(Exam).where(and_(*conditions)).order_by(Exam.exam_type, Exam.registration_end.asc().nullslast())
        result = await self.session.execute(query)
        exams = list(result.scalars().all())

        # Group by type
        grouped: dict[ExamType, list[Exam]] = {}
        for exam in exams:
            if exam.exam_type not in grouped:
                grouped[exam.exam_type] = []
            grouped[exam.exam_type].append(exam)

        return grouped

    async def update_exam(self, exam: Exam, **kwargs) -> Exam:
        """Update an exam's attributes."""
        for key, value in kwargs.items():
            if value is not None and hasattr(exam, key):
                setattr(exam, key, value)
        await self.session.flush()
        return exam

    async def delete_exam(self, exam: Exam) -> None:
        """Delete an exam."""
        await self.session.delete(exam)
        await self.session.flush()


class ExamBookmarkRepository:
    """Repository for ExamBookmark operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bookmark(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> ExamBookmark:
        """Create a new exam bookmark.
        
        Requirement 3.5: Add exam to user's saved exams list
        """
        bookmark = ExamBookmark(
            user_id=user_id,
            exam_id=exam_id,
        )
        self.session.add(bookmark)
        await self.session.flush()
        return bookmark

    async def get_bookmark(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> Optional[ExamBookmark]:
        """Get a bookmark by user and exam ID."""
        query = select(ExamBookmark).where(
            ExamBookmark.user_id == user_id,
            ExamBookmark.exam_id == exam_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_bookmarks(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExamBookmark], int]:
        """Get all bookmarks for a user with pagination."""
        query = (
            select(ExamBookmark)
            .options(selectinload(ExamBookmark.exam))
            .where(ExamBookmark.user_id == user_id)
        )
        count_query = select(func.count(ExamBookmark.id)).where(
            ExamBookmark.user_id == user_id
        )

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(ExamBookmark.created_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        bookmarks = list(result.scalars().all())

        return bookmarks, total

    async def delete_bookmark(self, bookmark: ExamBookmark) -> None:
        """Delete a bookmark."""
        await self.session.delete(bookmark)
        await self.session.flush()

    async def is_bookmarked(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> bool:
        """Check if an exam is bookmarked by a user."""
        bookmark = await self.get_bookmark(user_id, exam_id)
        return bookmark is not None

    async def get_users_who_bookmarked_exam(
        self,
        exam_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """Get all user IDs who have bookmarked a specific exam.
        
        Validates: Requirements 3.7
        
        Args:
            exam_id: UUID of the exam
            
        Returns:
            List of user UUIDs who bookmarked the exam
        """
        query = select(ExamBookmark.user_id).where(
            ExamBookmark.exam_id == exam_id
        )
        result = await self.session.execute(query)
        return [row[0] for row in result.fetchall()]


class ExamApplicationRepository:
    """Repository for ExamApplication operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_application(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
        applied_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> ExamApplication:
        """Create a new exam application.
        
        Requirement 3.6: Record application date and update status
        """
        application = ExamApplication(
            user_id=user_id,
            exam_id=exam_id,
            applied_date=applied_date or date.today(),
            notes=notes,
            status=ApplicationStatus.APPLIED,
        )
        self.session.add(application)
        await self.session.flush()
        return application

    async def get_application(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> Optional[ExamApplication]:
        """Get an application by user and exam ID."""
        query = select(ExamApplication).where(
            ExamApplication.user_id == user_id,
            ExamApplication.exam_id == exam_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_application_by_id(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ExamApplication]:
        """Get an application by ID for a specific user."""
        query = select(ExamApplication).where(
            ExamApplication.id == application_id,
            ExamApplication.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_applications(
        self,
        user_id: uuid.UUID,
        status: Optional[ApplicationStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExamApplication], int]:
        """Get all applications for a user with pagination."""
        query = (
            select(ExamApplication)
            .options(selectinload(ExamApplication.exam))
            .where(ExamApplication.user_id == user_id)
        )
        count_query = select(func.count(ExamApplication.id)).where(
            ExamApplication.user_id == user_id
        )

        if status:
            query = query.where(ExamApplication.status == status)
            count_query = count_query.where(ExamApplication.status == status)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(ExamApplication.applied_date.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        applications = list(result.scalars().all())

        return applications, total

    async def update_application(
        self,
        application: ExamApplication,
        **kwargs,
    ) -> ExamApplication:
        """Update an application's attributes."""
        for key, value in kwargs.items():
            if value is not None and hasattr(application, key):
                setattr(application, key, value)
        await self.session.flush()
        return application

    async def delete_application(self, application: ExamApplication) -> None:
        """Delete an application."""
        await self.session.delete(application)
        await self.session.flush()

    async def is_applied(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> bool:
        """Check if a user has applied to an exam."""
        application = await self.get_application(user_id, exam_id)
        return application is not None
