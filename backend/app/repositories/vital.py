"""Vital repository for database operations.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

from datetime import datetime, date, time, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import and_, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.vital import Vital, VitalTargetRange, DEFAULT_VITAL_RANGES
from app.schemas.vital import VitalCreate, VitalUpdate, VitalTargetRangeCreate, VitalTargetRangeUpdate


class VitalRepository:
    """Repository for Vital module database operations.
    
    Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    # ========================================================================
    # Vital Operations
    # ========================================================================
    
    async def create_vital(
        self,
        user_id: UUID,
        data: VitalCreate,
    ) -> Vital:
        """Create a new vital reading.
        
        Validates: Requirements 16.1
        
        Args:
            user_id: User's UUID
            data: Vital creation data
            
        Returns:
            Created Vital model instance
        """
        vital = Vital(
            user_id=user_id,
            family_member_id=data.family_member_id,
            vital_type=data.vital_type,
            value=data.value,
            unit=data.unit,
            notes=data.notes,
            recorded_at=data.recorded_at or datetime.now(timezone.utc),
        )
        self.db.add(vital)
        await self.db.flush()
        await self.db.refresh(vital)
        return vital
    
    async def get_vital_by_id(
        self,
        vital_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Vital]:
        """Get a vital by ID.
        
        Args:
            vital_id: Vital's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            Vital if found, None otherwise
        """
        stmt = select(Vital).where(Vital.id == vital_id)
        if user_id is not None:
            stmt = stmt.where(Vital.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_vitals_by_user(
        self,
        user_id: UUID,
        vital_type: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Vital]:
        """Get vitals for a user with optional filtering.
        
        Args:
            user_id: User's UUID
            vital_type: Optional vital type filter
            family_member_id: Optional family member filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Vital model instances
        """
        stmt = select(Vital).where(Vital.user_id == user_id)
        
        if vital_type is not None:
            stmt = stmt.where(Vital.vital_type == vital_type)
        
        if family_member_id is not None:
            stmt = stmt.where(Vital.family_member_id == family_member_id)
        else:
            # If no family_member_id specified, get user's own vitals
            stmt = stmt.where(Vital.family_member_id.is_(None))
        
        if start_date is not None:
            stmt = stmt.where(Vital.recorded_at >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(Vital.recorded_at <= end_date)
        
        stmt = stmt.order_by(desc(Vital.recorded_at)).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_vitals_for_all_members(
        self,
        user_id: UUID,
        vital_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Vital]:
        """Get vitals for user and all family members.
        
        Args:
            user_id: User's UUID
            vital_type: Optional vital type filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Vital model instances
        """
        stmt = (
            select(Vital)
            .where(Vital.user_id == user_id)
            .options(selectinload(Vital.family_member))
        )
        
        if vital_type is not None:
            stmt = stmt.where(Vital.vital_type == vital_type)
        
        if start_date is not None:
            stmt = stmt.where(Vital.recorded_at >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(Vital.recorded_at <= end_date)
        
        stmt = stmt.order_by(desc(Vital.recorded_at)).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_vitals(
        self,
        user_id: UUID,
        vital_type: Optional[str] = None,
        family_member_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Count total vitals for a user.
        
        Args:
            user_id: User's UUID
            vital_type: Optional vital type filter
            family_member_id: Optional family member filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Total count of vitals
        """
        stmt = select(func.count(Vital.id)).where(Vital.user_id == user_id)
        
        if vital_type is not None:
            stmt = stmt.where(Vital.vital_type == vital_type)
        
        if family_member_id is not None:
            stmt = stmt.where(Vital.family_member_id == family_member_id)
        else:
            stmt = stmt.where(Vital.family_member_id.is_(None))
        
        if start_date is not None:
            stmt = stmt.where(Vital.recorded_at >= start_date)
        
        if end_date is not None:
            stmt = stmt.where(Vital.recorded_at <= end_date)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_vital(
        self,
        vital: Vital,
        data: VitalUpdate,
    ) -> Vital:
        """Update a vital reading.
        
        Args:
            vital: Existing Vital model instance
            data: Vital update data
            
        Returns:
            Updated Vital model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vital, field, value)
        
        await self.db.flush()
        await self.db.refresh(vital)
        return vital
    
    async def delete_vital(self, vital: Vital) -> None:
        """Delete a vital reading.
        
        Args:
            vital: Vital model instance to delete
        """
        await self.db.delete(vital)
        await self.db.flush()
    
    async def get_vital_statistics(
        self,
        user_id: UUID,
        vital_type: str,
        family_member_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get statistics for a vital type.
        
        Validates: Requirements 16.2
        
        Args:
            user_id: User's UUID
            vital_type: Type of vital
            family_member_id: Optional family member filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dict with min, max, avg values
        """
        conditions = [
            Vital.user_id == user_id,
            Vital.vital_type == vital_type,
        ]
        
        if family_member_id is not None:
            conditions.append(Vital.family_member_id == family_member_id)
        else:
            conditions.append(Vital.family_member_id.is_(None))
        
        if start_date is not None:
            conditions.append(Vital.recorded_at >= start_date)
        if end_date is not None:
            conditions.append(Vital.recorded_at <= end_date)
        
        stmt = select(
            func.min(Vital.value).label("min_value"),
            func.max(Vital.value).label("max_value"),
            func.avg(Vital.value).label("avg_value"),
            func.count(Vital.id).label("count"),
        ).where(and_(*conditions))
        
        result = await self.db.execute(stmt)
        row = result.one()
        
        return {
            "min_value": row.min_value,
            "max_value": row.max_value,
            "avg_value": round(row.avg_value, 2) if row.avg_value else None,
            "count": row.count or 0,
        }
    
    async def get_latest_vital(
        self,
        user_id: UUID,
        vital_type: str,
        family_member_id: Optional[UUID] = None,
    ) -> Optional[Vital]:
        """Get the latest vital reading of a specific type.
        
        Args:
            user_id: User's UUID
            vital_type: Type of vital
            family_member_id: Optional family member filter
            
        Returns:
            Latest Vital if found, None otherwise
        """
        conditions = [
            Vital.user_id == user_id,
            Vital.vital_type == vital_type,
        ]
        
        if family_member_id is not None:
            conditions.append(Vital.family_member_id == family_member_id)
        else:
            conditions.append(Vital.family_member_id.is_(None))
        
        stmt = (
            select(Vital)
            .where(and_(*conditions))
            .order_by(desc(Vital.recorded_at))
            .limit(1)
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    # ========================================================================
    # Target Range Operations
    # ========================================================================
    
    async def create_target_range(
        self,
        user_id: UUID,
        data: VitalTargetRangeCreate,
    ) -> VitalTargetRange:
        """Create a custom target range.
        
        Validates: Requirements 16.4
        
        Args:
            user_id: User's UUID
            data: Target range creation data
            
        Returns:
            Created VitalTargetRange model instance
        """
        target_range = VitalTargetRange(
            user_id=user_id,
            family_member_id=data.family_member_id,
            vital_type=data.vital_type,
            min_value=data.min_value,
            max_value=data.max_value,
        )
        self.db.add(target_range)
        await self.db.flush()
        await self.db.refresh(target_range)
        return target_range
    
    async def get_target_range_by_id(
        self,
        range_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[VitalTargetRange]:
        """Get a target range by ID.
        
        Args:
            range_id: Target range's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            VitalTargetRange if found, None otherwise
        """
        stmt = select(VitalTargetRange).where(VitalTargetRange.id == range_id)
        if user_id is not None:
            stmt = stmt.where(VitalTargetRange.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_target_range(
        self,
        user_id: UUID,
        vital_type: str,
        family_member_id: Optional[UUID] = None,
    ) -> Optional[VitalTargetRange]:
        """Get target range for a specific vital type.
        
        Validates: Requirements 16.4
        
        Args:
            user_id: User's UUID
            vital_type: Type of vital
            family_member_id: Optional family member filter
            
        Returns:
            VitalTargetRange if found, None otherwise
        """
        conditions = [
            VitalTargetRange.user_id == user_id,
            VitalTargetRange.vital_type == vital_type,
        ]
        
        if family_member_id is not None:
            conditions.append(VitalTargetRange.family_member_id == family_member_id)
        else:
            conditions.append(VitalTargetRange.family_member_id.is_(None))
        
        stmt = select(VitalTargetRange).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_target_ranges_by_user(
        self,
        user_id: UUID,
        family_member_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[VitalTargetRange]:
        """Get all target ranges for a user.
        
        Args:
            user_id: User's UUID
            family_member_id: Optional family member filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of VitalTargetRange model instances
        """
        stmt = select(VitalTargetRange).where(VitalTargetRange.user_id == user_id)
        
        if family_member_id is not None:
            stmt = stmt.where(VitalTargetRange.family_member_id == family_member_id)
        else:
            stmt = stmt.where(VitalTargetRange.family_member_id.is_(None))
        
        stmt = stmt.order_by(VitalTargetRange.vital_type).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_target_ranges(
        self,
        user_id: UUID,
        family_member_id: Optional[UUID] = None,
    ) -> int:
        """Count total target ranges for a user.
        
        Args:
            user_id: User's UUID
            family_member_id: Optional family member filter
            
        Returns:
            Total count of target ranges
        """
        stmt = select(func.count(VitalTargetRange.id)).where(
            VitalTargetRange.user_id == user_id
        )
        
        if family_member_id is not None:
            stmt = stmt.where(VitalTargetRange.family_member_id == family_member_id)
        else:
            stmt = stmt.where(VitalTargetRange.family_member_id.is_(None))
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_target_range(
        self,
        target_range: VitalTargetRange,
        data: VitalTargetRangeUpdate,
    ) -> VitalTargetRange:
        """Update a target range.
        
        Args:
            target_range: Existing VitalTargetRange model instance
            data: Target range update data
            
        Returns:
            Updated VitalTargetRange model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(target_range, field, value)
        
        await self.db.flush()
        await self.db.refresh(target_range)
        return target_range
    
    async def delete_target_range(self, target_range: VitalTargetRange) -> None:
        """Delete a target range.
        
        Args:
            target_range: VitalTargetRange model instance to delete
        """
        await self.db.delete(target_range)
        await self.db.flush()
    
    async def upsert_target_range(
        self,
        user_id: UUID,
        data: VitalTargetRangeCreate,
    ) -> VitalTargetRange:
        """Create or update a target range.
        
        Validates: Requirements 16.4
        
        Args:
            user_id: User's UUID
            data: Target range data
            
        Returns:
            Created or updated VitalTargetRange model instance
        """
        existing = await self.get_target_range(
            user_id, data.vital_type, data.family_member_id
        )
        
        if existing:
            update_data = VitalTargetRangeUpdate(
                min_value=data.min_value,
                max_value=data.max_value,
            )
            return await self.update_target_range(existing, update_data)
        else:
            return await self.create_target_range(user_id, data)
