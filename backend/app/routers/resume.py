"""API router for resume builder.

Requirement 30: Resume Builder
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.resume import ResumeTemplate
from app.schemas.resume import (
    ResumeCreate,
    ResumeResponse,
    ResumeSummaryResponse,
    ResumeUpdate,
    ResumeVersionResponse,
    ResumeTemplatesResponse,
    ResumePDFResponse,
    ResumePopulateRequest,
    PaginatedResumeResponse,
)
from app.services.resume import ResumeService

router = APIRouter(prefix="/resumes", tags=["career"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get(
    "/templates",
    response_model=ResumeTemplatesResponse,
    summary="Get available resume templates",
    description="Get list of available resume templates. Requirement 30.2",
)
async def get_templates(
    db: AsyncSession = Depends(get_db),
) -> ResumeTemplatesResponse:
    """Get available resume templates."""
    service = ResumeService(db)
    return service.get_templates()


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new resume",
    description="Create a new resume, optionally populated from profile data. Requirement 30.1",
)
async def create_resume(
    data: ResumeCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ResumeResponse:
    """Create a new resume for the current user."""
    service = ResumeService(db)
    resume = await service.create_resume(user_id, data)
    return ResumeResponse.model_validate(resume)


@router.get(
    "",
    response_model=PaginatedResumeResponse,
    summary="List resumes",
    description="Get a paginated list of user's resumes. Requirement 30.5",
)
async def list_resumes(
    template: Optional[ResumeTemplate] = Query(None, description="Filter by template"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedResumeResponse:
    """Get paginated list of resumes for the current user."""
    service = ResumeService(db)
    return await service.get_resumes(
        user_id=user_id,
        template=template,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get resume details",
    description="Get a resume by ID.",
)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ResumeResponse:
    """Get a resume by ID."""
    service = ResumeService(db)
    resume = await service.get_resume(resume_id, user_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    return ResumeResponse.model_validate(resume)


@router.put(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Update a resume",
    description="Update a resume's details. Requirement 30.3",
)
async def update_resume(
    resume_id: uuid.UUID,
    data: ResumeUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ResumeResponse:
    """Update a resume for the current user."""
    service = ResumeService(db)
    resume = await service.update_resume(resume_id, user_id, data)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    return ResumeResponse.model_validate(resume)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume",
    description="Delete a resume.",
)
async def delete_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a resume for the current user."""
    service = ResumeService(db)
    deleted = await service.delete_resume(resume_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )


@router.post(
    "/{resume_id}/populate",
    response_model=ResumeResponse,
    summary="Populate resume from profile",
    description="Populate resume content from user's profile, skills, and achievements. Requirement 30.1",
)
async def populate_resume(
    resume_id: uuid.UUID,
    options: ResumePopulateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ResumeResponse:
    """Populate resume from profile data."""
    service = ResumeService(db)
    resume = await service.populate_resume(resume_id, user_id, options)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    return ResumeResponse.model_validate(resume)


@router.get(
    "/{resume_id}/versions",
    response_model=list[ResumeVersionResponse],
    summary="Get resume versions",
    description="Get all versions of a resume. Requirement 30.5",
)
async def get_resume_versions(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[ResumeVersionResponse]:
    """Get all versions of a resume."""
    service = ResumeService(db)
    
    # Verify resume exists
    resume = await service.get_resume(resume_id, user_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    
    return await service.get_versions(resume_id, user_id)


@router.get(
    "/{resume_id}/versions/{version_number}",
    response_model=ResumeVersionResponse,
    summary="Get specific resume version",
    description="Get a specific version of a resume. Requirement 30.5",
)
async def get_resume_version(
    resume_id: uuid.UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ResumeVersionResponse:
    """Get a specific version of a resume."""
    service = ResumeService(db)
    version = await service.get_version(resume_id, version_number, user_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found",
        )
    return version


@router.get(
    "/{resume_id}/pdf",
    summary="Export resume as PDF",
    description="Export resume as PDF file. Requirement 30.4",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF file of the resume",
        }
    },
)
async def export_resume_pdf(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response:
    """Export resume as PDF."""
    service = ResumeService(db)
    
    # Get resume to verify it exists and get the name
    resume = await service.get_resume(resume_id, user_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    
    pdf_bytes = await service.export_pdf(resume_id, user_id)
    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF",
        )
    
    # Create filename from resume name
    filename = f"{resume.name.replace(' ', '_')}_resume.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
