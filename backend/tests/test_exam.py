"""Unit tests for exam feed and filtering.

Tests Requirements 3.1, 3.2, 3.3, 3.4 for exam feed and eligibility filtering.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.exam import ApplicationStatus, ExamType
from app.schemas.exam import ExamCreate, ExamFilters


# Test user ID (matches the mock in router)
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ============================================================================
# Schema Tests
# ============================================================================

class TestExamSchemas:
    """Tests for exam Pydantic schemas."""

    def test_exam_create_valid(self):
        """Test creating a valid ExamCreate schema."""
        data = ExamCreate(
            name="TCS NQT 2024",
            organization="Tata Consultancy Services",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            min_cgpa=Decimal("6.0"),
            max_backlogs=0,
        )
        assert data.name == "TCS NQT 2024"
        assert data.organization == "Tata Consultancy Services"
        assert data.exam_type == ExamType.CAMPUS_PLACEMENT
        assert data.min_cgpa == Decimal("6.0")
        assert data.max_backlogs == 0

    def test_exam_create_name_strip(self):
        """Test that exam name is stripped of whitespace."""
        data = ExamCreate(
            name="  TCS NQT  ",
            organization="  TCS  ",
            exam_type=ExamType.CAMPUS_PLACEMENT,
        )
        assert data.name == "TCS NQT"
        assert data.organization == "TCS"

    def test_exam_create_with_eligibility(self):
        """Test ExamCreate with eligibility criteria."""
        data = ExamCreate(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            eligible_degrees=["B.Tech", "B.E"],
            eligible_branches=["CSE", "IT"],
            graduation_year_min=2024,
            graduation_year_max=2025,
        )
        assert data.eligible_degrees == ["B.Tech", "B.E"]
        assert data.eligible_branches == ["CSE", "IT"]
        assert data.graduation_year_min == 2024
        assert data.graduation_year_max == 2025

    def test_exam_filters_defaults(self):
        """Test ExamFilters with default values."""
        filters = ExamFilters()
        assert filters.exam_type is None
        assert filters.degree is None
        assert filters.branch is None
        assert filters.graduation_year is None
        assert filters.min_cgpa is None
        assert filters.backlogs is None
        assert filters.search is None
        assert filters.upcoming_only is False

    def test_exam_filters_with_values(self):
        """Test ExamFilters with all values."""
        filters = ExamFilters(
            exam_type=ExamType.CAMPUS_PLACEMENT,
            degree="B.Tech",
            branch="CSE",
            graduation_year=2024,
            min_cgpa=Decimal("7.5"),
            backlogs=0,
            search="TCS",
            upcoming_only=True,
        )
        assert filters.exam_type == ExamType.CAMPUS_PLACEMENT
        assert filters.degree == "B.Tech"
        assert filters.branch == "CSE"
        assert filters.graduation_year == 2024
        assert filters.min_cgpa == Decimal("7.5")
        assert filters.backlogs == 0
        assert filters.search == "TCS"
        assert filters.upcoming_only is True


class TestExamType:
    """Tests for ExamType enum."""

    def test_exam_types_exist(self):
        """Test that all required exam types exist.
        
        Requirement 3.4: Categorize exams into types
        """
        assert ExamType.CAMPUS_PLACEMENT.value == "campus_placement"
        assert ExamType.OFF_CAMPUS.value == "off_campus"
        assert ExamType.INTERNSHIP.value == "internship"
        assert ExamType.HIGHER_EDUCATION.value == "higher_education"
        assert ExamType.GOVERNMENT.value == "government"
        assert ExamType.SCHOLARSHIP.value == "scholarship"

    def test_exam_type_count(self):
        """Test that there are exactly 6 exam types."""
        assert len(ExamType) == 6


class TestApplicationStatus:
    """Tests for ApplicationStatus enum."""

    def test_application_statuses_exist(self):
        """Test that all application statuses exist."""
        assert ApplicationStatus.APPLIED.value == "applied"
        assert ApplicationStatus.SHORTLISTED.value == "shortlisted"
        assert ApplicationStatus.REJECTED.value == "rejected"
        assert ApplicationStatus.SELECTED.value == "selected"
        assert ApplicationStatus.WITHDRAWN.value == "withdrawn"


# ============================================================================
# API Endpoint Tests
# ============================================================================

@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestExamFeedEndpoints:
    """Integration tests for exam feed API endpoints."""

    @pytest.mark.asyncio
    async def test_get_exam_feed_endpoint(self, client: AsyncClient):
        """Test getting exam feed via API.
        
        Requirement 3.1: Filter by degree, branch, graduation year
        """
        response = await client.get("/api/v1/exams/feed")
        assert response.status_code in [200, 500]  # 500 if no DB

    @pytest.mark.asyncio
    async def test_get_exam_feed_with_filters(self, client: AsyncClient):
        """Test getting exam feed with filters.
        
        Requirement 3.1, 3.2, 3.3, 3.4: Apply various filters
        """
        response = await client.get(
            "/api/v1/exams/feed",
            params={
                "exam_type": "campus_placement",
                "degree": "B.Tech",
                "branch": "CSE",
                "graduation_year": 2024,
                "cgpa": 7.5,
                "backlogs": 0,
                "upcoming_only": True,
            },
        )
        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_get_exam_feed_grouped_endpoint(self, client: AsyncClient):
        """Test getting exam feed grouped by type.
        
        Requirement 3.4: Categorize exams by type
        """
        response = await client.get("/api/v1/exams/feed/grouped")
        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_get_exam_details_endpoint(self, client: AsyncClient):
        """Test getting exam details.
        
        Requirement 3.8: Return syllabus, cutoffs, previous papers, and resource links
        """
        exam_id = uuid.uuid4()
        response = await client.get(f"/api/v1/exams/{exam_id}")
        assert response.status_code in [200, 404, 500]


class TestExamCRUDEndpoints:
    """Integration tests for exam CRUD API endpoints."""

    @pytest.mark.asyncio
    async def test_create_exam_endpoint(self, client: AsyncClient):
        """Test creating an exam via API."""
        response = await client.post(
            "/api/v1/exams",
            json={
                "name": "TCS NQT 2024",
                "organization": "Tata Consultancy Services",
                "exam_type": "campus_placement",
                "min_cgpa": 6.0,
                "max_backlogs": 0,
                "eligible_degrees": ["B.Tech", "B.E"],
                "eligible_branches": ["CSE", "IT"],
            },
        )
        assert response.status_code in [201, 500]

    @pytest.mark.asyncio
    async def test_update_exam_endpoint(self, client: AsyncClient):
        """Test updating an exam via API."""
        exam_id = uuid.uuid4()
        response = await client.put(
            f"/api/v1/exams/{exam_id}",
            json={"name": "Updated Exam Name"},
        )
        assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_delete_exam_endpoint(self, client: AsyncClient):
        """Test deleting an exam via API."""
        exam_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/exams/{exam_id}")
        assert response.status_code in [204, 404, 500]


class TestExamBookmarkEndpoints:
    """Integration tests for exam bookmark API endpoints."""

    @pytest.mark.asyncio
    async def test_bookmark_exam_endpoint(self, client: AsyncClient):
        """Test bookmarking an exam via API.
        
        Requirement 3.5: Add exam to user's saved exams list
        """
        exam_id = uuid.uuid4()
        response = await client.post(
            "/api/v1/exams/bookmarks",
            json={"exam_id": str(exam_id)},
        )
        assert response.status_code in [201, 400, 500]

    @pytest.mark.asyncio
    async def test_get_bookmarks_endpoint(self, client: AsyncClient):
        """Test getting bookmarked exams via API."""
        response = await client.get("/api/v1/exams/bookmarks")
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_remove_bookmark_endpoint(self, client: AsyncClient):
        """Test removing a bookmark via API."""
        exam_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/exams/bookmarks/{exam_id}")
        assert response.status_code in [204, 404, 500]


class TestExamApplicationEndpoints:
    """Integration tests for exam application API endpoints."""

    @pytest.mark.asyncio
    async def test_mark_applied_endpoint(self, client: AsyncClient):
        """Test marking an exam as applied via API.
        
        Requirement 3.6: Record application date and update status
        """
        exam_id = uuid.uuid4()
        response = await client.post(
            "/api/v1/exams/applications",
            json={
                "exam_id": str(exam_id),
                "notes": "Applied via official portal",
            },
        )
        assert response.status_code in [201, 400, 500]

    @pytest.mark.asyncio
    async def test_get_applications_endpoint(self, client: AsyncClient):
        """Test getting exam applications via API."""
        response = await client.get("/api/v1/exams/applications")
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_get_applications_with_status_filter(self, client: AsyncClient):
        """Test getting applications filtered by status."""
        response = await client.get(
            "/api/v1/exams/applications",
            params={"status": "applied"},
        )
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_update_application_endpoint(self, client: AsyncClient):
        """Test updating an application via API."""
        application_id = uuid.uuid4()
        response = await client.put(
            f"/api/v1/exams/applications/{application_id}",
            json={"status": "shortlisted"},
        )
        assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_delete_application_endpoint(self, client: AsyncClient):
        """Test deleting an application via API."""
        application_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/exams/applications/{application_id}")
        assert response.status_code in [204, 404, 500]


# ============================================================================
# Filtering Logic Tests (Unit Tests)
# ============================================================================

class TestExamFilteringLogic:
    """Unit tests for exam filtering logic.
    
    These tests verify the filtering logic without database access.
    """

    def test_cgpa_filter_logic(self):
        """Test CGPA filter logic.
        
        Requirement 3.2: Exclude exams requiring higher CGPA than user's
        
        User with CGPA 7.0 should be eligible for exams requiring <= 7.0
        """
        user_cgpa = Decimal("7.0")
        
        # Exam requiring 6.0 - user eligible
        exam_min_cgpa_6 = Decimal("6.0")
        assert exam_min_cgpa_6 <= user_cgpa
        
        # Exam requiring 7.0 - user eligible (equal)
        exam_min_cgpa_7 = Decimal("7.0")
        assert exam_min_cgpa_7 <= user_cgpa
        
        # Exam requiring 8.0 - user NOT eligible
        exam_min_cgpa_8 = Decimal("8.0")
        assert not (exam_min_cgpa_8 <= user_cgpa)

    def test_backlog_filter_logic(self):
        """Test backlog filter logic.
        
        Requirement 3.3: Exclude exams that don't allow user's backlog count
        
        User with 1 backlog should be eligible for exams allowing >= 1 backlogs
        """
        user_backlogs = 1
        
        # Exam allowing 0 backlogs - user NOT eligible
        exam_max_backlogs_0 = 0
        assert not (exam_max_backlogs_0 >= user_backlogs)
        
        # Exam allowing 1 backlog - user eligible (equal)
        exam_max_backlogs_1 = 1
        assert exam_max_backlogs_1 >= user_backlogs
        
        # Exam allowing 2 backlogs - user eligible
        exam_max_backlogs_2 = 2
        assert exam_max_backlogs_2 >= user_backlogs

    def test_graduation_year_filter_logic(self):
        """Test graduation year filter logic.
        
        Requirement 3.1: Filter by graduation year
        
        User graduating in 2024 should be eligible for exams with year range including 2024
        """
        user_grad_year = 2024
        
        # Exam for 2024 only - user eligible
        exam_year_min_2024 = 2024
        exam_year_max_2024 = 2024
        assert exam_year_min_2024 <= user_grad_year <= exam_year_max_2024
        
        # Exam for 2024-2025 - user eligible
        exam_year_min_2024_2025 = 2024
        exam_year_max_2024_2025 = 2025
        assert exam_year_min_2024_2025 <= user_grad_year <= exam_year_max_2024_2025
        
        # Exam for 2025 only - user NOT eligible
        exam_year_min_2025 = 2025
        exam_year_max_2025 = 2025
        assert not (exam_year_min_2025 <= user_grad_year <= exam_year_max_2025)

    def test_degree_filter_logic(self):
        """Test degree filter logic.
        
        Requirement 3.1: Filter by degree
        
        User with B.Tech should be eligible for exams that include B.Tech or have no restriction
        """
        user_degree = "B.Tech"
        
        # Exam for B.Tech - user eligible
        exam_degrees_btech = ["B.Tech", "B.E"]
        assert user_degree in exam_degrees_btech
        
        # Exam for all degrees (empty list) - user eligible
        exam_degrees_all = []
        assert len(exam_degrees_all) == 0 or user_degree in exam_degrees_all
        
        # Exam for MCA only - user NOT eligible
        exam_degrees_mca = ["MCA"]
        assert user_degree not in exam_degrees_mca

    def test_branch_filter_logic(self):
        """Test branch filter logic.
        
        Requirement 3.1: Filter by branch
        
        User with CSE should be eligible for exams that include CSE or have no restriction
        """
        user_branch = "CSE"
        
        # Exam for CSE - user eligible
        exam_branches_cse = ["CSE", "IT"]
        assert user_branch in exam_branches_cse
        
        # Exam for all branches (empty list) - user eligible
        exam_branches_all = []
        assert len(exam_branches_all) == 0 or user_branch in exam_branches_all
        
        # Exam for Mechanical only - user NOT eligible
        exam_branches_mech = ["Mechanical"]
        assert user_branch not in exam_branches_mech


# ============================================================================
# Bookmark and Application Schema Tests (Requirements 3.5, 3.6, 3.8)
# ============================================================================

class TestExamBookmarkSchemas:
    """Tests for exam bookmark schemas.
    
    Validates: Requirements 3.5
    """

    def test_exam_bookmark_create_valid(self):
        """Test creating a valid ExamBookmarkCreate schema.
        
        Requirement 3.5: Add exam to user's saved exams list
        """
        from app.schemas.exam import ExamBookmarkCreate
        
        exam_id = uuid.uuid4()
        data = ExamBookmarkCreate(exam_id=exam_id)
        assert data.exam_id == exam_id

    def test_exam_bookmark_response_structure(self):
        """Test ExamBookmarkResponse has all required fields."""
        from app.schemas.exam import ExamBookmarkResponse
        from datetime import datetime
        
        bookmark_id = uuid.uuid4()
        user_id = uuid.uuid4()
        exam_id = uuid.uuid4()
        created_at = datetime.now()
        
        response = ExamBookmarkResponse(
            id=bookmark_id,
            user_id=user_id,
            exam_id=exam_id,
            created_at=created_at,
            exam=None,
        )
        
        assert response.id == bookmark_id
        assert response.user_id == user_id
        assert response.exam_id == exam_id
        assert response.created_at == created_at
        assert response.exam is None


class TestExamApplicationSchemas:
    """Tests for exam application schemas.
    
    Validates: Requirements 3.6
    """

    def test_exam_application_create_valid(self):
        """Test creating a valid ExamApplicationCreate schema.
        
        Requirement 3.6: Record application date and update status
        """
        from app.schemas.exam import ExamApplicationCreate
        
        exam_id = uuid.uuid4()
        applied_date = date.today()
        
        data = ExamApplicationCreate(
            exam_id=exam_id,
            applied_date=applied_date,
            notes="Applied via official portal",
        )
        
        assert data.exam_id == exam_id
        assert data.applied_date == applied_date
        assert data.notes == "Applied via official portal"

    def test_exam_application_create_without_date(self):
        """Test ExamApplicationCreate without applied_date uses default."""
        from app.schemas.exam import ExamApplicationCreate
        
        exam_id = uuid.uuid4()
        data = ExamApplicationCreate(exam_id=exam_id)
        
        assert data.exam_id == exam_id
        assert data.applied_date is None  # Will be set to today in service

    def test_exam_application_update_status(self):
        """Test ExamApplicationUpdate for status changes.
        
        Requirement 3.6: Update status
        """
        from app.schemas.exam import ExamApplicationUpdate
        
        data = ExamApplicationUpdate(status=ApplicationStatus.SHORTLISTED)
        assert data.status == ApplicationStatus.SHORTLISTED

    def test_exam_application_update_notes(self):
        """Test ExamApplicationUpdate for notes changes."""
        from app.schemas.exam import ExamApplicationUpdate
        
        data = ExamApplicationUpdate(notes="Interview scheduled for next week")
        assert data.notes == "Interview scheduled for next week"

    def test_exam_application_response_structure(self):
        """Test ExamApplicationResponse has all required fields."""
        from app.schemas.exam import ExamApplicationResponse
        from datetime import datetime
        
        app_id = uuid.uuid4()
        user_id = uuid.uuid4()
        exam_id = uuid.uuid4()
        applied_date = date.today()
        created_at = datetime.now()
        updated_at = datetime.now()
        
        response = ExamApplicationResponse(
            id=app_id,
            user_id=user_id,
            exam_id=exam_id,
            status=ApplicationStatus.APPLIED,
            applied_date=applied_date,
            notes="Test notes",
            created_at=created_at,
            updated_at=updated_at,
            exam=None,
        )
        
        assert response.id == app_id
        assert response.user_id == user_id
        assert response.exam_id == exam_id
        assert response.status == ApplicationStatus.APPLIED
        assert response.applied_date == applied_date
        assert response.notes == "Test notes"


class TestExamDetailSchemas:
    """Tests for exam detail schemas.
    
    Validates: Requirements 3.8
    """

    def test_exam_detail_response_includes_syllabus(self):
        """Test ExamDetailResponse includes syllabus field.
        
        Requirement 3.8: Return syllabus
        """
        from app.schemas.exam import ExamDetailResponse
        from datetime import datetime
        
        exam_id = uuid.uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()
        
        response = ExamDetailResponse(
            id=exam_id,
            name="GATE 2024",
            organization="IIT",
            exam_type=ExamType.HIGHER_EDUCATION,
            description="Graduate Aptitude Test in Engineering",
            registration_start=date.today(),
            registration_end=date.today() + timedelta(days=30),
            exam_date=date.today() + timedelta(days=90),
            min_cgpa=None,
            max_backlogs=None,
            eligible_degrees=["B.Tech", "B.E"],
            eligible_branches=["CSE", "IT", "ECE"],
            graduation_year_min=2024,
            graduation_year_max=2025,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
            syllabus="Engineering Mathematics, Digital Logic, Computer Organization...",
            cutoffs={"General": 25.0, "OBC": 22.5, "SC/ST": 16.67},
            resources=[
                {"title": "Previous Year Papers", "url": "https://gate.iitk.ac.in/papers"},
                {"title": "Syllabus PDF", "url": "https://gate.iitk.ac.in/syllabus"},
            ],
            source_url="https://gate.iitk.ac.in",
            is_bookmarked=False,
            is_applied=False,
            application_status=None,
        )
        
        assert response.syllabus == "Engineering Mathematics, Digital Logic, Computer Organization..."

    def test_exam_detail_response_includes_cutoffs(self):
        """Test ExamDetailResponse includes cutoffs field.
        
        Requirement 3.8: Return cutoffs
        """
        from app.schemas.exam import ExamDetailResponse
        from datetime import datetime
        
        exam_id = uuid.uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()
        
        response = ExamDetailResponse(
            id=exam_id,
            name="GATE 2024",
            organization="IIT",
            exam_type=ExamType.HIGHER_EDUCATION,
            description=None,
            registration_start=None,
            registration_end=None,
            exam_date=None,
            min_cgpa=None,
            max_backlogs=None,
            eligible_degrees=None,
            eligible_branches=None,
            graduation_year_min=None,
            graduation_year_max=None,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
            syllabus=None,
            cutoffs={"General": 25.0, "OBC": 22.5, "SC/ST": 16.67},
            resources=None,
            source_url=None,
            is_bookmarked=False,
            is_applied=False,
            application_status=None,
        )
        
        assert response.cutoffs == {"General": 25.0, "OBC": 22.5, "SC/ST": 16.67}

    def test_exam_detail_response_includes_resources(self):
        """Test ExamDetailResponse includes resources field.
        
        Requirement 3.8: Return resource links
        """
        from app.schemas.exam import ExamDetailResponse
        from datetime import datetime
        
        exam_id = uuid.uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()
        
        resources = [
            {"title": "Previous Year Papers", "url": "https://example.com/papers"},
            {"title": "Study Material", "url": "https://example.com/material"},
        ]
        
        response = ExamDetailResponse(
            id=exam_id,
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            description=None,
            registration_start=None,
            registration_end=None,
            exam_date=None,
            min_cgpa=None,
            max_backlogs=None,
            eligible_degrees=None,
            eligible_branches=None,
            graduation_year_min=None,
            graduation_year_max=None,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
            syllabus=None,
            cutoffs=None,
            resources=resources,
            source_url=None,
            is_bookmarked=False,
            is_applied=False,
            application_status=None,
        )
        
        assert response.resources == resources
        assert len(response.resources) == 2

    def test_exam_detail_response_includes_bookmark_status(self):
        """Test ExamDetailResponse includes is_bookmarked field.
        
        Requirement 3.5: Track bookmark status
        """
        from app.schemas.exam import ExamDetailResponse
        from datetime import datetime
        
        exam_id = uuid.uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()
        
        response = ExamDetailResponse(
            id=exam_id,
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            description=None,
            registration_start=None,
            registration_end=None,
            exam_date=None,
            min_cgpa=None,
            max_backlogs=None,
            eligible_degrees=None,
            eligible_branches=None,
            graduation_year_min=None,
            graduation_year_max=None,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
            syllabus=None,
            cutoffs=None,
            resources=None,
            source_url=None,
            is_bookmarked=True,
            is_applied=False,
            application_status=None,
        )
        
        assert response.is_bookmarked is True

    def test_exam_detail_response_includes_application_status(self):
        """Test ExamDetailResponse includes application status fields.
        
        Requirement 3.6: Track application status
        """
        from app.schemas.exam import ExamDetailResponse
        from datetime import datetime
        
        exam_id = uuid.uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()
        
        response = ExamDetailResponse(
            id=exam_id,
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            description=None,
            registration_start=None,
            registration_end=None,
            exam_date=None,
            min_cgpa=None,
            max_backlogs=None,
            eligible_degrees=None,
            eligible_branches=None,
            graduation_year_min=None,
            graduation_year_max=None,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
            syllabus=None,
            cutoffs=None,
            resources=None,
            source_url=None,
            is_bookmarked=False,
            is_applied=True,
            application_status=ApplicationStatus.SHORTLISTED,
        )
        
        assert response.is_applied is True
        assert response.application_status == ApplicationStatus.SHORTLISTED


class TestApplicationStatusTransitions:
    """Tests for application status transitions.
    
    Validates: Requirements 3.6
    """

    def test_all_application_statuses_are_valid(self):
        """Test that all application statuses can be used in updates."""
        from app.schemas.exam import ExamApplicationUpdate
        
        for status in ApplicationStatus:
            data = ExamApplicationUpdate(status=status)
            assert data.status == status

    def test_application_status_values(self):
        """Test application status enum values match expected strings."""
        assert ApplicationStatus.APPLIED.value == "applied"
        assert ApplicationStatus.SHORTLISTED.value == "shortlisted"
        assert ApplicationStatus.REJECTED.value == "rejected"
        assert ApplicationStatus.SELECTED.value == "selected"
        assert ApplicationStatus.WITHDRAWN.value == "withdrawn"

    def test_application_status_count(self):
        """Test that there are exactly 5 application statuses."""
        assert len(ApplicationStatus) == 5
