"""API router for skill inventory management."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.skill import ProficiencyLevel, SkillCategory
from app.schemas.skill import (
    PaginatedSkillResponse,
    SkillCreate,
    SkillResponse,
    SkillsGroupedResponse,
    SkillSuggestionsResponse,
    SkillUpdate,
    SkillWithHistoryResponse,
)
from app.services.skill import SkillService

router = APIRouter(prefix="/skills", tags=["career"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new skill",
    description="Add a new skill to the user's skill inventory. Requirement 24.1",
)
async def create_skill(
    data: SkillCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> SkillResponse:
    """Create a new skill for the current user."""
    service = SkillService(db)
    try:
        skill = await service.add_skill(user_id, data)
        return SkillResponse.model_validate(skill)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "",
    response_model=PaginatedSkillResponse,
    summary="List skills",
    description="Get a paginated list of user's skills with optional filtering.",
)
async def list_skills(
    category: Optional[SkillCategory] = Query(None, description="Filter by category"),
    proficiency: Optional[ProficiencyLevel] = Query(None, description="Filter by proficiency level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedSkillResponse:
    """Get paginated list of skills for the current user."""
    service = SkillService(db)
    return await service.get_skills(
        user_id=user_id,
        category=category,
        proficiency=proficiency,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/grouped",
    response_model=SkillsGroupedResponse,
    summary="Get skills grouped by category",
    description="Get all skills grouped by category. Requirement 24.4",
)
async def get_skills_grouped(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> SkillsGroupedResponse:
    """Get skills grouped by category for the current user."""
    service = SkillService(db)
    return await service.get_skills_grouped(user_id)


@router.get(
    "/suggestions",
    response_model=SkillSuggestionsResponse,
    summary="Get skill suggestions",
    description="Get skill suggestions based on career goals. Requirement 24.5",
)
async def get_skill_suggestions(
    roles: Optional[str] = Query(
        None,
        description="Comma-separated list of preferred roles",
    ),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> SkillSuggestionsResponse:
    """Get skill suggestions based on career preferences."""
    service = SkillService(db)
    preferred_roles = roles.split(",") if roles else None
    return await service.get_skill_suggestions(user_id, preferred_roles)


@router.get(
    "/{skill_id}",
    response_model=SkillWithHistoryResponse,
    summary="Get skill details",
    description="Get a skill with its proficiency history. Requirement 24.3",
)
async def get_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> SkillWithHistoryResponse:
    """Get a skill by ID with proficiency history."""
    service = SkillService(db)
    skill = await service.get_skill_with_history(skill_id, user_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
    return skill


@router.put(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Update a skill",
    description="Update a skill's details. Proficiency changes are tracked. Requirement 24.3",
)
async def update_skill(
    skill_id: uuid.UUID,
    data: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> SkillResponse:
    """Update a skill for the current user."""
    service = SkillService(db)
    try:
        skill = await service.update_skill(skill_id, user_id, data)
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found",
            )
        return SkillResponse.model_validate(skill)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a skill",
    description="Delete a skill from the user's inventory.",
)
async def delete_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a skill for the current user."""
    service = SkillService(db)
    deleted = await service.delete_skill(skill_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
