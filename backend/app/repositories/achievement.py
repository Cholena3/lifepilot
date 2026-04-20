"""Repository for achievement database operations.

Requirement 29: Achievement Logging
"""

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import func, select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement, AchievementCategory


class AchievementRepository:
    """Repository for Achievement CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_achievement(
        self,
        user_id: uuid.UUID,
        title: str,
        achieved_date: date,
        category: AchievementCategory,
        description: Optional[str] = None,
        document_ids: Optional[list[uuid.UUID]] = None,
    ) -> Achievement:
        """Create a new achievement for a user.
        
        Requirement 29.1: Store title, description, date, and category
        Requirement 29.3: Allow attaching supporting documents
        """
        achievement = Achievement(
            user_id=user_id,
            title=title,
            description=description,
            achieved_date=achieved_date,
            category=category,
            document_ids=document_ids or [],
        )
        self.session.add(achievement)
        await self.session.flush()
        return achievement

    async def get_achievement_by_id(
        self,
        achievement_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Achievement]:
        """Get an achievement by ID for a specific user."""
        query = select(Achievement).where(
            Achievement.id == achievement_id,
            Achievement.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_achievements(
        self,
        user_id: uuid.UUID,
        category: Optional[AchievementCategory] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Achievement], int]:
        """Get achievements for a user with optional filtering and pagination.
        
        Requirement 29.5: Display achievements on a timeline view (chronological order)
        """
        query = select(Achievement).where(Achievement.user_id == user_id)
        count_query = select(func.count(Achievement.id)).where(Achievement.user_id == user_id)

        if category:
            query = query.where(Achievement.category == category)
            count_query = count_query.where(Achievement.category == category)

        if start_date:
            query = query.where(Achievement.achieved_date >= start_date)
            count_query = count_query.where(Achievement.achieved_date >= start_date)

        if end_date:
            query = query.where(Achievement.achieved_date <= end_date)
            count_query = count_query.where(Achievement.achieved_date <= end_date)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering (chronological - most recent first)
        query = query.order_by(Achievement.achieved_date.desc(), Achievement.created_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        achievements = list(result.scalars().all())

        return achievements, total

    async def get_all_achievements(self, user_id: uuid.UUID) -> list[Achievement]:
        """Get all achievements for a user without pagination.
        
        Requirement 29.5: Display achievements on a timeline view
        """
        query = (
            select(Achievement)
            .where(Achievement.user_id == user_id)
            .order_by(Achievement.achieved_date.desc(), Achievement.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_achievements_timeline(
        self,
        user_id: uuid.UUID,
        category: Optional[AchievementCategory] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[int, list[Achievement]]:
        """Get achievements grouped by year for timeline view.
        
        Requirement 29.5: Display achievements on a timeline view
        """
        query = select(Achievement).where(Achievement.user_id == user_id)

        if category:
            query = query.where(Achievement.category == category)

        if start_date:
            query = query.where(Achievement.achieved_date >= start_date)

        if end_date:
            query = query.where(Achievement.achieved_date <= end_date)

        query = query.order_by(Achievement.achieved_date.desc())

        result = await self.session.execute(query)
        achievements = list(result.scalars().all())

        # Group by year
        timeline: dict[int, list[Achievement]] = {}
        for achievement in achievements:
            year = achievement.achieved_date.year
            if year not in timeline:
                timeline[year] = []
            timeline[year].append(achievement)

        return timeline

    async def get_achievements_by_category(
        self,
        user_id: uuid.UUID,
    ) -> dict[AchievementCategory, list[Achievement]]:
        """Get achievements grouped by category."""
        achievements = await self.get_all_achievements(user_id)
        
        grouped: dict[AchievementCategory, list[Achievement]] = {}
        for achievement in achievements:
            if achievement.category not in grouped:
                grouped[achievement.category] = []
            grouped[achievement.category].append(achievement)
        
        return grouped

    async def update_achievement(
        self,
        achievement: Achievement,
        **kwargs,
    ) -> Achievement:
        """Update an achievement's attributes."""
        for key, value in kwargs.items():
            if hasattr(achievement, key):
                setattr(achievement, key, value)
        await self.session.flush()
        return achievement

    async def delete_achievement(self, achievement: Achievement) -> None:
        """Delete an achievement."""
        await self.session.delete(achievement)
        await self.session.flush()

    async def get_recent_achievements(
        self,
        user_id: uuid.UUID,
        limit: int = 5,
    ) -> list[Achievement]:
        """Get most recent achievements for a user.
        
        Useful for resume suggestions (Requirement 29.4).
        """
        query = (
            select(Achievement)
            .where(Achievement.user_id == user_id)
            .order_by(Achievement.achieved_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_achievements_by_categories(
        self,
        user_id: uuid.UUID,
        categories: list[AchievementCategory],
        limit: int = 10,
    ) -> list[Achievement]:
        """Get achievements filtered by multiple categories.
        
        Useful for resume suggestions (Requirement 29.4).
        """
        query = (
            select(Achievement)
            .where(
                Achievement.user_id == user_id,
                Achievement.category.in_(categories),
            )
            .order_by(Achievement.achieved_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
