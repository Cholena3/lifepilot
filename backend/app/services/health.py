"""Health service for managing health records and family members.

Provides functionality for health record CRUD operations, family member
management, and health record search.

Validates: Requirements 14.1, 14.2, 14.5, 14.6
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health import HealthRecord, FamilyMember
from app.repositories.health import HealthRepository
from app.schemas.health import (
    HealthRecordCreate,
    HealthRecordUpdate,
    HealthRecordResponse,
    FamilyMemberCreate,
    FamilyMemberUpdate,
    FamilyMemberResponse,
    PaginatedHealthRecordResponse,
    PaginatedFamilyMemberResponse,
    TimelineEntryResponse,
    HealthTimelineResponse,
)


class HealthService:
    """Service for managing health records and family members.
    
    Validates: Requirements 14.1, 14.2, 14.5, 14.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the health service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.repository = HealthRepository(db)
    
    # ========================================================================
    # Family Member Operations
    # ========================================================================
    
    async def create_family_member(
        self,
        user_id: UUID,
        data: FamilyMemberCreate,
    ) -> FamilyMemberResponse:
        """Create a new family member.
        
        Validates: Requirements 14.2
        
        Args:
            user_id: User's UUID
            data: Family member creation data
            
        Returns:
            Created family member response
        """
        family_member = await self.repository.create_family_member(user_id, data)
        await self.db.commit()
        return FamilyMemberResponse.model_validate(family_member)
    
    async def get_family_member(
        self,
        user_id: UUID,
        family_member_id: UUID,
    ) -> Optional[FamilyMemberResponse]:
        """Get a family member by ID.
        
        Args:
            user_id: User's UUID
            family_member_id: Family member's UUID
            
        Returns:
            Family member response if found, None otherwise
        """
        family_member = await self.repository.get_family_member_by_id(
            family_member_id, user_id
        )
        if family_member is None:
            return None
        return FamilyMemberResponse.model_validate(family_member)
    
    async def list_family_members(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedFamilyMemberResponse:
        """List all family members for a user.
        
        Validates: Requirements 14.2
        
        Args:
            user_id: User's UUID
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated family member response
        """
        offset = (page - 1) * page_size
        
        family_members = await self.repository.get_family_members_by_user(
            user_id, limit=page_size, offset=offset
        )
        total = await self.repository.count_family_members(user_id)
        
        items = [FamilyMemberResponse.model_validate(fm) for fm in family_members]
        return PaginatedFamilyMemberResponse.create(items, total, page, page_size)
    
    async def update_family_member(
        self,
        user_id: UUID,
        family_member_id: UUID,
        data: FamilyMemberUpdate,
    ) -> Optional[FamilyMemberResponse]:
        """Update a family member.
        
        Args:
            user_id: User's UUID
            family_member_id: Family member's UUID
            data: Family member update data
            
        Returns:
            Updated family member response if found, None otherwise
        """
        family_member = await self.repository.get_family_member_by_id(
            family_member_id, user_id
        )
        if family_member is None:
            return None
        
        updated = await self.repository.update_family_member(family_member, data)
        await self.db.commit()
        return FamilyMemberResponse.model_validate(updated)
    
    async def delete_family_member(
        self,
        user_id: UUID,
        family_member_id: UUID,
    ) -> bool:
        """Delete a family member.
        
        Args:
            user_id: User's UUID
            family_member_id: Family member's UUID
            
        Returns:
            True if deleted, False if not found
        """
        family_member = await self.repository.get_family_member_by_id(
            family_member_id, user_id
        )
        if family_member is None:
            return False
        
        await self.repository.delete_family_member(family_member)
        await self.db.commit()
        return True
    
    # ========================================================================
    # Health Record Operations
    # ========================================================================
    
    async def create_health_record(
        self,
        user_id: UUID,
        data: HealthRecordCreate,
        file_path: str,
        encryption_key: str,
    ) -> HealthRecordResponse:
        """Create a new health record.
        
        Validates: Requirements 14.1, 14.2
        
        Args:
            user_id: User's UUID
            data: Health record creation data
            file_path: Path to the stored file
            encryption_key: Encryption key for the file
            
        Returns:
            Created health record response
        """
        # Validate family member belongs to user if provided
        if data.family_member_id is not None:
            family_member = await self.repository.get_family_member_by_id(
                data.family_member_id, user_id
            )
            if family_member is None:
                raise ValueError("Family member not found or does not belong to user")
        
        health_record = await self.repository.create_health_record(
            user_id, data, file_path, encryption_key
        )
        await self.db.commit()
        return HealthRecordResponse.model_validate(health_record)
    
    async def get_health_record(
        self,
        user_id: UUID,
        record_id: UUID,
    ) -> Optional[HealthRecordResponse]:
        """Get a health record by ID.
        
        Args:
            user_id: User's UUID
            record_id: Health record's UUID
            
        Returns:
            Health record response if found, None otherwise
        """
        health_record = await self.repository.get_health_record_by_id(record_id, user_id)
        if health_record is None:
            return None
        return HealthRecordResponse.model_validate(health_record)
    
    async def list_health_records(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedHealthRecordResponse:
        """List health records for a user with optional filtering.
        
        Validates: Requirements 14.1, 14.2, 14.5
        
        Args:
            user_id: User's UUID
            category: Optional category filter
            family_member_id: Optional family member filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated health record response
        """
        offset = (page - 1) * page_size
        
        health_records = await self.repository.get_health_records_by_user(
            user_id,
            category=category,
            family_member_id=family_member_id,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )
        total = await self.repository.count_health_records(
            user_id,
            category=category,
            family_member_id=family_member_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        items = [HealthRecordResponse.model_validate(hr) for hr in health_records]
        return PaginatedHealthRecordResponse.create(items, total, page, page_size)
    
    async def search_health_records(
        self,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedHealthRecordResponse:
        """Search health records by full-text search.
        
        Validates: Requirements 14.6
        
        Args:
            user_id: User's UUID
            query: Search query string
            category: Optional category filter
            family_member_id: Optional family member filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated health record response
        """
        offset = (page - 1) * page_size
        
        health_records = await self.repository.search_health_records(
            user_id,
            query,
            category=category,
            family_member_id=family_member_id,
            limit=page_size,
            offset=offset,
        )
        total = await self.repository.count_search_results(
            user_id,
            query,
            category=category,
            family_member_id=family_member_id,
        )
        
        items = [HealthRecordResponse.model_validate(hr) for hr in health_records]
        return PaginatedHealthRecordResponse.create(items, total, page, page_size)
    
    async def get_health_timeline(
        self,
        user_id: UUID,
        family_member_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> HealthTimelineResponse:
        """Get chronological health timeline for a user.
        
        Validates: Requirements 14.5, 14.6
        
        Returns health records in chronological order (most recent first),
        optionally filtered by family member.
        
        Args:
            user_id: User's UUID
            family_member_id: Optional family member filter (None for all)
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Health timeline response with chronologically ordered entries
        """
        offset = (page - 1) * page_size
        
        health_records = await self.repository.get_health_timeline(
            user_id,
            family_member_id=family_member_id,
            limit=page_size,
            offset=offset,
        )
        total = await self.repository.count_timeline_records(
            user_id,
            family_member_id=family_member_id,
        )
        
        # Convert to timeline entries with family member names
        items = []
        for hr in health_records:
            family_member_name = None
            if hr.family_member is not None:
                family_member_name = hr.family_member.name
            
            items.append(TimelineEntryResponse(
                id=hr.id,
                category=hr.category,
                title=hr.title,
                record_date=hr.record_date,
                doctor_name=hr.doctor_name,
                hospital_name=hr.hospital_name,
                family_member_id=hr.family_member_id,
                family_member_name=family_member_name,
                created_at=hr.created_at,
            ))
        
        return HealthTimelineResponse.create(items, total, page, page_size)
    
    async def update_health_record(
        self,
        user_id: UUID,
        record_id: UUID,
        data: HealthRecordUpdate,
    ) -> Optional[HealthRecordResponse]:
        """Update a health record.
        
        Args:
            user_id: User's UUID
            record_id: Health record's UUID
            data: Health record update data
            
        Returns:
            Updated health record response if found, None otherwise
        """
        health_record = await self.repository.get_health_record_by_id(record_id, user_id)
        if health_record is None:
            return None
        
        # Validate family member belongs to user if being updated
        if data.family_member_id is not None:
            family_member = await self.repository.get_family_member_by_id(
                data.family_member_id, user_id
            )
            if family_member is None:
                raise ValueError("Family member not found or does not belong to user")
        
        updated = await self.repository.update_health_record(health_record, data)
        await self.db.commit()
        return HealthRecordResponse.model_validate(updated)
    
    async def delete_health_record(
        self,
        user_id: UUID,
        record_id: UUID,
    ) -> bool:
        """Delete a health record.
        
        Args:
            user_id: User's UUID
            record_id: Health record's UUID
            
        Returns:
            True if deleted, False if not found
        """
        health_record = await self.repository.get_health_record_by_id(record_id, user_id)
        if health_record is None:
            return False
        
        await self.repository.delete_health_record(health_record)
        await self.db.commit()
        return True
    
    async def update_ocr_data(
        self,
        user_id: UUID,
        record_id: UUID,
        ocr_text: str,
        extracted_data: Optional[dict] = None,
    ) -> Optional[HealthRecordResponse]:
        """Update the OCR data for a health record.
        
        Args:
            user_id: User's UUID
            record_id: Health record's UUID
            ocr_text: Extracted OCR text
            extracted_data: Optional structured data from OCR
            
        Returns:
            Updated health record response if found, None otherwise
        """
        health_record = await self.repository.get_health_record_by_id(record_id, user_id)
        if health_record is None:
            return None
        
        updated = await self.repository.update_ocr_data(
            health_record, ocr_text, extracted_data
        )
        await self.db.commit()
        return HealthRecordResponse.model_validate(updated)
    
    async def trigger_prescription_ocr(
        self,
        user_id: UUID,
        record_id: UUID,
    ) -> Optional[str]:
        """Trigger async OCR processing for a prescription health record.
        
        Validates: Requirements 14.3, 14.4
        
        Args:
            user_id: User's UUID
            record_id: Health record's UUID
            
        Returns:
            Celery task ID if triggered, None if record not found
        """
        from app.tasks.ocr_tasks import process_prescription_ocr
        
        health_record = await self.repository.get_health_record_by_id(record_id, user_id)
        if health_record is None:
            return None
        
        # Only process prescription category records
        if health_record.category != "prescription":
            raise ValueError("OCR processing is only available for prescription records")
        
        # Queue the OCR task
        task = process_prescription_ocr.delay(
            health_record_id=str(record_id),
            user_id=str(user_id),
            file_path=health_record.file_path,
        )
        
        return task.id
    
    async def get_extracted_medicines(
        self,
        user_id: UUID,
        record_id: UUID,
    ) -> Optional[list]:
        """Get extracted medicines from a prescription health record.
        
        Validates: Requirements 14.3, 14.4
        
        Args:
            user_id: User's UUID
            record_id: Health record's UUID
            
        Returns:
            List of extracted medicines if available, None if record not found
        """
        health_record = await self.repository.get_health_record_by_id(record_id, user_id)
        if health_record is None:
            return None
        
        if health_record.extracted_data is None:
            return []
        
        return health_record.extracted_data.get("medicines", [])
    
    async def prepare_medicine_tracker_entries(
        self,
        user_id: UUID,
        record_id: UUID,
    ) -> list:
        """Prepare medicine tracker entries from extracted prescription data.
        
        Validates: Requirements 14.4
        
        This method extracts medicine information from a processed prescription
        and prepares it for creating medicine tracker entries (task 11.5).
        
        Args:
            user_id: User's UUID
            record_id: Health record's UUID
            
        Returns:
            List of dicts with medicine data ready for tracker creation
        """
        medicines = await self.get_extracted_medicines(user_id, record_id)
        if not medicines:
            return []
        
        tracker_entries = []
        for med in medicines:
            # Parse duration to days if available
            duration_days = None
            if med.get("duration"):
                duration_str = med["duration"].lower()
                import re
                duration_match = re.search(r'(\d+)\s*(day|week|month)', duration_str)
                if duration_match:
                    num = int(duration_match.group(1))
                    unit = duration_match.group(2)
                    if unit == "day":
                        duration_days = num
                    elif unit == "week":
                        duration_days = num * 7
                    elif unit == "month":
                        duration_days = num * 30
            
            tracker_entries.append({
                "name": med.get("name"),
                "dosage": med.get("dosage"),
                "frequency": med.get("frequency"),
                "duration_days": duration_days,
                "instructions": med.get("instructions"),
                "health_record_id": str(record_id),
            })
        
        return tracker_entries
