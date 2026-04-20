"""Health record share repository for database operations.

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_share import HealthRecordShare, HealthShareAccessLog
from app.schemas.health_share import HealthRecordShareCreate, HealthRecordShareUpdate


class HealthShareRepository:
    """Repository for health record share database operations.
    
    Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    # ========================================================================
    # Health Record Share Operations
    # ========================================================================
    
    async def create(
        self,
        user_id: UUID,
        data: HealthRecordShareCreate,
        expires_at: datetime,
    ) -> HealthRecordShare:
        """Create a new health record share.
        
        Validates: Requirements 18.1, 18.2
        
        Args:
            user_id: User's UUID
            data: Share creation data
            expires_at: Expiration datetime
            
        Returns:
            Created HealthRecordShare model instance
        """
        # Convert UUIDs to strings for JSON storage
        record_ids_str = [str(rid) for rid in data.record_ids]
        
        share = HealthRecordShare(
            user_id=user_id,
            record_ids=record_ids_str,
            doctor_name=data.doctor_name,
            doctor_email=data.doctor_email,
            purpose=data.purpose,
            expires_at=expires_at,
            notes=data.notes,
        )
        self.db.add(share)
        await self.db.flush()
        await self.db.refresh(share)
        return share
    
    async def get_by_id(
        self,
        share_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[HealthRecordShare]:
        """Get a health record share by ID.
        
        Args:
            share_id: Share's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            HealthRecordShare if found, None otherwise
        """
        stmt = select(HealthRecordShare).where(HealthRecordShare.id == share_id)
        if user_id is not None:
            stmt = stmt.where(HealthRecordShare.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_token(self, token: str) -> Optional[HealthRecordShare]:
        """Get a health record share by public token.
        
        Validates: Requirements 18.3
        
        Args:
            token: Public access token
            
        Returns:
            HealthRecordShare if found, None otherwise
        """
        stmt = select(HealthRecordShare).where(
            HealthRecordShare.public_token == token
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        user_id: UUID,
        include_expired: bool = False,
        include_revoked: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[HealthRecordShare]:
        """Get all health record shares for a user.
        
        Validates: Requirements 18.1
        
        Args:
            user_id: User's UUID
            include_expired: Whether to include expired shares
            include_revoked: Whether to include revoked shares
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of HealthRecordShare model instances
        """
        stmt = select(HealthRecordShare).where(HealthRecordShare.user_id == user_id)
        
        if not include_revoked:
            stmt = stmt.where(HealthRecordShare.is_revoked == False)
        
        if not include_expired:
            stmt = stmt.where(HealthRecordShare.expires_at > datetime.now(timezone.utc))
        
        stmt = stmt.order_by(HealthRecordShare.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_by_user(
        self,
        user_id: UUID,
        include_expired: bool = False,
        include_revoked: bool = False,
    ) -> int:
        """Count total health record shares for a user.
        
        Args:
            user_id: User's UUID
            include_expired: Whether to include expired shares
            include_revoked: Whether to include revoked shares
            
        Returns:
            Total count of shares
        """
        stmt = select(func.count(HealthRecordShare.id)).where(
            HealthRecordShare.user_id == user_id
        )
        
        if not include_revoked:
            stmt = stmt.where(HealthRecordShare.is_revoked == False)
        
        if not include_expired:
            stmt = stmt.where(HealthRecordShare.expires_at > datetime.now(timezone.utc))
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update(
        self,
        share: HealthRecordShare,
        data: HealthRecordShareUpdate,
    ) -> HealthRecordShare:
        """Update a health record share.
        
        Args:
            share: Existing HealthRecordShare model instance
            data: Share update data
            
        Returns:
            Updated HealthRecordShare model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(share, field, value)
        
        await self.db.flush()
        await self.db.refresh(share)
        return share
    
    async def revoke(self, share: HealthRecordShare) -> HealthRecordShare:
        """Revoke a health record share.
        
        Validates: Requirements 18.4
        
        Args:
            share: HealthRecordShare model instance to revoke
            
        Returns:
            Revoked HealthRecordShare model instance
        """
        share.is_revoked = True
        await self.db.flush()
        await self.db.refresh(share)
        return share
    
    async def delete(self, share: HealthRecordShare) -> None:
        """Delete a health record share.
        
        Args:
            share: HealthRecordShare model instance to delete
        """
        await self.db.delete(share)
        await self.db.flush()
    
    async def increment_access_count(
        self,
        share: HealthRecordShare,
    ) -> HealthRecordShare:
        """Increment the access count for a share.
        
        Validates: Requirements 18.5
        
        Args:
            share: HealthRecordShare model instance
            
        Returns:
            Updated HealthRecordShare model instance
        """
        share.access_count += 1
        share.last_accessed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(share)
        return share
    
    # ========================================================================
    # Access Log Operations
    # ========================================================================
    
    async def create_access_log(
        self,
        share_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> HealthShareAccessLog:
        """Create an access log entry for a share.
        
        Validates: Requirements 18.5
        
        Args:
            share_id: Share's UUID
            ip_address: IP address of the accessor
            user_agent: User agent string
            
        Returns:
            Created HealthShareAccessLog model instance
        """
        access_log = HealthShareAccessLog(
            share_id=share_id,
            ip_address=ip_address,
            user_agent=user_agent,
            accessed_at=datetime.now(timezone.utc),
        )
        self.db.add(access_log)
        await self.db.flush()
        await self.db.refresh(access_log)
        return access_log
    
    async def get_access_logs(
        self,
        share_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[HealthShareAccessLog]:
        """Get access logs for a share.
        
        Validates: Requirements 18.5
        
        Args:
            share_id: Share's UUID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of HealthShareAccessLog model instances
        """
        stmt = (
            select(HealthShareAccessLog)
            .where(HealthShareAccessLog.share_id == share_id)
            .order_by(HealthShareAccessLog.accessed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_access_logs(self, share_id: UUID) -> int:
        """Count total access logs for a share.
        
        Args:
            share_id: Share's UUID
            
        Returns:
            Total count of access logs
        """
        stmt = select(func.count(HealthShareAccessLog.id)).where(
            HealthShareAccessLog.share_id == share_id
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
