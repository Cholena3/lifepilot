"""Repository for Badge database operations.

Requirement 33.5: Award badges for achievements and milestones
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import Badge, BadgeType, BADGE_METADATA


class BadgeRepository:
    """Repository for Badge CRUD operations.
    
    Requirement 33.5: Award badges for achievements and milestones
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def award_badge(
        self,
        user_id: uuid.UUID,
        badge_type: BadgeType,
    ) -> tuple[Badge, bool]:
        """Award a badge to a user if not already earned.
        
        Requirement 33.5: Award badges for achievements and milestones
        
        Args:
            user_id: User's UUID
            badge_type: Type of badge to award
            
        Returns:
            Tuple of (Badge, already_earned) where already_earned is True
            if the badge was already earned
        """
        # Check if badge already exists
        existing = await self.get_badge_by_type(user_id, badge_type)
        if existing:
            return existing, True
        
        # Get badge metadata
        metadata = BADGE_METADATA.get(badge_type, {
            "name": badge_type.value.replace("_", " ").title(),
            "description": f"Earned the {badge_type.value} badge",
        })
        
        # Create new badge
        badge = Badge(
            user_id=user_id,
            badge_type=badge_type.value,
            name=metadata["name"],
            description=metadata["description"],
            earned_at=datetime.now(timezone.utc),
        )
        self.session.add(badge)
        await self.session.flush()
        return badge, False

    async def get_badge_by_type(
        self,
        user_id: uuid.UUID,
        badge_type: BadgeType,
    ) -> Optional[Badge]:
        """Get a specific badge for a user.
        
        Args:
            user_id: User's UUID
            badge_type: Type of badge to find
            
        Returns:
            Badge if found, None otherwise
        """
        query = select(Badge).where(
            and_(
                Badge.user_id == user_id,
                Badge.badge_type == badge_type.value,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_badges(
        self,
        user_id: uuid.UUID,
    ) -> list[Badge]:
        """Get all badges for a user.
        
        Requirement 33.5: Award badges for achievements and milestones
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of Badge instances
        """
        query = (
            select(Badge)
            .where(Badge.user_id == user_id)
            .order_by(Badge.earned_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_badge_count(
        self,
        user_id: uuid.UUID,
    ) -> int:
        """Get the count of badges for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of badges earned
        """
        query = select(func.count(Badge.id)).where(Badge.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def has_badge(
        self,
        user_id: uuid.UUID,
        badge_type: BadgeType,
    ) -> bool:
        """Check if a user has a specific badge.
        
        Args:
            user_id: User's UUID
            badge_type: Type of badge to check
            
        Returns:
            True if user has the badge, False otherwise
        """
        badge = await self.get_badge_by_type(user_id, badge_type)
        return badge is not None

    async def get_recent_badges(
        self,
        user_id: uuid.UUID,
        limit: int = 5,
    ) -> list[Badge]:
        """Get the most recently earned badges for a user.
        
        Args:
            user_id: User's UUID
            limit: Maximum number of badges to return
            
        Returns:
            List of most recent Badge instances
        """
        query = (
            select(Badge)
            .where(Badge.user_id == user_id)
            .order_by(Badge.earned_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_badge(
        self,
        user_id: uuid.UUID,
        badge_type: BadgeType,
    ) -> bool:
        """Delete a badge from a user (for testing/admin purposes).
        
        Args:
            user_id: User's UUID
            badge_type: Type of badge to delete
            
        Returns:
            True if badge was deleted, False if not found
        """
        from sqlalchemy import delete
        
        stmt = delete(Badge).where(
            and_(
                Badge.user_id == user_id,
                Badge.badge_type == badge_type.value,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
