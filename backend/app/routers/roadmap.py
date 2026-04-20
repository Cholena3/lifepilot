"""API router for career roadmap management.

Validates: Requirements 26.1, 26.2, 26.3, 26.4, 26.5
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.roadmap import (
    CareerGoalCreate,
    MilestoneResponse,
    MilestoneUpdate,
    PaginatedRoadmapResponse,
    ResourceCompletionUpdate,
    RoadmapDetailResponse,
    RoadmapProgressResponse,
    RoadmapUpdate,
    SkillGapResponse,
    SkillGapSummary,
    SkillGapUpdate,
)
from app.services.roadmap import RoadmapService

router = APIRouter(prefix="/roadmaps", tags=["career"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "",
    response_model=RoadmapDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a career roadmap",
    description="Create a new career roadmap from career goals. Generates milestones, identifies skill gaps, and recommends resources. Requirement 26.1, 26.2, 26.3",
)
async def create_roadmap(
    data: CareerGoalCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RoadmapDetailResponse:
    """Create a new career roadmap from career goals."""
    service = RoadmapService(db)
    return await service.create_roadmap(user_id, data)


@router.get(
    "",
    response_model=PaginatedRoadmapResponse,
    summary="List roadmaps",
    description="Get a paginated list of user's career roadmaps.",
)
async def list_roadmaps(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedRoadmapResponse:
    """Get paginated list of roadmaps for the current user."""
    service = RoadmapService(db)
    return await service.get_roadmaps(
        user_id=user_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/active",
    response_model=RoadmapDetailResponse,
    summary="Get active roadmap",
    description="Get the user's currently active career roadmap with all details.",
)
async def get_active_roadmap(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RoadmapDetailResponse:
    """Get the active roadmap for the current user."""
    service = RoadmapService(db)
    roadmap = await service.get_active_roadmap(user_id)
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active roadmap found",
        )
    return roadmap


@router.get(
    "/{roadmap_id}",
    response_model=RoadmapDetailResponse,
    summary="Get roadmap details",
    description="Get a roadmap with milestones, skill gaps, and resource recommendations.",
)
async def get_roadmap(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RoadmapDetailResponse:
    """Get a roadmap by ID with full details."""
    service = RoadmapService(db)
    roadmap = await service.get_roadmap(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found",
        )
    return roadmap


@router.put(
    "/{roadmap_id}",
    response_model=RoadmapDetailResponse,
    summary="Update a roadmap",
    description="Update a roadmap's details. Requirement 26.5",
)
async def update_roadmap(
    roadmap_id: uuid.UUID,
    data: RoadmapUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RoadmapDetailResponse:
    """Update a roadmap for the current user."""
    service = RoadmapService(db)
    roadmap = await service.update_roadmap(roadmap_id, user_id, data)
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found",
        )
    return roadmap


@router.delete(
    "/{roadmap_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a roadmap",
    description="Delete a career roadmap.",
)
async def delete_roadmap(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a roadmap for the current user."""
    service = RoadmapService(db)
    deleted = await service.delete_roadmap(roadmap_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found",
        )


@router.get(
    "/{roadmap_id}/progress",
    response_model=RoadmapProgressResponse,
    summary="Get roadmap progress",
    description="Get progress summary for a roadmap. Requirement 26.4",
)
async def get_roadmap_progress(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RoadmapProgressResponse:
    """Get progress summary for a roadmap."""
    service = RoadmapService(db)
    progress = await service.get_roadmap_progress(roadmap_id, user_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found",
        )
    return progress


@router.put(
    "/{roadmap_id}/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="Update a milestone",
    description="Update a milestone's details or status. Requirement 26.4",
)
async def update_milestone(
    roadmap_id: uuid.UUID,
    milestone_id: uuid.UUID,
    data: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> MilestoneResponse:
    """Update a milestone for a roadmap."""
    service = RoadmapService(db)
    milestone = await service.update_milestone(roadmap_id, milestone_id, user_id, data)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap or milestone not found",
        )
    return milestone


@router.post(
    "/{roadmap_id}/milestones/{milestone_id}/complete",
    response_model=MilestoneResponse,
    summary="Complete a milestone",
    description="Mark a milestone as completed and update roadmap progress. Requirement 26.4",
)
async def complete_milestone(
    roadmap_id: uuid.UUID,
    milestone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> MilestoneResponse:
    """Mark a milestone as completed."""
    service = RoadmapService(db)
    milestone = await service.complete_milestone(roadmap_id, milestone_id, user_id)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap or milestone not found",
        )
    return milestone


@router.get(
    "/{roadmap_id}/skill-gaps",
    response_model=list[SkillGapResponse],
    summary="Get skill gaps",
    description="Get skill gaps for a roadmap. Requirement 26.2",
)
async def get_skill_gaps(
    roadmap_id: uuid.UUID,
    include_filled: bool = Query(True, description="Include filled skill gaps"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[SkillGapResponse]:
    """Get skill gaps for a roadmap."""
    service = RoadmapService(db)
    return await service.get_skill_gaps(roadmap_id, user_id, include_filled)


@router.get(
    "/{roadmap_id}/skill-gaps/summary",
    response_model=SkillGapSummary,
    summary="Get skill gap summary",
    description="Get a summary of skill gaps for a roadmap. Requirement 26.2",
)
async def get_skill_gap_summary(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> SkillGapSummary:
    """Get skill gap summary for a roadmap."""
    service = RoadmapService(db)
    summary = await service.get_skill_gap_summary(roadmap_id, user_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found",
        )
    return summary


@router.put(
    "/{roadmap_id}/skill-gaps/{skill_gap_id}",
    response_model=SkillGapResponse,
    summary="Update a skill gap",
    description="Update a skill gap (e.g., mark as filled). Requirement 26.5",
)
async def update_skill_gap(
    roadmap_id: uuid.UUID,
    skill_gap_id: uuid.UUID,
    data: SkillGapUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> SkillGapResponse:
    """Update a skill gap for a roadmap."""
    service = RoadmapService(db)
    skill_gap = await service.update_skill_gap(roadmap_id, skill_gap_id, user_id, data)
    if not skill_gap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap or skill gap not found",
        )
    return skill_gap


@router.post(
    "/{roadmap_id}/resources/{resource_id}/complete",
    status_code=status.HTTP_200_OK,
    summary="Complete a resource",
    description="Mark a resource recommendation as completed. Requirement 26.3",
)
async def complete_resource(
    roadmap_id: uuid.UUID,
    resource_id: uuid.UUID,
    data: ResourceCompletionUpdate = ResourceCompletionUpdate(),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """Mark a resource as completed."""
    service = RoadmapService(db)
    success = await service.complete_resource(roadmap_id, resource_id, user_id, data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap or resource not found",
        )
    return {"success": True, "message": "Resource marked as completed"}


@router.post(
    "/{roadmap_id}/refresh-skill-gaps",
    response_model=RoadmapDetailResponse,
    summary="Refresh skill gaps",
    description="Refresh skill gaps based on current user skills. Requirement 26.5",
)
async def refresh_skill_gaps(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RoadmapDetailResponse:
    """Refresh skill gaps based on current user skills."""
    service = RoadmapService(db)
    roadmap = await service.refresh_skill_gaps(roadmap_id, user_id)
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found",
        )
    return roadmap
