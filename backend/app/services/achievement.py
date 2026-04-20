"""Service for achievement logging.

Requirement 29: Achievement Logging
"""

import uuid
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement, AchievementCategory
from app.repositories.achievement import AchievementRepository
from app.schemas.achievement import (
    AchievementCreate,
    AchievementResponse,
    AchievementsByCategory,
    AchievementsGroupedResponse,
    AchievementSuggestion,
    AchievementSuggestionsResponse,
    AchievementTimelineResponse,
    AchievementUpdate,
    PaginatedAchievementResponse,
)


class AchievementService:
    """Service for achievement logging.
    
    Implements Requirements 29.1-29.5 for achievement tracking.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.achievement_repo = AchievementRepository(session)

    async def add_achievement(
        self,
        user_id: uuid.UUID,
        data: AchievementCreate,
    ) -> Achievement:
        """Add a new achievement for a user.
        
        Requirement 29.1: Store title, description, date, and category
        Requirement 29.3: Allow attaching supporting documents
        """
        achievement = await self.achievement_repo.create_achievement(
            user_id=user_id,
            title=data.title,
            description=data.description,
            achieved_date=data.achieved_date,
            category=data.category,
            document_ids=data.document_ids,
        )
        return achievement

    async def get_achievement(
        self,
        achievement_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Achievement]:
        """Get an achievement by ID."""
        return await self.achievement_repo.get_achievement_by_id(achievement_id, user_id)

    async def get_achievements(
        self,
        user_id: uuid.UUID,
        category: Optional[AchievementCategory] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedAchievementResponse:
        """Get achievements for a user with optional filtering.
        
        Requirement 29.5: Display achievements on a timeline view
        """
        achievements, total = await self.achievement_repo.get_achievements(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        
        items = [AchievementResponse.model_validate(a) for a in achievements]
        return PaginatedAchievementResponse.create(items, total, page, page_size)

    async def get_achievements_timeline(
        self,
        user_id: uuid.UUID,
        category: Optional[AchievementCategory] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[AchievementTimelineResponse]:
        """Get achievements grouped by year for timeline view.
        
        Requirement 29.5: Display achievements on a timeline view
        """
        timeline_dict = await self.achievement_repo.get_achievements_timeline(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Convert to response format, sorted by year descending
        timeline = []
        for year in sorted(timeline_dict.keys(), reverse=True):
            achievements = [
                AchievementResponse.model_validate(a) 
                for a in timeline_dict[year]
            ]
            timeline.append(AchievementTimelineResponse(
                year=year,
                achievements=achievements,
            ))
        
        return timeline

    async def get_achievements_grouped(
        self,
        user_id: uuid.UUID,
    ) -> AchievementsGroupedResponse:
        """Get achievements grouped by category.
        
        Requirement 29.2: Support categories
        """
        grouped_dict = await self.achievement_repo.get_achievements_by_category(user_id)
        
        # Convert to list of AchievementsByCategory
        groups = []
        for cat in sorted(grouped_dict.keys(), key=lambda x: x.value):
            achievements = [
                AchievementResponse.model_validate(a) 
                for a in grouped_dict[cat]
            ]
            groups.append(AchievementsByCategory(
                category=cat,
                achievements=achievements,
                count=len(achievements),
            ))
        
        total = sum(g.count for g in groups)
        return AchievementsGroupedResponse(
            groups=groups,
            total_achievements=total,
        )

    async def update_achievement(
        self,
        achievement_id: uuid.UUID,
        user_id: uuid.UUID,
        data: AchievementUpdate,
    ) -> Optional[Achievement]:
        """Update an achievement."""
        achievement = await self.achievement_repo.get_achievement_by_id(
            achievement_id, user_id
        )
        if not achievement:
            return None

        # Update achievement
        update_data = data.model_dump(exclude_unset=True)
        achievement = await self.achievement_repo.update_achievement(
            achievement, **update_data
        )
        return achievement

    async def delete_achievement(
        self,
        achievement_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an achievement."""
        achievement = await self.achievement_repo.get_achievement_by_id(
            achievement_id, user_id
        )
        if not achievement:
            return False
        await self.achievement_repo.delete_achievement(achievement)
        return True

    async def get_achievement_suggestions(
        self,
        user_id: uuid.UUID,
        target_role: Optional[str] = None,
        categories: Optional[list[AchievementCategory]] = None,
        limit: int = 10,
    ) -> AchievementSuggestionsResponse:
        """Get achievement suggestions for resume building.
        
        Requirement 29.4: Suggest relevant achievements to include when building a resume
        """
        # Get all achievements for the user
        all_achievements = await self.achievement_repo.get_all_achievements(user_id)
        
        if not all_achievements:
            return AchievementSuggestionsResponse(
                suggestions=[],
                total_achievements=0,
            )

        suggestions: list[AchievementSuggestion] = []
        
        # Define category relevance for different roles
        role_category_weights: dict[str, dict[AchievementCategory, float]] = {
            "software engineer": {
                AchievementCategory.PROJECT: 1.0,
                AchievementCategory.CERTIFICATION: 0.9,
                AchievementCategory.PROFESSIONAL: 0.8,
                AchievementCategory.AWARD: 0.7,
                AchievementCategory.PUBLICATION: 0.6,
                AchievementCategory.ACADEMIC: 0.5,
            },
            "data scientist": {
                AchievementCategory.PROJECT: 1.0,
                AchievementCategory.PUBLICATION: 0.95,
                AchievementCategory.CERTIFICATION: 0.9,
                AchievementCategory.ACADEMIC: 0.8,
                AchievementCategory.AWARD: 0.7,
                AchievementCategory.PROFESSIONAL: 0.6,
            },
            "manager": {
                AchievementCategory.PROFESSIONAL: 1.0,
                AchievementCategory.AWARD: 0.9,
                AchievementCategory.PROJECT: 0.8,
                AchievementCategory.CERTIFICATION: 0.7,
                AchievementCategory.ACADEMIC: 0.5,
                AchievementCategory.PUBLICATION: 0.4,
            },
        }
        
        # Default weights if no role specified
        default_weights: dict[AchievementCategory, float] = {
            AchievementCategory.CERTIFICATION: 0.9,
            AchievementCategory.AWARD: 0.85,
            AchievementCategory.PROJECT: 0.8,
            AchievementCategory.PROFESSIONAL: 0.75,
            AchievementCategory.PUBLICATION: 0.7,
            AchievementCategory.ACADEMIC: 0.65,
            AchievementCategory.OTHER: 0.5,
        }
        
        # Get weights based on target role
        weights = default_weights
        if target_role:
            role_lower = target_role.lower()
            for known_role, role_weights in role_category_weights.items():
                if known_role in role_lower or role_lower in known_role:
                    weights = {**default_weights, **role_weights}
                    break
        
        # Filter by categories if specified
        filtered_achievements = all_achievements
        if categories:
            filtered_achievements = [
                a for a in all_achievements if a.category in categories
            ]
        
        # Score and sort achievements
        for achievement in filtered_achievements:
            base_score = weights.get(achievement.category, 0.5)
            
            # Boost recent achievements (within last 2 years)
            from datetime import date as date_type
            today = date_type.today()
            years_ago = (today - achievement.achieved_date).days / 365
            recency_boost = max(0, 0.2 * (1 - years_ago / 2)) if years_ago < 2 else 0
            
            # Boost achievements with documents attached
            doc_boost = 0.1 if achievement.document_ids else 0
            
            final_score = min(1.0, base_score + recency_boost + doc_boost)
            
            # Generate reason
            reasons = []
            if achievement.category in [AchievementCategory.CERTIFICATION, AchievementCategory.AWARD]:
                reasons.append(f"Strong {achievement.category.value} credential")
            if years_ago < 1:
                reasons.append("Recent achievement")
            if achievement.document_ids:
                reasons.append("Has supporting documents")
            if target_role:
                reasons.append(f"Relevant for {target_role} role")
            
            reason = "; ".join(reasons) if reasons else "Relevant achievement"
            
            suggestions.append(AchievementSuggestion(
                achievement=AchievementResponse.model_validate(achievement),
                relevance_score=round(final_score, 2),
                reason=reason,
            ))
        
        # Sort by relevance score and limit
        suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
        suggestions = suggestions[:limit]
        
        return AchievementSuggestionsResponse(
            suggestions=suggestions,
            total_achievements=len(all_achievements),
        )

    async def attach_documents(
        self,
        achievement_id: uuid.UUID,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
    ) -> Optional[Achievement]:
        """Attach documents to an achievement.
        
        Requirement 29.3: Allow attaching supporting documents
        """
        achievement = await self.achievement_repo.get_achievement_by_id(
            achievement_id, user_id
        )
        if not achievement:
            return None
        
        # Merge existing and new document IDs
        existing_ids = set(achievement.document_ids or [])
        new_ids = existing_ids.union(set(document_ids))
        
        achievement = await self.achievement_repo.update_achievement(
            achievement, document_ids=list(new_ids)
        )
        return achievement

    async def detach_document(
        self,
        achievement_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Optional[Achievement]:
        """Detach a document from an achievement.
        
        Requirement 29.3: Allow attaching supporting documents
        """
        achievement = await self.achievement_repo.get_achievement_by_id(
            achievement_id, user_id
        )
        if not achievement:
            return None
        
        # Remove the document ID
        existing_ids = list(achievement.document_ids or [])
        if document_id in existing_ids:
            existing_ids.remove(document_id)
        
        achievement = await self.achievement_repo.update_achievement(
            achievement, document_ids=existing_ids
        )
        return achievement
