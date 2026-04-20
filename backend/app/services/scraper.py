"""Scraper service for exam data from various sources.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5

This module implements:
- Base scraper class with common functionality
- Specific scrapers for TCS, Infosys, GATE, UPSC, Naukri, LinkedIn
- Data validation and deduplication
- User notification on exam updates
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import Exam, ExamType
from app.models.notification import NotificationChannel
from app.repositories.exam import ExamBookmarkRepository, ExamRepository
from app.schemas.exam import ExamCreate, ExamUpdate
from app.services.exam import ExamService
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


class ScraperSource(str, Enum):
    """Supported scraper sources.
    
    Validates: Requirements 5.5
    """
    TCS = "tcs"
    INFOSYS = "infosys"
    GATE = "gate"
    UPSC = "upsc"
    NAUKRI = "naukri"
    LINKEDIN = "linkedin"


@dataclass
class ScrapedExamData:
    """Data structure for scraped exam information."""
    name: str
    organization: str
    exam_type: ExamType
    description: Optional[str] = None
    registration_start: Optional[date] = None
    registration_end: Optional[date] = None
    exam_date: Optional[date] = None
    min_cgpa: Optional[Decimal] = None
    max_backlogs: Optional[int] = None
    eligible_degrees: list[str] = field(default_factory=list)
    eligible_branches: list[str] = field(default_factory=list)
    graduation_year_min: Optional[int] = None
    graduation_year_max: Optional[int] = None
    syllabus: Optional[str] = None
    cutoffs: dict[str, Any] = field(default_factory=dict)
    resources: list[dict[str, str]] = field(default_factory=list)
    source_url: Optional[str] = None
    
    def to_exam_create(self) -> ExamCreate:
        """Convert to ExamCreate schema."""
        return ExamCreate(
            name=self.name,
            organization=self.organization,
            exam_type=self.exam_type,
            description=self.description,
            registration_start=self.registration_start,
            registration_end=self.registration_end,
            exam_date=self.exam_date,
            min_cgpa=self.min_cgpa,
            max_backlogs=self.max_backlogs,
            eligible_degrees=self.eligible_degrees,
            eligible_branches=self.eligible_branches,
            graduation_year_min=self.graduation_year_min,
            graduation_year_max=self.graduation_year_max,
            syllabus=self.syllabus,
            cutoffs=self.cutoffs,
            resources=self.resources,
            source_url=self.source_url,
        )
    
    def get_unique_key(self) -> str:
        """Generate a unique key for deduplication.
        
        Uses name, organization, and exam_date to create a unique identifier.
        """
        key_parts = [
            self.name.lower().strip(),
            self.organization.lower().strip(),
            str(self.exam_date) if self.exam_date else "",
        ]
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]


@dataclass
class ScraperResult:
    """Result of a scraping operation."""
    source: ScraperSource
    success: bool
    exams_found: int = 0
    exams_created: int = 0
    exams_updated: int = 0
    exams_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=None))
    completed_at: Optional[datetime] = None
    
    def complete(self) -> None:
        """Mark the scraping operation as complete."""
        self.completed_at = datetime.now(tz=None)


class BaseScraper(ABC):
    """Base class for exam scrapers.
    
    Validates: Requirements 5.1, 5.2, 5.3, 5.4
    
    Provides common functionality for:
    - Data validation
    - Deduplication
    - Database operations
    - User notifications
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.exam_service = ExamService(session)
        self.exam_repo = ExamRepository(session)
        self.bookmark_repo = ExamBookmarkRepository(session)
        self.notification_service = NotificationService(session)
    
    @property
    @abstractmethod
    def source(self) -> ScraperSource:
        """Return the scraper source identifier."""
        pass
    
    @abstractmethod
    async def fetch_exams(self) -> list[ScrapedExamData]:
        """Fetch exam data from the source.
        
        This method should be implemented by each specific scraper
        to fetch data from their respective sources.
        
        Returns:
            List of scraped exam data
        """
        pass
    
    def validate_exam_data(self, data: ScrapedExamData) -> tuple[bool, list[str]]:
        """Validate scraped exam data.
        
        Validates: Requirements 5.2
        
        Args:
            data: Scraped exam data to validate
            
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Required fields
        if not data.name or not data.name.strip():
            errors.append("Exam name is required")
        elif len(data.name) > 255:
            errors.append("Exam name exceeds 255 characters")
            
        if not data.organization or not data.organization.strip():
            errors.append("Organization is required")
        elif len(data.organization) > 255:
            errors.append("Organization exceeds 255 characters")
        
        # CGPA validation
        if data.min_cgpa is not None:
            if data.min_cgpa < 0 or data.min_cgpa > 10:
                errors.append("min_cgpa must be between 0 and 10")
        
        # Backlogs validation
        if data.max_backlogs is not None:
            if data.max_backlogs < 0:
                errors.append("max_backlogs must be non-negative")
        
        # Date validations
        if data.registration_start and data.registration_end:
            if data.registration_start > data.registration_end:
                errors.append("registration_start cannot be after registration_end")
        
        if data.registration_end and data.exam_date:
            if data.registration_end > data.exam_date:
                errors.append("registration_end cannot be after exam_date")
        
        # Graduation year validation
        if data.graduation_year_min and data.graduation_year_max:
            if data.graduation_year_min > data.graduation_year_max:
                errors.append("graduation_year_min cannot be greater than graduation_year_max")
        
        return len(errors) == 0, errors
    
    async def find_existing_exam(self, data: ScrapedExamData) -> Optional[Exam]:
        """Find an existing exam that matches the scraped data.
        
        Validates: Requirements 5.2 (deduplication)
        
        Uses source_url as primary match, falls back to name+organization+exam_date.
        """
        # First try to match by source_url if available
        if data.source_url:
            query = select(Exam).where(
                Exam.source_url == data.source_url,
                Exam.is_active == True,
            )
            result = await self.session.execute(query)
            exam = result.scalar_one_or_none()
            if exam:
                return exam
        
        # Fall back to matching by name, organization, and exam_date
        query = select(Exam).where(
            Exam.name == data.name,
            Exam.organization == data.organization,
            Exam.is_active == True,
        )
        if data.exam_date:
            query = query.where(Exam.exam_date == data.exam_date)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    def has_significant_changes(self, existing: Exam, new_data: ScrapedExamData) -> tuple[bool, list[str]]:
        """Check if the scraped data has significant changes from existing exam.
        
        Validates: Requirements 5.3
        
        Returns:
            Tuple of (has_changes, list of changed fields)
        """
        changed_fields = []
        
        # Check important fields for changes
        if existing.registration_start != new_data.registration_start:
            changed_fields.append("registration_start")
        if existing.registration_end != new_data.registration_end:
            changed_fields.append("registration_end")
        if existing.exam_date != new_data.exam_date:
            changed_fields.append("exam_date")
        if existing.min_cgpa != new_data.min_cgpa:
            changed_fields.append("min_cgpa")
        if existing.max_backlogs != new_data.max_backlogs:
            changed_fields.append("max_backlogs")
        if existing.syllabus != new_data.syllabus and new_data.syllabus:
            changed_fields.append("syllabus")
        if existing.description != new_data.description and new_data.description:
            changed_fields.append("description")
        
        return len(changed_fields) > 0, changed_fields

    async def notify_affected_users(
        self,
        exam: Exam,
        changed_fields: list[str],
    ) -> int:
        """Notify users who bookmarked an exam about updates.
        
        Validates: Requirements 5.3
        
        Args:
            exam: The updated exam
            changed_fields: List of fields that changed
            
        Returns:
            Number of notifications sent
        """
        # Get all users who bookmarked this exam
        user_ids = await self.bookmark_repo.get_users_who_bookmarked_exam(exam.id)
        
        if not user_ids:
            return 0
        
        notifications_sent = 0
        
        # Format the changed fields for the notification
        field_descriptions = {
            "registration_start": "registration start date",
            "registration_end": "registration deadline",
            "exam_date": "exam date",
            "min_cgpa": "minimum CGPA requirement",
            "max_backlogs": "maximum backlogs allowed",
            "syllabus": "syllabus",
            "description": "description",
        }
        
        changes_text = ", ".join(
            field_descriptions.get(f, f) for f in changed_fields
        )
        
        title = f"Exam Update: {exam.name}"
        body = (
            f"The {exam.name} exam from {exam.organization} has been updated. "
            f"Changes: {changes_text}. "
            f"Please review the updated information."
        )
        
        for user_id in user_ids:
            try:
                result = await self.notification_service.send_notification(
                    user_id=user_id,
                    title=title,
                    body=body,
                    channel=NotificationChannel.PUSH,
                )
                if result.success:
                    notifications_sent += 1
            except Exception as e:
                logger.error(
                    f"Failed to notify user {user_id} about exam {exam.id} update: {e}"
                )
        
        return notifications_sent
    
    async def process_exam(
        self,
        data: ScrapedExamData,
        result: ScraperResult,
    ) -> None:
        """Process a single scraped exam.
        
        Validates: Requirements 5.2, 5.3
        
        Args:
            data: Scraped exam data
            result: ScraperResult to update with statistics
        """
        # Validate the data
        is_valid, validation_errors = self.validate_exam_data(data)
        if not is_valid:
            result.exams_skipped += 1
            result.errors.extend(
                f"Validation error for '{data.name}': {err}" 
                for err in validation_errors
            )
            logger.warning(f"Skipping invalid exam data: {validation_errors}")
            return
        
        # Check for existing exam (deduplication)
        existing_exam = await self.find_existing_exam(data)
        
        if existing_exam:
            # Check if there are significant changes
            has_changes, changed_fields = self.has_significant_changes(existing_exam, data)
            
            if has_changes:
                # Update the existing exam
                update_data = ExamUpdate(
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
                )
                
                await self.exam_service.update_exam(existing_exam.id, update_data)
                
                # Update scraped_at timestamp
                existing_exam.scraped_at = datetime.utcnow()
                await self.session.flush()
                
                # Notify affected users
                await self.notify_affected_users(existing_exam, changed_fields)
                
                result.exams_updated += 1
                logger.info(
                    f"Updated exam '{data.name}' with changes: {changed_fields}"
                )
            else:
                # No significant changes, just update scraped_at
                existing_exam.scraped_at = datetime.utcnow()
                await self.session.flush()
                result.exams_skipped += 1
                logger.debug(f"No changes for exam '{data.name}'")
        else:
            # Create new exam
            exam_create = data.to_exam_create()
            new_exam = await self.exam_service.create_exam(exam_create)
            new_exam.scraped_at = datetime.utcnow()
            await self.session.flush()
            
            result.exams_created += 1
            logger.info(f"Created new exam '{data.name}'")
    
    async def run(self) -> ScraperResult:
        """Run the scraper.
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        
        Returns:
            ScraperResult with statistics about the scraping operation
        """
        result = ScraperResult(source=self.source, success=False)
        
        try:
            logger.info(f"Starting scraper for {self.source.value}")
            
            # Fetch exams from source
            scraped_exams = await self.fetch_exams()
            result.exams_found = len(scraped_exams)
            
            logger.info(f"Found {result.exams_found} exams from {self.source.value}")
            
            # Process each exam
            for exam_data in scraped_exams:
                try:
                    await self.process_exam(exam_data, result)
                except Exception as e:
                    result.errors.append(f"Error processing exam '{exam_data.name}': {str(e)}")
                    logger.exception(f"Error processing exam: {e}")
            
            result.success = True
            
        except Exception as e:
            result.errors.append(f"Scraper error: {str(e)}")
            logger.exception(f"Scraper {self.source.value} failed: {e}")
        
        result.complete()
        logger.info(
            f"Scraper {self.source.value} completed: "
            f"found={result.exams_found}, created={result.exams_created}, "
            f"updated={result.exams_updated}, skipped={result.exams_skipped}"
        )
        
        return result


# ============================================================================
# Specific Scraper Implementations
# ============================================================================

class TCSScraper(BaseScraper):
    """Scraper for TCS recruitment exams.
    
    Validates: Requirements 5.5
    
    Note: This is a mock implementation. In production, this would
    scrape actual TCS career portal pages.
    """
    
    @property
    def source(self) -> ScraperSource:
        return ScraperSource.TCS
    
    async def fetch_exams(self) -> list[ScrapedExamData]:
        """Fetch TCS exam data.
        
        In production, this would:
        1. Make HTTP requests to TCS career portal
        2. Parse HTML/JSON responses
        3. Extract exam information
        
        For now, returns mock data for testing purposes.
        """
        # Mock implementation - in production, this would scrape actual data
        logger.info("Fetching TCS exam data (mock implementation)")
        
        # Return empty list - actual implementation would fetch from TCS portal
        # This allows the scraper infrastructure to work without real scraping
        return []


class InfosysScraper(BaseScraper):
    """Scraper for Infosys recruitment exams.
    
    Validates: Requirements 5.5
    """
    
    @property
    def source(self) -> ScraperSource:
        return ScraperSource.INFOSYS
    
    async def fetch_exams(self) -> list[ScrapedExamData]:
        """Fetch Infosys exam data."""
        logger.info("Fetching Infosys exam data (mock implementation)")
        return []


class GATEScraper(BaseScraper):
    """Scraper for GATE exam information.
    
    Validates: Requirements 5.5
    """
    
    @property
    def source(self) -> ScraperSource:
        return ScraperSource.GATE
    
    async def fetch_exams(self) -> list[ScrapedExamData]:
        """Fetch GATE exam data."""
        logger.info("Fetching GATE exam data (mock implementation)")
        return []


class UPSCScraper(BaseScraper):
    """Scraper for UPSC exam information.
    
    Validates: Requirements 5.5
    """
    
    @property
    def source(self) -> ScraperSource:
        return ScraperSource.UPSC
    
    async def fetch_exams(self) -> list[ScrapedExamData]:
        """Fetch UPSC exam data."""
        logger.info("Fetching UPSC exam data (mock implementation)")
        return []


class NaukriScraper(BaseScraper):
    """Scraper for Naukri job portal exams.
    
    Validates: Requirements 5.5
    """
    
    @property
    def source(self) -> ScraperSource:
        return ScraperSource.NAUKRI
    
    async def fetch_exams(self) -> list[ScrapedExamData]:
        """Fetch Naukri exam data."""
        logger.info("Fetching Naukri exam data (mock implementation)")
        return []


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job opportunities.
    
    Validates: Requirements 5.5
    """
    
    @property
    def source(self) -> ScraperSource:
        return ScraperSource.LINKEDIN
    
    async def fetch_exams(self) -> list[ScrapedExamData]:
        """Fetch LinkedIn exam/job data."""
        logger.info("Fetching LinkedIn exam data (mock implementation)")
        return []


# ============================================================================
# Scraper Factory
# ============================================================================

def get_scraper(source: ScraperSource, session: AsyncSession) -> BaseScraper:
    """Factory function to get the appropriate scraper for a source.
    
    Args:
        source: The scraper source
        session: Database session
        
    Returns:
        Appropriate scraper instance
        
    Raises:
        ValueError: If source is not supported
    """
    scrapers = {
        ScraperSource.TCS: TCSScraper,
        ScraperSource.INFOSYS: InfosysScraper,
        ScraperSource.GATE: GATEScraper,
        ScraperSource.UPSC: UPSCScraper,
        ScraperSource.NAUKRI: NaukriScraper,
        ScraperSource.LINKEDIN: LinkedInScraper,
    }
    
    scraper_class = scrapers.get(source)
    if not scraper_class:
        raise ValueError(f"Unsupported scraper source: {source}")
    
    return scraper_class(session)


async def run_all_scrapers(session: AsyncSession) -> list[ScraperResult]:
    """Run all configured scrapers.
    
    Validates: Requirements 5.1
    
    Args:
        session: Database session
        
    Returns:
        List of ScraperResult for each source
    """
    results = []
    
    for source in ScraperSource:
        try:
            scraper = get_scraper(source, session)
            result = await scraper.run()
            results.append(result)
        except Exception as e:
            logger.exception(f"Failed to run scraper for {source.value}: {e}")
            results.append(ScraperResult(
                source=source,
                success=False,
                errors=[str(e)],
            ))
    
    return results
