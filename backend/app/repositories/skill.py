"""Repository for skill database operations."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.skill import (
    ProficiencyLevel,
    Skill,
    SkillCategory,
    SkillProficiencyHistory,
)


class SkillRepository:
    """Repository for Skill CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_skill(
        self,
        user_id: uuid.UUID,
        name: str,
        category: SkillCategory,
        proficiency: ProficiencyLevel,
    ) -> Skill:
        """Create a new skill for a user.
        
        Requirement 24.1: Store skill name, category, and proficiency level
        """
        skill = Skill(
            user_id=user_id,
            name=name,
            category=category,
            proficiency=proficiency,
        )
        self.session.add(skill)
        await self.session.flush()
        
        # Create initial proficiency history entry
        history = SkillProficiencyHistory(
            skill_id=skill.id,
            previous_level=None,
            new_level=proficiency,
        )
        self.session.add(history)
        await self.session.flush()
        
        return skill

    async def get_skill_by_id(
        self,
        skill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Skill]:
        """Get a skill by ID for a specific user."""
        query = select(Skill).where(
            Skill.id == skill_id,
            Skill.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_skill_with_history(
        self,
        skill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Skill]:
        """Get a skill with its proficiency history."""
        query = (
            select(Skill)
            .options(selectinload(Skill.proficiency_history))
            .where(
                Skill.id == skill_id,
                Skill.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_skills(
        self,
        user_id: uuid.UUID,
        category: Optional[SkillCategory] = None,
        proficiency: Optional[ProficiencyLevel] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Skill], int]:
        """Get skills for a user with optional filtering and pagination."""
        query = select(Skill).where(Skill.user_id == user_id)
        count_query = select(func.count(Skill.id)).where(Skill.user_id == user_id)

        if category:
            query = query.where(Skill.category == category)
            count_query = count_query.where(Skill.category == category)

        if proficiency:
            query = query.where(Skill.proficiency == proficiency)
            count_query = count_query.where(Skill.proficiency == proficiency)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Skill.category, Skill.name)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        skills = list(result.scalars().all())

        return skills, total

    async def get_all_skills(self, user_id: uuid.UUID) -> list[Skill]:
        """Get all skills for a user without pagination."""
        query = (
            select(Skill)
            .where(Skill.user_id == user_id)
            .order_by(Skill.category, Skill.name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_skill_by_name(
        self,
        user_id: uuid.UUID,
        name: str,
    ) -> Optional[Skill]:
        """Get a skill by name for a specific user (case-insensitive)."""
        query = select(Skill).where(
            Skill.user_id == user_id,
            func.lower(Skill.name) == func.lower(name),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_skill(
        self,
        skill: Skill,
        **kwargs,
    ) -> Skill:
        """Update a skill's attributes."""
        for key, value in kwargs.items():
            if value is not None and hasattr(skill, key):
                setattr(skill, key, value)
        await self.session.flush()
        return skill

    async def delete_skill(self, skill: Skill) -> None:
        """Delete a skill."""
        await self.session.delete(skill)
        await self.session.flush()


class SkillProficiencyHistoryRepository:
    """Repository for SkillProficiencyHistory operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_history_entry(
        self,
        skill_id: uuid.UUID,
        previous_level: Optional[ProficiencyLevel],
        new_level: ProficiencyLevel,
    ) -> SkillProficiencyHistory:
        """Create a proficiency history entry.
        
        Requirement 24.3: Record proficiency changes with timestamp
        """
        history = SkillProficiencyHistory(
            skill_id=skill_id,
            previous_level=previous_level,
            new_level=new_level,
        )
        self.session.add(history)
        await self.session.flush()
        return history

    async def get_history_for_skill(
        self,
        skill_id: uuid.UUID,
    ) -> list[SkillProficiencyHistory]:
        """Get proficiency history for a skill."""
        query = (
            select(SkillProficiencyHistory)
            .where(SkillProficiencyHistory.skill_id == skill_id)
            .order_by(SkillProficiencyHistory.changed_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
