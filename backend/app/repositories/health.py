"""Health repository for database operations.

Validates: Requirements 14.1, 14.2, 14.5, 14.6
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.health import HealthRecord, FamilyMember
from app.schemas.health import (
    HealthRecordCreate,
    HealthRecordUpdate,
    FamilyMemberCreate,
    FamilyMemberUpdate,
)


class HealthRepository:
    """Repository for Health module database operations.
    
    Validates: Requirements 14.1, 14.2, 14.5, 14.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    # ========================================================================
    # Family Member Operations
    # ========================================================================
    
    async def create_family_member(
        self,
        user_id: UUID,
        data: FamilyMemberCreate,
    ) -> FamilyMember:
        """Create a new family member.
        
        Validates: Requirements 14.2
        
        Args:
            user_id: User's UUID
            data: Family member creation data
            
        Returns:
            Created FamilyMember model instance
        """
        family_member = FamilyMember(
            user_id=user_id,
            name=data.name,
            relationship=data.relationship,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
        )
        self.db.add(family_member)
        await self.db.flush()
        await self.db.refresh(family_member)
        return family_member
    
    async def get_family_member_by_id(
        self,
        family_member_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[FamilyMember]:
        """Get a family member by ID.
        
        Args:
            family_member_id: Family member's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            FamilyMember if found, None otherwise
        """
        stmt = select(FamilyMember).where(FamilyMember.id == family_member_id)
        if user_id is not None:
            stmt = stmt.where(FamilyMember.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_family_members_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FamilyMember]:
        """Get all family members for a user.
        
        Validates: Requirements 14.2
        
        Args:
            user_id: User's UUID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of FamilyMember model instances
        """
        stmt = (
            select(FamilyMember)
            .where(FamilyMember.user_id == user_id)
            .order_by(FamilyMember.name)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_family_members(self, user_id: UUID) -> int:
        """Count total family members for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Total count of family members
        """
        stmt = select(func.count(FamilyMember.id)).where(FamilyMember.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_family_member(
        self,
        family_member: FamilyMember,
        data: FamilyMemberUpdate,
    ) -> FamilyMember:
        """Update a family member.
        
        Args:
            family_member: Existing FamilyMember model instance
            data: Family member update data
            
        Returns:
            Updated FamilyMember model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(family_member, field, value)
        
        await self.db.flush()
        await self.db.refresh(family_member)
        return family_member
    
    async def delete_family_member(self, family_member: FamilyMember) -> None:
        """Delete a family member.
        
        Args:
            family_member: FamilyMember model instance to delete
        """
        await self.db.delete(family_member)
        await self.db.flush()
    
    # ========================================================================
    # Health Record Operations
    # ========================================================================
    
    async def create_health_record(
        self,
        user_id: UUID,
        data: HealthRecordCreate,
        file_path: str,
        encryption_key: str,
    ) -> HealthRecord:
        """Create a new health record.
        
        Validates: Requirements 14.1, 14.2
        
        Args:
            user_id: User's UUID
            data: Health record creation data
            file_path: Path to the stored file
            encryption_key: Encryption key for the file
            
        Returns:
            Created HealthRecord model instance
        """
        health_record = HealthRecord(
            user_id=user_id,
            family_member_id=data.family_member_id,
            category=data.category,
            title=data.title,
            file_path=file_path,
            content_type=data.content_type,
            file_size=data.file_size,
            encryption_key=encryption_key,
            record_date=data.record_date,
            doctor_name=data.doctor_name,
            hospital_name=data.hospital_name,
            notes=data.notes,
        )
        self.db.add(health_record)
        await self.db.flush()
        await self.db.refresh(health_record)
        return health_record
    
    async def get_health_record_by_id(
        self,
        record_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[HealthRecord]:
        """Get a health record by ID.
        
        Args:
            record_id: Health record's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            HealthRecord if found, None otherwise
        """
        stmt = select(HealthRecord).where(HealthRecord.id == record_id)
        if user_id is not None:
            stmt = stmt.where(HealthRecord.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_health_record_with_family_member(
        self,
        record_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[HealthRecord]:
        """Get a health record by ID with family member loaded.
        
        Args:
            record_id: Health record's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            HealthRecord with family_member relationship loaded
        """
        stmt = (
            select(HealthRecord)
            .options(selectinload(HealthRecord.family_member))
            .where(HealthRecord.id == record_id)
        )
        if user_id is not None:
            stmt = stmt.where(HealthRecord.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_health_records_by_user(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[HealthRecord]:
        """Get health records for a user with optional filtering.
        
        Validates: Requirements 14.1, 14.2, 14.5
        
        Args:
            user_id: User's UUID
            category: Optional category filter
            family_member_id: Optional family member filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of HealthRecord model instances
        """
        stmt = select(HealthRecord).where(HealthRecord.user_id == user_id)
        
        if category is not None:
            stmt = stmt.where(HealthRecord.category == category)
        
        if family_member_id is not None:
            stmt = stmt.where(HealthRecord.family_member_id == family_member_id)
        
        if start_date is not None:
            stmt = stmt.where(HealthRecord.record_date >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(HealthRecord.record_date <= end_date)
        
        stmt = stmt.order_by(HealthRecord.record_date.desc().nullslast(), HealthRecord.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_health_records(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """Count total health records for a user with optional filtering.
        
        Args:
            user_id: User's UUID
            category: Optional category filter
            family_member_id: Optional family member filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Total count of health records
        """
        stmt = select(func.count(HealthRecord.id)).where(HealthRecord.user_id == user_id)
        
        if category is not None:
            stmt = stmt.where(HealthRecord.category == category)
        
        if family_member_id is not None:
            stmt = stmt.where(HealthRecord.family_member_id == family_member_id)
        
        if start_date is not None:
            stmt = stmt.where(HealthRecord.record_date >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(HealthRecord.record_date <= end_date)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def search_health_records(
        self,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[HealthRecord]:
        """Search health records by full-text search.
        
        Validates: Requirements 14.6
        
        Searches across:
        - Record title
        - Doctor name
        - Hospital name
        - OCR extracted text
        - Notes
        
        Args:
            user_id: User's UUID
            query: Search query string
            category: Optional category filter
            family_member_id: Optional family member filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching HealthRecord model instances
        """
        search_term = f"%{query.lower()}%"
        
        stmt = select(HealthRecord).where(
            HealthRecord.user_id == user_id,
            or_(
                func.lower(HealthRecord.title).like(search_term),
                func.lower(HealthRecord.doctor_name).like(search_term),
                func.lower(HealthRecord.hospital_name).like(search_term),
                func.lower(HealthRecord.ocr_text).like(search_term),
                func.lower(HealthRecord.notes).like(search_term),
            )
        )
        
        if category is not None:
            stmt = stmt.where(HealthRecord.category == category)
        
        if family_member_id is not None:
            stmt = stmt.where(HealthRecord.family_member_id == family_member_id)
        
        stmt = stmt.order_by(HealthRecord.record_date.desc().nullslast(), HealthRecord.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_search_results(
        self,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
    ) -> int:
        """Count total search results for pagination.
        
        Args:
            user_id: User's UUID
            query: Search query string
            category: Optional category filter
            family_member_id: Optional family member filter
            
        Returns:
            Total count of matching health records
        """
        search_term = f"%{query.lower()}%"
        
        stmt = select(func.count(HealthRecord.id)).where(
            HealthRecord.user_id == user_id,
            or_(
                func.lower(HealthRecord.title).like(search_term),
                func.lower(HealthRecord.doctor_name).like(search_term),
                func.lower(HealthRecord.hospital_name).like(search_term),
                func.lower(HealthRecord.ocr_text).like(search_term),
                func.lower(HealthRecord.notes).like(search_term),
            )
        )
        
        if category is not None:
            stmt = stmt.where(HealthRecord.category == category)
        
        if family_member_id is not None:
            stmt = stmt.where(HealthRecord.family_member_id == family_member_id)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_health_record(
        self,
        health_record: HealthRecord,
        data: HealthRecordUpdate,
    ) -> HealthRecord:
        """Update a health record.
        
        Args:
            health_record: Existing HealthRecord model instance
            data: Health record update data
            
        Returns:
            Updated HealthRecord model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(health_record, field, value)
        
        await self.db.flush()
        await self.db.refresh(health_record)
        return health_record
    
    async def update_ocr_data(
        self,
        health_record: HealthRecord,
        ocr_text: str,
        extracted_data: Optional[dict] = None,
    ) -> HealthRecord:
        """Update the OCR data for a health record.
        
        Args:
            health_record: HealthRecord model instance
            ocr_text: Extracted OCR text
            extracted_data: Optional structured data from OCR
            
        Returns:
            Updated HealthRecord model instance
        """
        health_record.ocr_text = ocr_text
        if extracted_data is not None:
            health_record.extracted_data = extracted_data
        
        await self.db.flush()
        await self.db.refresh(health_record)
        return health_record
    
    async def delete_health_record(self, health_record: HealthRecord) -> None:
        """Delete a health record.
        
        Args:
            health_record: HealthRecord model instance to delete
        """
        await self.db.delete(health_record)
        await self.db.flush()
    
    async def get_health_timeline(
        self,
        user_id: UUID,
        family_member_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[HealthRecord]:
        """Get health records as a chronological timeline.
        
        Validates: Requirements 14.5, 14.6
        
        Returns health records ordered by record_date (descending), then by
        created_at (descending) for records without a record_date.
        
        Args:
            user_id: User's UUID
            family_member_id: Optional family member filter (None for all)
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of HealthRecord model instances in chronological order
        """
        stmt = (
            select(HealthRecord)
            .options(selectinload(HealthRecord.family_member))
            .where(HealthRecord.user_id == user_id)
        )
        
        if family_member_id is not None:
            stmt = stmt.where(HealthRecord.family_member_id == family_member_id)
        
        # Order by record_date descending (nulls last), then by created_at descending
        stmt = stmt.order_by(
            HealthRecord.record_date.desc().nullslast(),
            HealthRecord.created_at.desc()
        )
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_timeline_records(
        self,
        user_id: UUID,
        family_member_id: Optional[UUID] = None,
    ) -> int:
        """Count total timeline records for pagination.
        
        Args:
            user_id: User's UUID
            family_member_id: Optional family member filter
            
        Returns:
            Total count of health records
        """
        stmt = select(func.count(HealthRecord.id)).where(HealthRecord.user_id == user_id)
        
        if family_member_id is not None:
            stmt = stmt.where(HealthRecord.family_member_id == family_member_id)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
