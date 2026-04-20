"""Repository for Weekly Summary database operations.

Requirement 34: Weekly Summary
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weekly_summary import WeeklySummary


class WeeklySummaryRepository:
    """Repository for Weekly Summary CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update_summary(
        self,
        user_id: uuid.UUID,
        week_start: date,
        week_end: date,
        metrics: dict,
        comparisons: dict,
        generated_at: datetime,
    ) -> WeeklySummary:
        """Create or update a weekly summary.
        
        Requirement 34.1: Generate summary of activities across all modules
        """
        # Check if summary exists for this week
        existing = await self.get_summary_by_week(user_id, week_start)
        
        if existing:
            # Update existing summary
            existing.week_end = week_end
            existing.metrics = metrics
            existing.comparisons = comparisons
            existing.generated_at = generated_at
            await self.session.flush()
            return existing
        
        # Create new summary
        summary = WeeklySummary(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            metrics=metrics,
            comparisons=comparisons,
            generated_at=generated_at,
        )
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def get_summary_by_week(
        self,
        user_id: uuid.UUID,
        week_start: date,
    ) -> Optional[WeeklySummary]:
        """Get weekly summary for a specific week."""
        query = select(WeeklySummary).where(
            and_(
                WeeklySummary.user_id == user_id,
                WeeklySummary.week_start == week_start,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_summary_by_id(
        self,
        summary_id: uuid.UUID,
    ) -> Optional[WeeklySummary]:
        """Get weekly summary by ID."""
        query = select(WeeklySummary).where(WeeklySummary.id == summary_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_summary(
        self,
        user_id: uuid.UUID,
    ) -> Optional[WeeklySummary]:
        """Get the most recent weekly summary for a user."""
        query = (
            select(WeeklySummary)
            .where(WeeklySummary.user_id == user_id)
            .order_by(WeeklySummary.week_start.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_summaries_paginated(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[WeeklySummary], int]:
        """Get paginated weekly summaries for a user.
        
        Requirement 34.5: View past weekly summaries
        """
        # Count query
        count_query = select(func.count(WeeklySummary.id)).where(
            WeeklySummary.user_id == user_id
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        offset = (page - 1) * page_size
        query = (
            select(WeeklySummary)
            .where(WeeklySummary.user_id == user_id)
            .order_by(WeeklySummary.week_start.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        summaries = list(result.scalars().all())

        return summaries, total

    async def get_summaries_in_range(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> list[WeeklySummary]:
        """Get weekly summaries within a date range."""
        query = (
            select(WeeklySummary)
            .where(
                and_(
                    WeeklySummary.user_id == user_id,
                    WeeklySummary.week_start >= start_date,
                    WeeklySummary.week_start <= end_date,
                )
            )
            .order_by(WeeklySummary.week_start.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_summary(
        self,
        summary_id: uuid.UUID,
    ) -> bool:
        """Delete a weekly summary."""
        summary = await self.get_summary_by_id(summary_id)
        if summary:
            await self.session.delete(summary)
            await self.session.flush()
            return True
        return False

    async def get_all_user_ids_with_activity(self) -> list[uuid.UUID]:
        """Get all user IDs that have any activity (for batch summary generation)."""
        from app.models.user import User
        
        query = select(User.id)
        result = await self.session.execute(query)
        return [row[0] for row in result.all()]
