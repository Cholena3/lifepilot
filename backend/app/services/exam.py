"""Service for exam feed and discovery.

Implements Requirements 3.1-3.8 for exam feed, filtering, and tracking.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import (
    ApplicationStatus,
    Exam,
    ExamApplication,
    ExamBookmark,
    ExamType,
)
from app.repositories.exam import (
    ExamApplicationRepository,
    ExamBookmarkRepository,
    ExamRepository,
)
from app.schemas.exam import (
    ExamApplicationCreate,
    ExamApplicationResponse,
    ExamApplicationUpdate,
    ExamBookmarkResponse,
    ExamCreate,
    ExamDetailResponse,
    ExamFeedGroupedResponse,
    ExamFeedResponse,
    ExamFilters,
    ExamResponse,
    ExamsByTypeResponse,
    ExamUpdate,
)


class ExamService:
    """Service for exam feed and discovery.
    
    Implements Requirements 3.1-3.8 for exam feed, filtering, and tracking.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.exam_repo = ExamRepository(session)
        self.bookmark_repo = ExamBookmarkRepository(session)
        self.application_repo = ExamApplicationRepository(session)

    # ========================================================================
    # Exam Feed Methods
    # ========================================================================

    async def get_exam_feed(
        self,
        user_id: uuid.UUID,
        filters: ExamFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> ExamFeedResponse:
        """Get exam feed with eligibility filtering.
        
        Requirement 3.1: Filter by degree, branch, graduation year
        Requirement 3.2: Apply CGPA filter
        Requirement 3.3: Apply backlog filter
        Requirement 3.4: Filter by exam type
        """
        exams, total = await self.exam_repo.get_exam_feed(
            user_id=user_id,
            exam_type=filters.exam_type,
            degree=filters.degree,
            branch=filters.branch,
            graduation_year=filters.graduation_year,
            user_cgpa=filters.min_cgpa,
            user_backlogs=filters.backlogs,
            search=filters.search,
            upcoming_only=filters.upcoming_only,
            page=page,
            page_size=page_size,
        )

        items = [ExamResponse.model_validate(exam) for exam in exams]
        return ExamFeedResponse.create(items, total, page, page_size)

    async def get_exam_feed_for_user_profile(
        self,
        user_id: uuid.UUID,
        degree: Optional[str] = None,
        branch: Optional[str] = None,
        graduation_year: Optional[int] = None,
        cgpa: Optional[Decimal] = None,
        backlogs: Optional[int] = None,
        exam_type: Optional[ExamType] = None,
        search: Optional[str] = None,
        upcoming_only: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> ExamFeedResponse:
        """Get exam feed filtered by user's student profile.
        
        This method is designed to be called with the user's profile data
        to automatically filter exams based on eligibility.
        """
        filters = ExamFilters(
            exam_type=exam_type,
            degree=degree,
            branch=branch,
            graduation_year=graduation_year,
            min_cgpa=cgpa,
            backlogs=backlogs,
            search=search,
            upcoming_only=upcoming_only,
        )
        return await self.get_exam_feed(user_id, filters, page, page_size)

    async def get_exams_grouped_by_type(
        self,
        user_id: uuid.UUID,
        degree: Optional[str] = None,
        branch: Optional[str] = None,
        graduation_year: Optional[int] = None,
        cgpa: Optional[Decimal] = None,
        backlogs: Optional[int] = None,
    ) -> ExamFeedGroupedResponse:
        """Get exams grouped by type with eligibility filtering.
        
        Requirement 3.4: Categorize exams by type
        """
        grouped = await self.exam_repo.get_exams_by_type(
            user_id=user_id,
            degree=degree,
            branch=branch,
            graduation_year=graduation_year,
            user_cgpa=cgpa,
            user_backlogs=backlogs,
        )

        groups = []
        total_exams = 0
        for exam_type, exams in grouped.items():
            exam_responses = [ExamResponse.model_validate(exam) for exam in exams]
            groups.append(ExamsByTypeResponse(
                exam_type=exam_type,
                exams=exam_responses,
                count=len(exam_responses),
            ))
            total_exams += len(exam_responses)

        # Sort groups by exam type value
        groups.sort(key=lambda g: g.exam_type.value)

        return ExamFeedGroupedResponse(
            groups=groups,
            total_exams=total_exams,
        )

    # ========================================================================
    # Exam Detail Methods
    # ========================================================================

    async def get_exam_details(
        self,
        exam_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ExamDetailResponse]:
        """Get detailed exam information.
        
        Requirement 3.8: Return syllabus, cutoffs, previous papers, and resource links
        """
        exam = await self.exam_repo.get_exam_by_id(exam_id)
        if not exam:
            return None

        # Check bookmark and application status
        is_bookmarked = await self.bookmark_repo.is_bookmarked(user_id, exam_id)
        application = await self.application_repo.get_application(user_id, exam_id)

        return ExamDetailResponse(
            id=exam.id,
            name=exam.name,
            organization=exam.organization,
            exam_type=exam.exam_type,
            description=exam.description,
            registration_start=exam.registration_start,
            registration_end=exam.registration_end,
            exam_date=exam.exam_date,
            min_cgpa=exam.min_cgpa,
            max_backlogs=exam.max_backlogs,
            eligible_degrees=exam.eligible_degrees,
            eligible_branches=exam.eligible_branches,
            graduation_year_min=exam.graduation_year_min,
            graduation_year_max=exam.graduation_year_max,
            syllabus=exam.syllabus,
            cutoffs=exam.cutoffs,
            resources=exam.resources,
            source_url=exam.source_url,
            is_active=exam.is_active,
            created_at=exam.created_at,
            updated_at=exam.updated_at,
            is_bookmarked=is_bookmarked,
            is_applied=application is not None,
            application_status=application.status if application else None,
        )

    # ========================================================================
    # Exam CRUD Methods (Admin/Scraper)
    # ========================================================================

    async def create_exam(self, data: ExamCreate) -> Exam:
        """Create a new exam (admin/scraper use)."""
        exam = await self.exam_repo.create_exam(
            name=data.name,
            organization=data.organization,
            exam_type=data.exam_type,
            description=data.description,
            registration_start=data.registration_start,
            registration_end=data.registration_end,
            exam_date=data.exam_date,
            min_cgpa=data.min_cgpa,
            max_backlogs=data.max_backlogs,
            eligible_degrees=data.eligible_degrees,
            eligible_branches=data.eligible_branches,
            graduation_year_min=data.graduation_year_min,
            graduation_year_max=data.graduation_year_max,
            syllabus=data.syllabus,
            cutoffs=data.cutoffs,
            resources=data.resources,
            source_url=data.source_url,
        )
        return exam

    async def update_exam(
        self,
        exam_id: uuid.UUID,
        data: ExamUpdate,
    ) -> Optional[Exam]:
        """Update an exam."""
        exam = await self.exam_repo.get_exam_by_id(exam_id)
        if not exam:
            return None

        update_data = data.model_dump(exclude_unset=True)
        exam = await self.exam_repo.update_exam(exam, **update_data)
        return exam

    async def delete_exam(self, exam_id: uuid.UUID) -> bool:
        """Delete an exam."""
        exam = await self.exam_repo.get_exam_by_id(exam_id)
        if not exam:
            return False
        await self.exam_repo.delete_exam(exam)
        return True

    # ========================================================================
    # Bookmark Methods
    # ========================================================================

    async def bookmark_exam(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> ExamBookmark:
        """Bookmark an exam.
        
        Requirement 3.5: Add exam to user's saved exams list
        
        Raises:
            ValueError: If exam doesn't exist or already bookmarked
        """
        # Check if exam exists
        exam = await self.exam_repo.get_exam_by_id(exam_id)
        if not exam:
            raise ValueError("Exam not found")

        # Check if already bookmarked
        existing = await self.bookmark_repo.get_bookmark(user_id, exam_id)
        if existing:
            raise ValueError("Exam already bookmarked")

        bookmark = await self.bookmark_repo.create_bookmark(user_id, exam_id)
        return bookmark

    async def remove_bookmark(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> bool:
        """Remove an exam bookmark."""
        bookmark = await self.bookmark_repo.get_bookmark(user_id, exam_id)
        if not bookmark:
            return False
        await self.bookmark_repo.delete_bookmark(bookmark)
        return True

    async def get_user_bookmarks(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExamBookmarkResponse], int]:
        """Get user's bookmarked exams."""
        bookmarks, total = await self.bookmark_repo.get_user_bookmarks(
            user_id, page, page_size
        )
        
        responses = []
        for bookmark in bookmarks:
            response = ExamBookmarkResponse(
                id=bookmark.id,
                user_id=bookmark.user_id,
                exam_id=bookmark.exam_id,
                created_at=bookmark.created_at,
                exam=ExamResponse.model_validate(bookmark.exam) if bookmark.exam else None,
            )
            responses.append(response)
        
        return responses, total

    # ========================================================================
    # Application Methods
    # ========================================================================

    async def mark_applied(
        self,
        user_id: uuid.UUID,
        data: ExamApplicationCreate,
    ) -> ExamApplication:
        """Mark an exam as applied.
        
        Requirement 3.6: Record application date and update status
        
        Raises:
            ValueError: If exam doesn't exist or already applied
        """
        # Check if exam exists
        exam = await self.exam_repo.get_exam_by_id(data.exam_id)
        if not exam:
            raise ValueError("Exam not found")

        # Check if already applied
        existing = await self.application_repo.get_application(user_id, data.exam_id)
        if existing:
            raise ValueError("Already applied to this exam")

        application = await self.application_repo.create_application(
            user_id=user_id,
            exam_id=data.exam_id,
            applied_date=data.applied_date,
            notes=data.notes,
        )
        return application

    async def update_application(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: ExamApplicationUpdate,
    ) -> Optional[ExamApplication]:
        """Update an exam application."""
        application = await self.application_repo.get_application_by_id(
            application_id, user_id
        )
        if not application:
            return None

        update_data = data.model_dump(exclude_unset=True)
        application = await self.application_repo.update_application(
            application, **update_data
        )
        return application

    async def get_user_applications(
        self,
        user_id: uuid.UUID,
        status: Optional[ApplicationStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExamApplicationResponse], int]:
        """Get user's exam applications."""
        applications, total = await self.application_repo.get_user_applications(
            user_id, status, page, page_size
        )
        
        responses = []
        for app in applications:
            response = ExamApplicationResponse(
                id=app.id,
                user_id=app.user_id,
                exam_id=app.exam_id,
                status=app.status,
                applied_date=app.applied_date,
                notes=app.notes,
                created_at=app.created_at,
                updated_at=app.updated_at,
                exam=ExamResponse.model_validate(app.exam) if app.exam else None,
            )
            responses.append(response)
        
        return responses, total

    async def delete_application(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> bool:
        """Delete an exam application."""
        application = await self.application_repo.get_application_by_id(
            application_id, user_id
        )
        if not application:
            return False
        await self.application_repo.delete_application(application)
        return True
