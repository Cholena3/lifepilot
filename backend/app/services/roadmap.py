"""Service for career roadmap management.

Validates: Requirements 26.1, 26.2, 26.3, 26.4, 26.5
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.roadmap import (
    CareerRoadmap,
    MilestoneStatus,
    ResourceRecommendation,
    ResourceType,
    RoadmapMilestone,
    ROLE_SKILL_REQUIREMENTS,
    SKILL_RESOURCES,
    SkillGap,
)
from app.models.skill import ProficiencyLevel, Skill
from app.repositories.roadmap import (
    MilestoneRepository,
    ResourceRecommendationRepository,
    RoadmapRepository,
    SkillGapRepository,
)
from app.repositories.skill import SkillRepository
from app.schemas.roadmap import (
    CareerGoalCreate,
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    PaginatedRoadmapResponse,
    ResourceCompletionUpdate,
    RoadmapDetailResponse,
    RoadmapProgressResponse,
    RoadmapResponse,
    RoadmapUpdate,
    SkillGapResponse,
    SkillGapSummary,
    SkillGapUpdate,
)


# Proficiency level ordering for comparison
PROFICIENCY_ORDER = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4,
}


class RoadmapService:
    """Service for career roadmap management.
    
    Implements Requirements 26.1-26.5 for career roadmap functionality.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.roadmap_repo = RoadmapRepository(session)
        self.milestone_repo = MilestoneRepository(session)
        self.skill_gap_repo = SkillGapRepository(session)
        self.resource_repo = ResourceRecommendationRepository(session)
        self.skill_repo = SkillRepository(session)

    async def create_roadmap(
        self,
        user_id: uuid.UUID,
        data: CareerGoalCreate,
    ) -> RoadmapDetailResponse:
        """Create a new career roadmap from career goals.
        
        Requirement 26.1: Generate roadmap from career goals with milestones
        Requirement 26.2: Identify skill gaps
        Requirement 26.3: Recommend courses and resources
        """
        # Create the roadmap
        roadmap = await self.roadmap_repo.create_roadmap(
            user_id=user_id,
            target_role=data.target_role,
            target_timeline_months=data.target_timeline_months,
            notes=data.notes,
        )

        # Deactivate other roadmaps
        await self.roadmap_repo.deactivate_other_roadmaps(user_id, roadmap.id)

        # Generate milestones based on target role
        await self._generate_milestones(roadmap, data.target_timeline_months)

        # Identify skill gaps
        await self._identify_skill_gaps(user_id, roadmap)

        # Get the complete roadmap with details
        complete_roadmap = await self.roadmap_repo.get_roadmap_with_details(
            roadmap.id, user_id
        )
        return RoadmapDetailResponse.model_validate(complete_roadmap)

    async def _generate_milestones(
        self,
        roadmap: CareerRoadmap,
        timeline_months: int,
    ) -> list[RoadmapMilestone]:
        """Generate milestones based on target role and timeline.
        
        Requirement 26.1: Generate roadmap with milestones
        """
        target_role_lower = roadmap.target_role.lower()
        
        # Find matching role requirements
        matched_role = None
        for role in ROLE_SKILL_REQUIREMENTS:
            if role in target_role_lower or target_role_lower in role:
                matched_role = role
                break

        # Default milestones structure
        milestone_templates = [
            {
                "title": "Foundation Skills Assessment",
                "description": "Assess current skills and identify gaps for the target role.",
                "month_offset": 0,
                "skills": [],
            },
            {
                "title": "Core Technical Skills",
                "description": "Build foundational technical skills required for the role.",
                "month_offset": int(timeline_months * 0.25),
                "skills": [],
            },
            {
                "title": "Intermediate Skills Development",
                "description": "Develop intermediate-level skills and start building projects.",
                "month_offset": int(timeline_months * 0.5),
                "skills": [],
            },
            {
                "title": "Advanced Skills & Specialization",
                "description": "Master advanced skills and specialize in key areas.",
                "month_offset": int(timeline_months * 0.75),
                "skills": [],
            },
            {
                "title": "Portfolio & Job Preparation",
                "description": "Build portfolio, prepare resume, and start job applications.",
                "month_offset": timeline_months,
                "skills": [],
            },
        ]

        # Assign skills to milestones if we have role requirements
        if matched_role and matched_role in ROLE_SKILL_REQUIREMENTS:
            skills = ROLE_SKILL_REQUIREMENTS[matched_role]
            skills_per_milestone = max(1, len(skills) // 3)
            
            # Distribute skills across milestones 1-3 (core, intermediate, advanced)
            for i, skill in enumerate(skills):
                milestone_idx = min(1 + (i // skills_per_milestone), 3)
                milestone_templates[milestone_idx]["skills"].append(skill["name"])

        # Create milestones
        milestones = []
        today = date.today()
        
        for idx, template in enumerate(milestone_templates):
            target_date = today + timedelta(days=template["month_offset"] * 30)
            milestone = await self.milestone_repo.create_milestone(
                roadmap_id=roadmap.id,
                title=template["title"],
                description=template["description"],
                order_index=idx,
                target_date=target_date,
                required_skills=template["skills"] if template["skills"] else None,
            )
            milestones.append(milestone)

        return milestones

    async def _identify_skill_gaps(
        self,
        user_id: uuid.UUID,
        roadmap: CareerRoadmap,
    ) -> list[SkillGap]:
        """Identify skill gaps between current skills and role requirements.
        
        Requirement 26.2: Identify skill gaps between current skills and goal requirements
        Requirement 26.3: Recommend courses and resources to fill skill gaps
        """
        target_role_lower = roadmap.target_role.lower()
        
        # Find matching role requirements
        matched_role = None
        for role in ROLE_SKILL_REQUIREMENTS:
            if role in target_role_lower or target_role_lower in role:
                matched_role = role
                break

        if not matched_role:
            # Use generic skills if no match
            required_skills = [
                {"name": "Communication", "level": "intermediate"},
                {"name": "Problem Solving", "level": "intermediate"},
                {"name": "Time Management", "level": "intermediate"},
            ]
        else:
            required_skills = ROLE_SKILL_REQUIREMENTS[matched_role]

        # Get user's current skills
        user_skills = await self.skill_repo.get_all_skills(user_id)
        user_skill_map = {
            skill.name.lower(): skill.proficiency.value
            for skill in user_skills
        }

        # Identify gaps
        skill_gaps = []
        for idx, req_skill in enumerate(required_skills):
            skill_name = req_skill["name"]
            required_level = req_skill["level"]
            current_level = user_skill_map.get(skill_name.lower())

            # Check if there's a gap
            is_gap = False
            if current_level is None:
                is_gap = True
            else:
                current_order = PROFICIENCY_ORDER.get(current_level, 0)
                required_order = PROFICIENCY_ORDER.get(required_level, 0)
                if current_order < required_order:
                    is_gap = True

            if is_gap:
                # Create skill gap
                priority = idx + 1  # Priority based on order in requirements
                skill_gap = await self.skill_gap_repo.create_skill_gap(
                    roadmap_id=roadmap.id,
                    skill_name=skill_name,
                    required_level=required_level,
                    current_level=current_level,
                    priority=priority,
                )
                skill_gaps.append(skill_gap)

                # Add resource recommendations
                await self._add_resource_recommendations(skill_gap, skill_name)

        return skill_gaps

    async def _add_resource_recommendations(
        self,
        skill_gap: SkillGap,
        skill_name: str,
    ) -> list[ResourceRecommendation]:
        """Add resource recommendations for a skill gap.
        
        Requirement 26.3: Recommend courses and resources to fill skill gaps
        """
        recommendations = []
        
        # Check if we have predefined resources for this skill
        resources = SKILL_RESOURCES.get(skill_name, [])
        
        if not resources:
            # Add generic recommendations
            resources = [
                {
                    "title": f"Learn {skill_name} - Online Course",
                    "type": "course",
                    "platform": "Various",
                    "hours": "20",
                },
                {
                    "title": f"{skill_name} Documentation",
                    "type": "documentation",
                    "platform": "Official",
                    "hours": "10",
                },
            ]

        for resource in resources:
            resource_type = ResourceType(resource.get("type", "course"))
            estimated_hours = Decimal(resource.get("hours", "0")) if resource.get("hours") else None
            
            rec = await self.resource_repo.create_recommendation(
                skill_gap_id=skill_gap.id,
                title=resource["title"],
                resource_type=resource_type,
                platform=resource.get("platform"),
                estimated_hours=estimated_hours,
            )
            recommendations.append(rec)

        return recommendations

    async def get_roadmap(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[RoadmapDetailResponse]:
        """Get a roadmap with full details."""
        roadmap = await self.roadmap_repo.get_roadmap_with_details(roadmap_id, user_id)
        if not roadmap:
            return None
        return RoadmapDetailResponse.model_validate(roadmap)

    async def get_active_roadmap(
        self,
        user_id: uuid.UUID,
    ) -> Optional[RoadmapDetailResponse]:
        """Get the user's active roadmap."""
        roadmap = await self.roadmap_repo.get_active_roadmap(user_id)
        if not roadmap:
            return None
        return RoadmapDetailResponse.model_validate(roadmap)

    async def get_roadmaps(
        self,
        user_id: uuid.UUID,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedRoadmapResponse:
        """Get roadmaps for a user with optional filtering."""
        roadmaps, total = await self.roadmap_repo.get_roadmaps(
            user_id=user_id,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
        
        items = [RoadmapResponse.model_validate(r) for r in roadmaps]
        return PaginatedRoadmapResponse.create(items, total, page, page_size)

    async def update_roadmap(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RoadmapUpdate,
    ) -> Optional[RoadmapDetailResponse]:
        """Update a roadmap.
        
        Requirement 26.5: Adjust roadmap based on user progress and feedback
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return None

        update_data = data.model_dump(exclude_unset=True)
        
        # If activating this roadmap, deactivate others
        if update_data.get("is_active") is True:
            await self.roadmap_repo.deactivate_other_roadmaps(user_id, roadmap_id)

        await self.roadmap_repo.update_roadmap(roadmap, **update_data)
        
        return await self.get_roadmap(roadmap_id, user_id)

    async def delete_roadmap(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a roadmap."""
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return False
        await self.roadmap_repo.delete_roadmap(roadmap)
        return True

    async def complete_milestone(
        self,
        roadmap_id: uuid.UUID,
        milestone_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[MilestoneResponse]:
        """Mark a milestone as completed.
        
        Requirement 26.4: Track milestone completion and update roadmap progress
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return None

        milestone = await self.milestone_repo.get_milestone_by_id(milestone_id, roadmap_id)
        if not milestone:
            return None

        # Update milestone status
        now = datetime.now(timezone.utc)
        await self.milestone_repo.update_milestone(
            milestone,
            status=MilestoneStatus.COMPLETED,
            completed_at=now,
        )

        # Recalculate roadmap progress
        progress = await self.roadmap_repo.calculate_progress(roadmap_id)
        await self.roadmap_repo.update_roadmap(roadmap, current_progress=progress)

        return MilestoneResponse.model_validate(milestone)

    async def update_milestone(
        self,
        roadmap_id: uuid.UUID,
        milestone_id: uuid.UUID,
        user_id: uuid.UUID,
        data: MilestoneUpdate,
    ) -> Optional[MilestoneResponse]:
        """Update a milestone.
        
        Requirement 26.4: Update milestone status
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return None

        milestone = await self.milestone_repo.get_milestone_by_id(milestone_id, roadmap_id)
        if not milestone:
            return None

        update_data = data.model_dump(exclude_unset=True)
        
        # Handle status change to completed
        if update_data.get("status") == MilestoneStatus.COMPLETED and milestone.status != MilestoneStatus.COMPLETED:
            update_data["completed_at"] = datetime.now(timezone.utc)
        elif update_data.get("status") and update_data["status"] != MilestoneStatus.COMPLETED:
            update_data["completed_at"] = None

        await self.milestone_repo.update_milestone(milestone, **update_data)

        # Recalculate roadmap progress
        progress = await self.roadmap_repo.calculate_progress(roadmap_id)
        await self.roadmap_repo.update_roadmap(roadmap, current_progress=progress)

        return MilestoneResponse.model_validate(milestone)

    async def get_skill_gaps(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
        include_filled: bool = True,
    ) -> list[SkillGapResponse]:
        """Get skill gaps for a roadmap.
        
        Requirement 26.2: List skill gaps
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return []

        skill_gaps = await self.skill_gap_repo.get_skill_gaps_for_roadmap(
            roadmap_id, include_filled
        )
        return [SkillGapResponse.model_validate(sg) for sg in skill_gaps]

    async def get_skill_gap_summary(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[SkillGapSummary]:
        """Get a summary of skill gaps.
        
        Requirement 26.2: Skill gap analysis
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return None

        skill_gaps = await self.skill_gap_repo.get_skill_gaps_for_roadmap(roadmap_id)
        
        total = len(skill_gaps)
        filled = sum(1 for sg in skill_gaps if sg.is_filled)
        unfilled = total - filled
        
        # Get high priority gaps (priority <= 3)
        high_priority = [
            SkillGapResponse.model_validate(sg)
            for sg in skill_gaps
            if sg.priority <= 3 and not sg.is_filled
        ]

        return SkillGapSummary(
            total_gaps=total,
            filled_gaps=filled,
            unfilled_gaps=unfilled,
            high_priority_gaps=high_priority,
        )

    async def update_skill_gap(
        self,
        roadmap_id: uuid.UUID,
        skill_gap_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SkillGapUpdate,
    ) -> Optional[SkillGapResponse]:
        """Update a skill gap (e.g., mark as filled).
        
        Requirement 26.5: Adjust roadmap based on user progress
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return None

        skill_gap = await self.skill_gap_repo.get_skill_gap_by_id(skill_gap_id, roadmap_id)
        if not skill_gap:
            return None

        await self.skill_gap_repo.update_skill_gap(skill_gap, is_filled=data.is_filled)
        
        # Refresh to get updated data with recommendations
        skill_gap = await self.skill_gap_repo.get_skill_gap_by_id(skill_gap_id, roadmap_id)
        return SkillGapResponse.model_validate(skill_gap)

    async def complete_resource(
        self,
        roadmap_id: uuid.UUID,
        resource_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ResourceCompletionUpdate,
    ) -> bool:
        """Mark a resource recommendation as completed.
        
        Requirement 26.3: Track resource completion
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return False

        recommendation = await self.resource_repo.get_recommendation_by_id(resource_id)
        if not recommendation:
            return False

        # Verify the resource belongs to this roadmap
        skill_gap = await self.skill_gap_repo.get_skill_gap_by_id(
            recommendation.skill_gap_id, roadmap_id
        )
        if not skill_gap:
            return False

        await self.resource_repo.mark_completed(recommendation, data.is_completed)
        return True

    async def get_roadmap_progress(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[RoadmapProgressResponse]:
        """Get progress summary for a roadmap.
        
        Requirement 26.4: Track milestone completion
        """
        roadmap = await self.roadmap_repo.get_roadmap_with_details(roadmap_id, user_id)
        if not roadmap:
            return None

        milestones = roadmap.milestones
        milestones_total = len(milestones)
        milestones_completed = sum(
            1 for m in milestones if m.status == MilestoneStatus.COMPLETED
        )
        milestones_in_progress = sum(
            1 for m in milestones if m.status == MilestoneStatus.IN_PROGRESS
        )

        skill_gaps = roadmap.skill_gaps
        skill_gaps_total = len(skill_gaps)
        skill_gaps_filled = sum(1 for sg in skill_gaps if sg.is_filled)

        # Estimate completion date based on progress
        estimated_completion = None
        if milestones_total > 0 and milestones_completed < milestones_total:
            remaining_milestones = [
                m for m in milestones
                if m.status != MilestoneStatus.COMPLETED and m.target_date
            ]
            if remaining_milestones:
                last_milestone = max(remaining_milestones, key=lambda m: m.target_date)
                estimated_completion = last_milestone.target_date

        return RoadmapProgressResponse(
            roadmap_id=roadmap.id,
            target_role=roadmap.target_role,
            overall_progress=roadmap.current_progress,
            milestones_total=milestones_total,
            milestones_completed=milestones_completed,
            milestones_in_progress=milestones_in_progress,
            skill_gaps_total=skill_gaps_total,
            skill_gaps_filled=skill_gaps_filled,
            estimated_completion_date=estimated_completion,
        )

    async def refresh_skill_gaps(
        self,
        roadmap_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[RoadmapDetailResponse]:
        """Refresh skill gaps based on current user skills.
        
        Requirement 26.5: Adjust roadmap based on user progress
        """
        roadmap = await self.roadmap_repo.get_roadmap_by_id(roadmap_id, user_id)
        if not roadmap:
            return None

        # Get current skill gaps
        current_gaps = await self.skill_gap_repo.get_skill_gaps_for_roadmap(roadmap_id)
        
        # Get user's current skills
        user_skills = await self.skill_repo.get_all_skills(user_id)
        user_skill_map = {
            skill.name.lower(): skill.proficiency.value
            for skill in user_skills
        }

        # Update each skill gap
        for gap in current_gaps:
            current_level = user_skill_map.get(gap.skill_name.lower())
            
            # Check if gap is now filled
            is_filled = False
            if current_level:
                current_order = PROFICIENCY_ORDER.get(current_level, 0)
                required_order = PROFICIENCY_ORDER.get(gap.required_level, 0)
                if current_order >= required_order:
                    is_filled = True

            await self.skill_gap_repo.update_skill_gap(
                gap,
                current_level=current_level,
                is_filled=is_filled,
            )

        return await self.get_roadmap(roadmap_id, user_id)
