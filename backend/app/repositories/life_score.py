"""Repository for Life Score database operations.

Requirement 33: Life Score Gamification
"""

import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.life_score import LifeScore


class LifeScoreRepository:
    """Repository for Life Score CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update_score(
        self,
        user_id: uuid.UUID,
        score_date: date,
        total_score: int,
        module_scores: dict[str, int],
        activity_count: int,
    ) -> LifeScore:
        """Create or update a Life Score for a specific date.
        
        Requirement 33.1: Calculate Life Score based on activity across all modules
        """
        # Check if score exists for this date
        existing = await self.get_score_by_date(user_id, score_date)
        
        if existing:
            # Update existing score
            existing.total_score = total_score
            existing.module_scores = module_scores
            existing.activity_count = activity_count
            await self.session.flush()
            return existing
        
        # Create new score
        life_score = LifeScore(
            user_id=user_id,
            score_date=score_date,
            total_score=total_score,
            module_scores=module_scores,
            activity_count=activity_count,
        )
        self.session.add(life_score)
        await self.session.flush()
        return life_score

    async def get_score_by_date(
        self,
        user_id: uuid.UUID,
        score_date: date,
    ) -> Optional[LifeScore]:
        """Get Life Score for a specific date."""
        query = select(LifeScore).where(
            and_(
                LifeScore.user_id == user_id,
                LifeScore.score_date == score_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_score(
        self,
        user_id: uuid.UUID,
    ) -> Optional[LifeScore]:
        """Get the most recent Life Score for a user."""
        query = (
            select(LifeScore)
            .where(LifeScore.user_id == user_id)
            .order_by(LifeScore.score_date.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_scores_in_range(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> list[LifeScore]:
        """Get Life Scores within a date range.
        
        Requirement 33.4: Display Life Score trends over time
        """
        query = (
            select(LifeScore)
            .where(
                and_(
                    LifeScore.user_id == user_id,
                    LifeScore.score_date >= start_date,
                    LifeScore.score_date <= end_date,
                )
            )
            .order_by(LifeScore.score_date.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_scores_paginated(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 30,
    ) -> tuple[list[LifeScore], int]:
        """Get paginated Life Score history for a user."""
        # Count query
        count_query = select(func.count(LifeScore.id)).where(
            LifeScore.user_id == user_id
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        offset = (page - 1) * page_size
        query = (
            select(LifeScore)
            .where(LifeScore.user_id == user_id)
            .order_by(LifeScore.score_date.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        scores = list(result.scalars().all())

        return scores, total

    async def get_average_score(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> Optional[float]:
        """Get average Life Score for a date range."""
        query = select(func.avg(LifeScore.total_score)).where(
            and_(
                LifeScore.user_id == user_id,
                LifeScore.score_date >= start_date,
                LifeScore.score_date <= end_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar()

    async def delete_scores_before(
        self,
        user_id: uuid.UUID,
        before_date: date,
    ) -> int:
        """Delete Life Scores before a specific date (for cleanup)."""
        from sqlalchemy import delete
        
        stmt = delete(LifeScore).where(
            and_(
                LifeScore.user_id == user_id,
                LifeScore.score_date < before_date,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
