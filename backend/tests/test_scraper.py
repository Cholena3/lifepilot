"""Unit tests for exam data scraper service.

Tests Requirements 5.1, 5.2, 5.3, 5.4, 5.5 for exam data scraping.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.exam import ExamType
from app.services.scraper import (
    BaseScraper,
    GATEScraper,
    InfosysScraper,
    LinkedInScraper,
    NaukriScraper,
    ScrapedExamData,
    ScraperResult,
    ScraperSource,
    TCSScraper,
    UPSCScraper,
    get_scraper,
    run_all_scrapers,
)


# ============================================================================
# ScrapedExamData Tests
# ============================================================================

class TestScrapedExamData:
    """Tests for ScrapedExamData dataclass."""

    def test_create_basic_scraped_data(self):
        """Test creating basic scraped exam data."""
        data = ScrapedExamData(
            name="TCS NQT 2024",
            organization="Tata Consultancy Services",
            exam_type=ExamType.CAMPUS_PLACEMENT,
        )
        assert data.name == "TCS NQT 2024"
        assert data.organization == "Tata Consultancy Services"
        assert data.exam_type == ExamType.CAMPUS_PLACEMENT

    def test_create_full_scraped_data(self):
        """Test creating scraped exam data with all fields."""
        data = ScrapedExamData(
            name="GATE 2024",
            organization="IIT Bombay",
            exam_type=ExamType.HIGHER_EDUCATION,
            description="Graduate Aptitude Test in Engineering",
            registration_start=date(2024, 1, 1),
            registration_end=date(2024, 2, 15),
            exam_date=date(2024, 4, 10),
            min_cgpa=Decimal("6.0"),
            max_backlogs=0,
            eligible_degrees=["B.Tech", "B.E"],
            eligible_branches=["CSE", "IT", "ECE"],
            graduation_year_min=2024,
            graduation_year_max=2025,
            syllabus="Engineering Mathematics, Digital Logic...",
            cutoffs={"General": 25.0, "OBC": 22.5},
            resources=[{"title": "Papers", "url": "https://example.com"}],
            source_url="https://gate.iitb.ac.in",
        )
        
        assert data.description == "Graduate Aptitude Test in Engineering"
        assert data.registration_start == date(2024, 1, 1)
        assert data.min_cgpa == Decimal("6.0")
        assert data.eligible_degrees == ["B.Tech", "B.E"]

    def test_to_exam_create(self):
        """Test converting ScrapedExamData to ExamCreate schema."""
        data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            min_cgpa=Decimal("7.0"),
            max_backlogs=1,
        )
        
        exam_create = data.to_exam_create()
        
        assert exam_create.name == "Test Exam"
        assert exam_create.organization == "Test Org"
        assert exam_create.exam_type == ExamType.CAMPUS_PLACEMENT
        assert exam_create.min_cgpa == Decimal("7.0")
        assert exam_create.max_backlogs == 1

    def test_get_unique_key_same_data(self):
        """Test that same data produces same unique key."""
        data1 = ScrapedExamData(
            name="TCS NQT",
            organization="TCS",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            exam_date=date(2024, 3, 15),
        )
        data2 = ScrapedExamData(
            name="TCS NQT",
            organization="TCS",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            exam_date=date(2024, 3, 15),
        )
        
        assert data1.get_unique_key() == data2.get_unique_key()

    def test_get_unique_key_different_data(self):
        """Test that different data produces different unique keys."""
        data1 = ScrapedExamData(
            name="TCS NQT",
            organization="TCS",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            exam_date=date(2024, 3, 15),
        )
        data2 = ScrapedExamData(
            name="Infosys InfyTQ",
            organization="Infosys",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            exam_date=date(2024, 3, 15),
        )
        
        assert data1.get_unique_key() != data2.get_unique_key()

    def test_get_unique_key_case_insensitive(self):
        """Test that unique key is case insensitive."""
        data1 = ScrapedExamData(
            name="TCS NQT",
            organization="TCS",
            exam_type=ExamType.CAMPUS_PLACEMENT,
        )
        data2 = ScrapedExamData(
            name="tcs nqt",
            organization="tcs",
            exam_type=ExamType.CAMPUS_PLACEMENT,
        )
        
        assert data1.get_unique_key() == data2.get_unique_key()


# ============================================================================
# ScraperResult Tests
# ============================================================================

class TestScraperResult:
    """Tests for ScraperResult dataclass."""

    def test_create_scraper_result(self):
        """Test creating a scraper result."""
        result = ScraperResult(
            source=ScraperSource.TCS,
            success=True,
            exams_found=10,
            exams_created=5,
            exams_updated=3,
            exams_skipped=2,
        )
        
        assert result.source == ScraperSource.TCS
        assert result.success is True
        assert result.exams_found == 10
        assert result.exams_created == 5
        assert result.exams_updated == 3
        assert result.exams_skipped == 2

    def test_scraper_result_complete(self):
        """Test marking scraper result as complete."""
        result = ScraperResult(source=ScraperSource.TCS, success=True)
        assert result.completed_at is None
        
        result.complete()
        
        assert result.completed_at is not None
        assert isinstance(result.completed_at, datetime)

    def test_scraper_result_errors(self):
        """Test scraper result with errors."""
        result = ScraperResult(
            source=ScraperSource.TCS,
            success=False,
            errors=["Connection timeout", "Invalid response"],
        )
        
        assert result.success is False
        assert len(result.errors) == 2
        assert "Connection timeout" in result.errors


# ============================================================================
# ScraperSource Tests
# ============================================================================

class TestScraperSource:
    """Tests for ScraperSource enum.
    
    Validates: Requirements 5.5
    """

    def test_all_sources_exist(self):
        """Test that all required scraper sources exist.
        
        Validates: Requirements 5.5 - Support TCS, Infosys, GATE, UPSC, Naukri, LinkedIn
        """
        assert ScraperSource.TCS.value == "tcs"
        assert ScraperSource.INFOSYS.value == "infosys"
        assert ScraperSource.GATE.value == "gate"
        assert ScraperSource.UPSC.value == "upsc"
        assert ScraperSource.NAUKRI.value == "naukri"
        assert ScraperSource.LINKEDIN.value == "linkedin"

    def test_source_count(self):
        """Test that there are exactly 6 scraper sources."""
        assert len(ScraperSource) == 6


# ============================================================================
# Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Tests for scraper data validation.
    
    Validates: Requirements 5.2
    """

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    def test_validate_valid_data(self, mock_session):
        """Test validation of valid exam data."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="TCS NQT 2024",
            organization="TCS",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            min_cgpa=Decimal("6.0"),
            max_backlogs=0,
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_name(self, mock_session):
        """Test validation fails for missing name."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="",
            organization="TCS",
            exam_type=ExamType.CAMPUS_PLACEMENT,
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is False
        assert any("name" in err.lower() for err in errors)

    def test_validate_missing_organization(self, mock_session):
        """Test validation fails for missing organization."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="Test Exam",
            organization="",
            exam_type=ExamType.CAMPUS_PLACEMENT,
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is False
        assert any("organization" in err.lower() for err in errors)

    def test_validate_invalid_cgpa(self, mock_session):
        """Test validation fails for invalid CGPA."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            min_cgpa=Decimal("11.0"),  # Invalid: > 10
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is False
        assert any("cgpa" in err.lower() for err in errors)

    def test_validate_negative_backlogs(self, mock_session):
        """Test validation fails for negative backlogs."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            max_backlogs=-1,  # Invalid: negative
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is False
        assert any("backlog" in err.lower() for err in errors)

    def test_validate_invalid_date_range(self, mock_session):
        """Test validation fails for invalid date range."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            registration_start=date(2024, 3, 1),
            registration_end=date(2024, 2, 1),  # Invalid: before start
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is False
        assert any("registration" in err.lower() for err in errors)

    def test_validate_invalid_graduation_year_range(self, mock_session):
        """Test validation fails for invalid graduation year range."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            graduation_year_min=2025,
            graduation_year_max=2024,  # Invalid: max < min
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is False
        assert any("graduation" in err.lower() for err in errors)

    def test_validate_name_too_long(self, mock_session):
        """Test validation fails for name exceeding max length."""
        scraper = TCSScraper(mock_session)
        data = ScrapedExamData(
            name="A" * 300,  # Exceeds 255 characters
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
        )
        
        is_valid, errors = scraper.validate_exam_data(data)
        
        assert is_valid is False
        assert any("255" in err or "exceed" in err.lower() for err in errors)


# ============================================================================
# Scraper Factory Tests
# ============================================================================

class TestScraperFactory:
    """Tests for scraper factory function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    def test_get_tcs_scraper(self, mock_session):
        """Test getting TCS scraper."""
        scraper = get_scraper(ScraperSource.TCS, mock_session)
        assert isinstance(scraper, TCSScraper)
        assert scraper.source == ScraperSource.TCS

    def test_get_infosys_scraper(self, mock_session):
        """Test getting Infosys scraper."""
        scraper = get_scraper(ScraperSource.INFOSYS, mock_session)
        assert isinstance(scraper, InfosysScraper)
        assert scraper.source == ScraperSource.INFOSYS

    def test_get_gate_scraper(self, mock_session):
        """Test getting GATE scraper."""
        scraper = get_scraper(ScraperSource.GATE, mock_session)
        assert isinstance(scraper, GATEScraper)
        assert scraper.source == ScraperSource.GATE

    def test_get_upsc_scraper(self, mock_session):
        """Test getting UPSC scraper."""
        scraper = get_scraper(ScraperSource.UPSC, mock_session)
        assert isinstance(scraper, UPSCScraper)
        assert scraper.source == ScraperSource.UPSC

    def test_get_naukri_scraper(self, mock_session):
        """Test getting Naukri scraper."""
        scraper = get_scraper(ScraperSource.NAUKRI, mock_session)
        assert isinstance(scraper, NaukriScraper)
        assert scraper.source == ScraperSource.NAUKRI

    def test_get_linkedin_scraper(self, mock_session):
        """Test getting LinkedIn scraper."""
        scraper = get_scraper(ScraperSource.LINKEDIN, mock_session)
        assert isinstance(scraper, LinkedInScraper)
        assert scraper.source == ScraperSource.LINKEDIN


# ============================================================================
# Change Detection Tests
# ============================================================================

class TestChangeDetection:
    """Tests for detecting significant changes in exam data.
    
    Validates: Requirements 5.3
    """

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_exam(self):
        """Create a mock existing exam."""
        exam = MagicMock()
        exam.id = uuid.uuid4()
        exam.name = "Test Exam"
        exam.organization = "Test Org"
        exam.registration_start = date(2024, 1, 1)
        exam.registration_end = date(2024, 2, 15)
        exam.exam_date = date(2024, 3, 15)
        exam.min_cgpa = Decimal("6.0")
        exam.max_backlogs = 0
        exam.syllabus = "Original syllabus"
        exam.description = "Original description"
        return exam

    def test_no_changes_detected(self, mock_session, mock_exam):
        """Test that no changes are detected when data is the same."""
        scraper = TCSScraper(mock_session)
        new_data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            registration_start=date(2024, 1, 1),
            registration_end=date(2024, 2, 15),
            exam_date=date(2024, 3, 15),
            min_cgpa=Decimal("6.0"),
            max_backlogs=0,
            syllabus="Original syllabus",
            description="Original description",
        )
        
        has_changes, changed_fields = scraper.has_significant_changes(mock_exam, new_data)
        
        assert has_changes is False
        assert len(changed_fields) == 0

    def test_registration_end_change_detected(self, mock_session, mock_exam):
        """Test that registration deadline change is detected."""
        scraper = TCSScraper(mock_session)
        new_data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            registration_start=date(2024, 1, 1),
            registration_end=date(2024, 2, 28),  # Changed
            exam_date=date(2024, 3, 15),
            min_cgpa=Decimal("6.0"),
            max_backlogs=0,
        )
        
        has_changes, changed_fields = scraper.has_significant_changes(mock_exam, new_data)
        
        assert has_changes is True
        assert "registration_end" in changed_fields

    def test_exam_date_change_detected(self, mock_session, mock_exam):
        """Test that exam date change is detected."""
        scraper = TCSScraper(mock_session)
        new_data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            registration_start=date(2024, 1, 1),
            registration_end=date(2024, 2, 15),
            exam_date=date(2024, 4, 1),  # Changed
            min_cgpa=Decimal("6.0"),
            max_backlogs=0,
        )
        
        has_changes, changed_fields = scraper.has_significant_changes(mock_exam, new_data)
        
        assert has_changes is True
        assert "exam_date" in changed_fields

    def test_cgpa_change_detected(self, mock_session, mock_exam):
        """Test that CGPA requirement change is detected."""
        scraper = TCSScraper(mock_session)
        new_data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            registration_start=date(2024, 1, 1),
            registration_end=date(2024, 2, 15),
            exam_date=date(2024, 3, 15),
            min_cgpa=Decimal("7.0"),  # Changed
            max_backlogs=0,
        )
        
        has_changes, changed_fields = scraper.has_significant_changes(mock_exam, new_data)
        
        assert has_changes is True
        assert "min_cgpa" in changed_fields

    def test_multiple_changes_detected(self, mock_session, mock_exam):
        """Test that multiple changes are detected."""
        scraper = TCSScraper(mock_session)
        new_data = ScrapedExamData(
            name="Test Exam",
            organization="Test Org",
            exam_type=ExamType.CAMPUS_PLACEMENT,
            registration_start=date(2024, 1, 15),  # Changed
            registration_end=date(2024, 2, 28),  # Changed
            exam_date=date(2024, 4, 1),  # Changed
            min_cgpa=Decimal("6.0"),
            max_backlogs=0,
        )
        
        has_changes, changed_fields = scraper.has_significant_changes(mock_exam, new_data)
        
        assert has_changes is True
        assert len(changed_fields) >= 2


# ============================================================================
# Specific Scraper Tests
# ============================================================================

class TestSpecificScrapers:
    """Tests for specific scraper implementations.
    
    Validates: Requirements 5.5
    """

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_tcs_scraper_fetch(self, mock_session):
        """Test TCS scraper fetch returns list."""
        scraper = TCSScraper(mock_session)
        result = await scraper.fetch_exams()
        
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_infosys_scraper_fetch(self, mock_session):
        """Test Infosys scraper fetch returns list."""
        scraper = InfosysScraper(mock_session)
        result = await scraper.fetch_exams()
        
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_gate_scraper_fetch(self, mock_session):
        """Test GATE scraper fetch returns list."""
        scraper = GATEScraper(mock_session)
        result = await scraper.fetch_exams()
        
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_upsc_scraper_fetch(self, mock_session):
        """Test UPSC scraper fetch returns list."""
        scraper = UPSCScraper(mock_session)
        result = await scraper.fetch_exams()
        
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_naukri_scraper_fetch(self, mock_session):
        """Test Naukri scraper fetch returns list."""
        scraper = NaukriScraper(mock_session)
        result = await scraper.fetch_exams()
        
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_linkedin_scraper_fetch(self, mock_session):
        """Test LinkedIn scraper fetch returns list."""
        scraper = LinkedInScraper(mock_session)
        result = await scraper.fetch_exams()
        
        assert isinstance(result, list)


# ============================================================================
# Scraper Run Tests
# ============================================================================

class TestScraperRun:
    """Tests for running scrapers.
    
    Validates: Requirements 5.1, 5.4
    """

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_scraper_run_returns_result(self, mock_session):
        """Test that running a scraper returns a ScraperResult."""
        scraper = TCSScraper(mock_session)
        
        # Mock the dependencies
        with patch.object(scraper, 'fetch_exams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            
            result = await scraper.run()
            
            assert isinstance(result, ScraperResult)
            assert result.source == ScraperSource.TCS
            assert result.success is True
            assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_scraper_run_handles_fetch_error(self, mock_session):
        """Test that scraper handles fetch errors gracefully.
        
        Validates: Requirements 5.4 - Log error and retry
        """
        scraper = TCSScraper(mock_session)
        
        with patch.object(scraper, 'fetch_exams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")
            
            result = await scraper.run()
            
            assert result.success is False
            assert len(result.errors) > 0
            assert "Network error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_scraper_run_counts_exams(self, mock_session):
        """Test that scraper correctly counts found exams."""
        scraper = TCSScraper(mock_session)
        
        mock_exams = [
            ScrapedExamData(
                name=f"Exam {i}",
                organization="Test Org",
                exam_type=ExamType.CAMPUS_PLACEMENT,
            )
            for i in range(3)
        ]
        
        with patch.object(scraper, 'fetch_exams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_exams
            with patch.object(scraper, 'process_exam', new_callable=AsyncMock):
                result = await scraper.run()
                
                assert result.exams_found == 3


# ============================================================================
# Celery Task Tests
# ============================================================================

class TestCeleryTasks:
    """Tests for Celery scraper tasks.
    
    Validates: Requirements 5.1
    """

    def test_task_names_are_correct(self):
        """Test that Celery task names are correctly defined."""
        from app.tasks.exam_tasks import (
            run_all_exam_scrapers,
            run_exam_scraper,
            scrape_gate_exams,
            scrape_infosys_exams,
            scrape_linkedin_exams,
            scrape_naukri_exams,
            scrape_tcs_exams,
            scrape_upsc_exams,
        )
        
        assert run_exam_scraper.name == "app.tasks.exam_tasks.run_exam_scraper"
        assert run_all_exam_scrapers.name == "app.tasks.exam_tasks.run_all_exam_scrapers"
        assert scrape_tcs_exams.name == "app.tasks.exam_tasks.scrape_tcs_exams"
        assert scrape_infosys_exams.name == "app.tasks.exam_tasks.scrape_infosys_exams"
        assert scrape_gate_exams.name == "app.tasks.exam_tasks.scrape_gate_exams"
        assert scrape_upsc_exams.name == "app.tasks.exam_tasks.scrape_upsc_exams"
        assert scrape_naukri_exams.name == "app.tasks.exam_tasks.scrape_naukri_exams"
        assert scrape_linkedin_exams.name == "app.tasks.exam_tasks.scrape_linkedin_exams"


# ============================================================================
# Celery Beat Schedule Tests
# ============================================================================

class TestCeleryBeatSchedule:
    """Tests for Celery Beat schedule configuration.
    
    Validates: Requirements 5.1
    """

    def test_scraper_tasks_in_beat_schedule(self):
        """Test that scraper tasks are in Celery Beat schedule."""
        from app.tasks import celery_app
        
        schedule = celery_app.conf.beat_schedule
        
        # Check that main scraper task is scheduled
        assert "scrape-all-exam-sources-daily" in schedule
        
        # Check individual scraper tasks
        assert "scrape-tcs-exams-daily" in schedule
        assert "scrape-infosys-exams-daily" in schedule
        assert "scrape-gate-exams-weekly" in schedule
        assert "scrape-upsc-exams-weekly" in schedule
        assert "scrape-naukri-exams-twice-daily" in schedule
        assert "scrape-linkedin-exams-twice-daily" in schedule

    def test_scraper_schedule_intervals(self):
        """Test that scraper tasks have appropriate intervals."""
        from app.tasks import celery_app
        
        schedule = celery_app.conf.beat_schedule
        
        # Daily tasks (86400 seconds)
        assert schedule["scrape-all-exam-sources-daily"]["schedule"] == 86400.0
        assert schedule["scrape-tcs-exams-daily"]["schedule"] == 86400.0
        assert schedule["scrape-infosys-exams-daily"]["schedule"] == 86400.0
        
        # Weekly tasks (604800 seconds)
        assert schedule["scrape-gate-exams-weekly"]["schedule"] == 604800.0
        assert schedule["scrape-upsc-exams-weekly"]["schedule"] == 604800.0
        
        # Twice daily tasks (43200 seconds)
        assert schedule["scrape-naukri-exams-twice-daily"]["schedule"] == 43200.0
        assert schedule["scrape-linkedin-exams-twice-daily"]["schedule"] == 43200.0
