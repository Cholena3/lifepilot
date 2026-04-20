"""Share link repository for database operations.

Validates: Requirements 9.1, 9.2, 9.4, 9.5, 9.6
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.share_link import ShareLink, ShareLinkAccess


class ShareLinkRepository:
    """Repository for ShareLink database operations.
    
    Validates: Requirements 9.1, 9.2, 9.4, 9.5, 9.6
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create_share_link(
        self,
        document_id: UUID,
        user_id: UUID,
        token: str,
        expires_at: datetime,
        password_hash: Optional[str] = None,
    ) -> ShareLink:
        """Create a new share link.
        
        Validates: Requirements 9.1, 9.2
        
        Args:
            document_id: Document's UUID
            user_id: User's UUID
            token: Unique share token
            expires_at: Expiration timestamp
            password_hash: Optional bcrypt password hash
            
        Returns:
            Created ShareLink model instance
        """
        share_link = ShareLink(
            document_id=document_id,
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            password_hash=password_hash,
            is_revoked=False,
        )
        self.db.add(share_link)
        await self.db.flush()
        await self.db.refresh(share_link)
        return share_link
    
    async def get_share_link_by_id(
        self,
        share_link_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[ShareLink]:
        """Get a share link by ID.
        
        Args:
            share_link_id: ShareLink's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            ShareLink if found, None otherwise
        """
        stmt = select(ShareLink).where(ShareLink.id == share_link_id)
        if user_id is not None:
            stmt = stmt.where(ShareLink.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_share_link_by_token(
        self,
        token: str,
    ) -> Optional[ShareLink]:
        """Get a share link by token.
        
        Validates: Requirements 9.4, 9.5
        
        Args:
            token: Share link token
            
        Returns:
            ShareLink if found, None otherwise
        """
        stmt = (
            select(ShareLink)
            .where(ShareLink.token == token)
            .options(selectinload(ShareLink.document))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_share_links_by_document(
        self,
        document_id: UUID,
        user_id: UUID,
        include_revoked: bool = False,
    ) -> List[ShareLink]:
        """Get all share links for a document.
        
        Args:
            document_id: Document's UUID
            user_id: User's UUID (for ownership verification)
            include_revoked: Whether to include revoked links
            
        Returns:
            List of ShareLink model instances
        """
        stmt = (
            select(ShareLink)
            .where(
                ShareLink.document_id == document_id,
                ShareLink.user_id == user_id,
            )
            .order_by(ShareLink.created_at.desc())
        )
        
        if not include_revoked:
            stmt = stmt.where(ShareLink.is_revoked == False)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_share_links_by_user(
        self,
        user_id: UUID,
        include_revoked: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ShareLink]:
        """Get all share links created by a user.
        
        Args:
            user_id: User's UUID
            include_revoked: Whether to include revoked links
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of ShareLink model instances
        """
        stmt = (
            select(ShareLink)
            .where(ShareLink.user_id == user_id)
            .order_by(ShareLink.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        if not include_revoked:
            stmt = stmt.where(ShareLink.is_revoked == False)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def revoke_share_link(
        self,
        share_link: ShareLink,
    ) -> ShareLink:
        """Revoke a share link.
        
        Validates: Requirements 9.5
        
        Args:
            share_link: ShareLink model instance
            
        Returns:
            Updated ShareLink model instance
        """
        share_link.is_revoked = True
        await self.db.flush()
        await self.db.refresh(share_link)
        return share_link
    
    async def delete_share_link(
        self,
        share_link: ShareLink,
    ) -> None:
        """Delete a share link.
        
        Args:
            share_link: ShareLink model instance to delete
        """
        await self.db.delete(share_link)
        await self.db.flush()
    
    async def log_access(
        self,
        share_link_id: UUID,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> ShareLinkAccess:
        """Log an access to a share link.
        
        Validates: Requirements 9.6
        
        Args:
            share_link_id: ShareLink's UUID
            ip_address: IP address of the accessor
            user_agent: User agent string
            
        Returns:
            Created ShareLinkAccess model instance
        """
        access_log = ShareLinkAccess(
            share_link_id=share_link_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(access_log)
        await self.db.flush()
        await self.db.refresh(access_log)
        return access_log
    
    async def get_access_logs(
        self,
        share_link_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ShareLinkAccess]:
        """Get access logs for a share link.
        
        Validates: Requirements 9.6
        
        Args:
            share_link_id: ShareLink's UUID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of ShareLinkAccess model instances
        """
        stmt = (
            select(ShareLinkAccess)
            .where(ShareLinkAccess.share_link_id == share_link_id)
            .order_by(ShareLinkAccess.accessed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_accesses(
        self,
        share_link_id: UUID,
    ) -> int:
        """Count total accesses for a share link.
        
        Args:
            share_link_id: ShareLink's UUID
            
        Returns:
            Total count of accesses
        """
        stmt = (
            select(func.count(ShareLinkAccess.id))
            .where(ShareLinkAccess.share_link_id == share_link_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def token_exists(self, token: str) -> bool:
        """Check if a token already exists.
        
        Args:
            token: Token to check
            
        Returns:
            True if token exists, False otherwise
        """
        stmt = select(func.count(ShareLink.id)).where(ShareLink.token == token)
        result = await self.db.execute(stmt)
        count = result.scalar() or 0
        return count > 0
