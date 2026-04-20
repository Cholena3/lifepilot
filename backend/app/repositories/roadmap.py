"""Repository for career roadmap database operations.

Validates: Requirements 26.1, 26.2, 26.3, 26.4, 26.5
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.roadmap import (
    CareerRoadmap,
    MilestoneStatus,
    ResourceRecommendation,
    ResourceType,
    RoadmapMilestone,
    SkillGap,
)


class RoadmapRepository:
    """Repository for CareerRoadmap CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_roadmap(
        self,
        user_id: uuid.UUID,
        target_role: str,
        target_timeline_months: int = 12,
        notes: Optional[str] = None,
    ) -> CareerRoadmap:
        """Create a new career roadmap.
        
        Requirement 26.1: Generate roadmap from career goals
        """
        roadmap = CareerRoadmap(
            user_id=user_id,
            target_role=target_role,
            target_timeline_months=target_timeline_months,
            notes=notes,
            current_progress=0,
            is_active=True,
        )
        self.session.add(roadmap)
        await self.session.flush()
        return roadmap

    async def get_roadmap_by_id(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CareerRoadmap]:
        """Get a roadmap by ID for a specific user."""
        query = select(CareerRoadmap).where(
            CareerRoadmap.id == roadmap_id,
            CareerRoadmap.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_roadmap_with_details(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CareerRoadmap]:
        """Get a roadmap with milestones and skill gaps."""
        query = (
            select(CareerRoadmap)
            .options(
                selectinload(CareerRoadmap.milestones),
                selectinload(CareerRoadmap.skill_gaps).selectinload(SkillGap.recommendations),
            )
            .where(
                CareerRoadmap.id == roadmap_id,
                CareerRoadmap.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_roadmap(
        self,
        user_id: uuid.UUID,
    ) -> Optional[CareerRoadmap]:
        """Get the active roadmap for a user."""
        query = (
            select(CareerRoadmap)
            .options(
                selectinload(CareerRoadmap.milestones),
                selectinload(CareerRoadmap.skill_gaps).selectinload(SkillGap.recommendations),
            )
            .where(
                CareerRoadmap.user_id == user_id,
                CareerRoadmap.is_active == True,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_roadmaps(
        self,
        user_id: uuid.UUID,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CareerRoadmap], int]:
        """Get roadmaps for a user with optional filtering and pagination."""
        query = select(CareerRoadmap).where(CareerRoadmap.user_id == user_id)
        count_query = select(func.count(CareerRoadmap.id)).where(
            CareerRoadmap.user_id == user_id
        )

        if is_active is not None:
            query = query.where(CareerRoadmap.is_active == is_active)
            count_query = count_query.where(CareerRoadmap.is_active == is_active)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(
            CareerRoadmap.is_active.desc(),
            CareerRoadmap.created_at.desc()
        )
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        roadmaps = list(result.scalars().all())

        return roadmaps, total

    async def update_roadmap(
        self,
        roadmap: CareerRoadmap,
        **kwargs,
    ) -> CareerRoadmap:
        """Update a roadmap's attributes."""
        for key, value in kwargs.items():
            if value is not None and hasattr(roadmap, key):
                setattr(roadmap, key, value)
        await self.session.flush()
        return roadmap

    async def deactivate_other_roadmaps(
        self,
        user_id: uuid.UUID,
        active_roadmap_id: uuid.UUID,
    ) -> None:
        """Deactivate all roadmaps except the specified one."""
        stmt = (
            update(CareerRoadmap)
            .where(
                CareerRoadmap.user_id == user_id,
                CareerRoadmap.id != active_roadmap_id,
            )
            .values(is_active=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_roadmap(self, roadmap: CareerRoadmap) -> None:
        """Delete a roadmap."""
        await self.session.delete(roadmap)
        await self.session.flush()

    async def calculate_progress(self, roadmap_id: uuid.UUID) -> int:
        """Calculate overall progress based on completed milestones.
        
        Requirement 26.4: Track milestone completion
        """
        # Count total and completed milestones
        total_query = select(func.count(RoadmapMilestone.id)).where(
            RoadmapMilestone.roadmap_id == roadmap_id
        )
        completed_query = select(func.count(RoadmapMilestone.id)).where(
            RoadmapMilestone.roadmap_id == roadmap_id,
            RoadmapMilestone.status == MilestoneStatus.COMPLETED,
        )

        total_result = await self.session.execute(total_query)
        completed_result = await self.session.execute(completed_query)

        total = total_result.scalar() or 0
        completed = completed_result.scalar() or 0

        if total == 0:
            return 0
        return int((completed / total) * 100)


class MilestoneRepository:
    """Repository for RoadmapMilestone operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_milestone(
        self,
        roadmap_id: uuid.UUID,
        title: str,
        description: Optional[str] = None,
        order_index: int = 0,
        target_date: Optional[date] = None,
        required_skills: Optional[list[str]] = None,
    ) -> RoadmapMilestone:
        """Create a new milestone.
        
        Requirement 26.1: Roadmap milestones
        """
        milestone = RoadmapMilestone(
            roadmap_id=roadmap_id,
            title=title,
            description=description,
            order_index=order_index,
            target_date=target_date,
            required_skills=required_skills,
            status=MilestoneStatus.NOT_STARTED,
        )
        self.session.add(milestone)
        await self.session.flush()
        return milestone

    async def get_milestone_by_id(
        self,
        milestone_id: uuid.UUID,
        roadmap_id: uuid.UUID,
    ) -> Optional[RoadmapMilestone]:
        """Get a milestone by ID."""
        query = select(RoadmapMilestone).where(
            RoadmapMilestone.id == milestone_id,
            RoadmapMilestone.roadmap_id == roadmap_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_milestones_for_roadmap(
        self,
        roadmap_id: uuid.UUID,
    ) -> list[RoadmapMilestone]:
        """Get all milestones for a roadmap."""
        query = (
            select(RoadmapMilestone)
            .where(RoadmapMilestone.roadmap_id == roadmap_id)
            .order_by(RoadmapMilestone.order_index)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_milestone(
        self,
        milestone: RoadmapMilestone,
        **kwargs,
    ) -> RoadmapMilestone:
        """Update a milestone's attributes.
        
        Requirement 26.4: Update milestone completion
        """
        for key, value in kwargs.items():
            if value is not None and hasattr(milestone, key):
                setattr(milestone, key, value)
        await self.session.flush()
        return milestone

    async def delete_milestone(self, milestone: RoadmapMilestone) -> None:
        """Delete a milestone."""
        await self.session.delete(milestone)
        await self.session.flush()

    async def get_next_order_index(self, roadmap_id: uuid.UUID) -> int:
        """Get the next order index for a new milestone."""
        query = select(func.max(RoadmapMilestone.order_index)).where(
            RoadmapMilestone.roadmap_id == roadmap_id
        )
        result = await self.session.execute(query)
        max_index = result.scalar()
        return (max_index or 0) + 1


class SkillGapRepository:
    """Repository for SkillGap operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_skill_gap(
        self,
        roadmap_id: uuid.UUID,
        skill_name: str,
        required_level: str,
        current_level: Optional[str] = None,
        priority: int = 1,
    ) -> SkillGap:
        """Create a skill gap entry.
        
        Requirement 26.2: Identify skill gaps
        """
        skill_gap = SkillGap(
            roadmap_id=roadmap_id,
            skill_name=skill_name,
            current_level=current_level,
            required_level=required_level,
            priority=priority,
            is_filled=False,
        )
        self.session.add(skill_gap)
        await self.session.flush()
        return skill_gap

    async def get_skill_gap_by_id(
        self,
        skill_gap_id: uuid.UUID,
        roadmap_id: uuid.UUID,
    ) -> Optional[SkillGap]:
        """Get a skill gap by ID."""
        query = (
            select(SkillGap)
            .options(selectinload(SkillGap.recommendations))
            .where(
                SkillGap.id == skill_gap_id,
                SkillGap.roadmap_id == roadmap_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_skill_gaps_for_roadmap(
        self,
        roadmap_id: uuid.UUID,
        include_filled: bool = True,
    ) -> list[SkillGap]:
        """Get all skill gaps for a roadmap.
        
        Requirement 26.2: List skill gaps
        """
        query = (
            select(SkillGap)
            .options(selectinload(SkillGap.recommendations))
            .where(SkillGap.roadmap_id == roadmap_id)
        )
        
        if not include_filled:
            query = query.where(SkillGap.is_filled == False)
        
        query = query.order_by(SkillGap.priority, SkillGap.skill_name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_skill_gap(
        self,
        skill_gap: SkillGap,
        **kwargs,
    ) -> SkillGap:
        """Update a skill gap."""
        for key, value in kwargs.items():
            if value is not None and hasattr(skill_gap, key):
                setattr(skill_gap, key, value)
        await self.session.flush()
        return skill_gap

    async def delete_skill_gap(self, skill_gap: SkillGap) -> None:
        """Delete a skill gap."""
        await self.session.delete(skill_gap)
        await self.session.flush()


class ResourceRecommendationRepository:
    """Repository for ResourceRecommendation operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_recommendation(
        self,
        skill_gap_id: uuid.UUID,
        title: str,
        resource_type: ResourceType = ResourceType.COURSE,
        url: Optional[str] = None,
        platform: Optional[str] = None,
        estimated_hours: Optional[Decimal] = None,
    ) -> ResourceRecommendation:
        """Create a resource recommendation.
        
        Requirement 26.3: Recommend courses and resources
        """
        recommendation = ResourceRecommendation(
            skill_gap_id=skill_gap_id,
            title=title,
            resource_type=resource_type,
            url=url,
            platform=platform,
            estimated_hours=estimated_hours,
            is_completed=False,
        )
        self.session.add(recommendation)
        await self.session.flush()
        return recommendation

    async def get_recommendation_by_id(
        self,
        recommendation_id: uuid.UUID,
    ) -> Optional[ResourceRecommendation]:
        """Get a recommendation by ID."""
        query = select(ResourceRecommendation).where(
            ResourceRecommendation.id == recommendation_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_recommendations_for_skill_gap(
        self,
        skill_gap_id: uuid.UUID,
    ) -> list[ResourceRecommendation]:
        """Get all recommendations for a skill gap."""
        query = (
            select(ResourceRecommendation)
            .where(ResourceRecommendation.skill_gap_id == skill_gap_id)
            .order_by(ResourceRecommendation.resource_type, ResourceRecommendation.title)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_recommendation(
        self,
        recommendation: ResourceRecommendation,
        **kwargs,
    ) -> ResourceRecommendation:
        """Update a recommendation."""
        for key, value in kwargs.items():
            if value is not None and hasattr(recommendation, key):
                setattr(recommendation, key, value)
        await self.session.flush()
        return recommendation

    async def mark_completed(
        self,
        recommendation: ResourceRecommendation,
        is_completed: bool = True,
    ) -> ResourceRecommendation:
        """Mark a recommendation as completed."""
        recommendation.is_completed = is_completed
        if is_completed:
            recommendation.completed_at = datetime.now(timezone.utc)
        else:
            recommendation.completed_at = None
        await self.session.flush()
        return recommendation
