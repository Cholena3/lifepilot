"""Service for skill inventory management."""

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import (
    ProficiencyLevel,
    Skill,
    SkillCategory,
    SKILL_SUGGESTIONS_BY_ROLE,
)
from app.repositories.skill import SkillProficiencyHistoryRepository, SkillRepository
from app.schemas.skill import (
    PaginatedSkillResponse,
    SkillCreate,
    SkillResponse,
    SkillsByCategory,
    SkillsGroupedResponse,
    SkillSuggestion,
    SkillSuggestionsResponse,
    SkillUpdate,
    SkillWithHistoryResponse,
)


class SkillService:
    """Service for skill inventory management.
    
    Implements Requirements 24.1-24.5 for skill tracking and suggestions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.skill_repo = SkillRepository(session)
        self.history_repo = SkillProficiencyHistoryRepository(session)

    async def add_skill(
        self,
        user_id: uuid.UUID,
        data: SkillCreate,
    ) -> Skill:
        """Add a new skill for a user.
        
        Requirement 24.1: Store skill name, category, and proficiency level
        
        Raises:
            ValueError: If skill with same name already exists
        """
        # Check for duplicate skill name
        existing = await self.skill_repo.get_skill_by_name(user_id, data.name)
        if existing:
            raise ValueError(f"Skill '{data.name}' already exists")

        skill = await self.skill_repo.create_skill(
            user_id=user_id,
            name=data.name,
            category=data.category,
            proficiency=data.proficiency,
        )
        return skill

    async def get_skill(
        self,
        skill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Skill]:
        """Get a skill by ID."""
        return await self.skill_repo.get_skill_by_id(skill_id, user_id)

    async def get_skill_with_history(
        self,
        skill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[SkillWithHistoryResponse]:
        """Get a skill with its proficiency history.
        
        Requirement 24.3: Track proficiency changes with timestamps
        """
        skill = await self.skill_repo.get_skill_with_history(skill_id, user_id)
        if not skill:
            return None
        return SkillWithHistoryResponse.model_validate(skill)

    async def get_skills(
        self,
        user_id: uuid.UUID,
        category: Optional[SkillCategory] = None,
        proficiency: Optional[ProficiencyLevel] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedSkillResponse:
        """Get skills for a user with optional filtering."""
        skills, total = await self.skill_repo.get_skills(
            user_id=user_id,
            category=category,
            proficiency=proficiency,
            page=page,
            page_size=page_size,
        )
        
        items = [SkillResponse.model_validate(s) for s in skills]
        return PaginatedSkillResponse.create(items, total, page, page_size)

    async def get_skills_grouped(
        self,
        user_id: uuid.UUID,
    ) -> SkillsGroupedResponse:
        """Get skills grouped by category.
        
        Requirement 24.4: Display skills grouped by category with visual proficiency indicators
        """
        skills = await self.skill_repo.get_all_skills(user_id)
        
        # Group skills by category
        groups_dict: dict[SkillCategory, list[SkillResponse]] = {}
        for skill in skills:
            skill_response = SkillResponse.model_validate(skill)
            if skill.category not in groups_dict:
                groups_dict[skill.category] = []
            groups_dict[skill.category].append(skill_response)
        
        # Convert to list of SkillsByCategory
        groups = [
            SkillsByCategory(category=cat, skills=skills_list)
            for cat, skills_list in sorted(groups_dict.items(), key=lambda x: x[0].value)
        ]
        
        return SkillsGroupedResponse(
            groups=groups,
            total_skills=len(skills),
        )

    async def update_skill(
        self,
        skill_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SkillUpdate,
    ) -> Optional[Skill]:
        """Update a skill.
        
        Requirement 24.3: Record proficiency changes with timestamp
        """
        skill = await self.skill_repo.get_skill_by_id(skill_id, user_id)
        if not skill:
            return None

        # Check for duplicate name if name is being updated
        if data.name and data.name.lower() != skill.name.lower():
            existing = await self.skill_repo.get_skill_by_name(user_id, data.name)
            if existing:
                raise ValueError(f"Skill '{data.name}' already exists")

        # Track proficiency change if proficiency is being updated
        if data.proficiency and data.proficiency != skill.proficiency:
            await self.history_repo.create_history_entry(
                skill_id=skill.id,
                previous_level=skill.proficiency,
                new_level=data.proficiency,
            )

        # Update skill
        update_data = data.model_dump(exclude_unset=True)
        skill = await self.skill_repo.update_skill(skill, **update_data)
        return skill

    async def delete_skill(
        self,
        skill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a skill."""
        skill = await self.skill_repo.get_skill_by_id(skill_id, user_id)
        if not skill:
            return False
        await self.skill_repo.delete_skill(skill)
        return True

    async def get_skill_suggestions(
        self,
        user_id: uuid.UUID,
        preferred_roles: Optional[list[str]] = None,
    ) -> SkillSuggestionsResponse:
        """Get skill suggestions based on career goals.
        
        Requirement 24.5: Suggest skills to learn based on career goals
        """
        if not preferred_roles:
            preferred_roles = []

        # Get user's existing skills
        existing_skills = await self.skill_repo.get_all_skills(user_id)
        existing_skill_names = {s.name.lower() for s in existing_skills}

        suggestions: list[SkillSuggestion] = []
        matched_roles: list[str] = []

        # Get suggestions based on preferred roles
        for role in preferred_roles:
            role_lower = role.lower()
            for known_role, role_skills in SKILL_SUGGESTIONS_BY_ROLE.items():
                if known_role in role_lower or role_lower in known_role:
                    matched_roles.append(known_role)
                    for skill_info in role_skills:
                        skill_name = skill_info["name"]
                        if skill_name.lower() not in existing_skill_names:
                            # Check if already in suggestions
                            if not any(s.name.lower() == skill_name.lower() for s in suggestions):
                                suggestions.append(
                                    SkillSuggestion(
                                        name=skill_name,
                                        category=skill_info["category"],
                                        reason=f"Recommended for {known_role} role",
                                    )
                                )

        # If no roles matched, provide general suggestions
        if not suggestions:
            general_skills = [
                {"name": "Git", "category": "devops"},
                {"name": "Communication", "category": "soft_skill"},
                {"name": "Problem Solving", "category": "soft_skill"},
                {"name": "SQL", "category": "database"},
            ]
            for skill_info in general_skills:
                skill_name = skill_info["name"]
                if skill_name.lower() not in existing_skill_names:
                    suggestions.append(
                        SkillSuggestion(
                            name=skill_name,
                            category=skill_info["category"],
                            reason="General skill recommended for career growth",
                        )
                    )

        return SkillSuggestionsResponse(
            suggestions=suggestions[:10],  # Limit to 10 suggestions
            based_on_roles=list(set(matched_roles)),
        )
