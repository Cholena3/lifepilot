"""Repository for resume database operations.

Requirement 30: Resume Builder
"""

import uuid
from typing import Optional, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import Resume, ResumeTemplate, ResumeVersion


class ResumeRepository:
    """Repository for Resume CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_resume(
        self,
        user_id: uuid.UUID,
        name: str,
        template: ResumeTemplate,
        content: dict[str, Any],
    ) -> Resume:
        """Create a new resume for a user.
        
        Requirement 30.1: Populate resume from profile, skills, achievements
        Requirement 30.2: Support multiple resume templates
        """
        resume = Resume(
            user_id=user_id,
            name=name,
            template=template,
            content=content,
            version=1,
        )
        self.session.add(resume)
        await self.session.flush()
        
        # Create initial version
        await self._create_version(resume)
        
        return resume

    async def get_resume_by_id(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Resume]:
        """Get a resume by ID for a specific user."""
        query = select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_resume_with_versions(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Resume]:
        """Get a resume with its version history."""
        query = (
            select(Resume)
            .options(selectinload(Resume.versions))
            .where(
                Resume.id == resume_id,
                Resume.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_resumes(
        self,
        user_id: uuid.UUID,
        template: Optional[ResumeTemplate] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Resume], int]:
        """Get resumes for a user with optional filtering and pagination.
        
        Requirement 30.5: Allow saving multiple resume versions
        """
        query = select(Resume).where(Resume.user_id == user_id)
        count_query = select(func.count(Resume.id)).where(Resume.user_id == user_id)

        if template:
            query = query.where(Resume.template == template)
            count_query = count_query.where(Resume.template == template)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering (most recent first)
        query = query.order_by(Resume.updated_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        resumes = list(result.scalars().all())

        return resumes, total

    async def get_all_resumes(self, user_id: uuid.UUID) -> list[Resume]:
        """Get all resumes for a user without pagination."""
        query = (
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.updated_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_resume(
        self,
        resume: Resume,
        create_version: bool = True,
        **kwargs,
    ) -> Resume:
        """Update a resume's attributes.
        
        Requirement 30.3: Edit resume content without affecting source data
        Requirement 30.5: Allow saving multiple resume versions
        """
        # Check if content is being updated
        content_changed = "content" in kwargs and kwargs["content"] != resume.content
        
        for key, value in kwargs.items():
            if hasattr(resume, key):
                setattr(resume, key, value)
        
        # Increment version if content changed
        if content_changed and create_version:
            resume.version += 1
            await self._create_version(resume)
        
        await self.session.flush()
        return resume

    async def delete_resume(self, resume: Resume) -> None:
        """Delete a resume and all its versions."""
        await self.session.delete(resume)
        await self.session.flush()

    async def _create_version(self, resume: Resume) -> ResumeVersion:
        """Create a version snapshot of the resume.
        
        Requirement 30.5: Allow saving multiple resume versions
        """
        version = ResumeVersion(
            resume_id=resume.id,
            version_number=resume.version,
            content=resume.content,
            pdf_url=resume.pdf_url,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_version(
        self,
        resume_id: uuid.UUID,
        version_number: int,
        user_id: uuid.UUID,
    ) -> Optional[ResumeVersion]:
        """Get a specific version of a resume."""
        # First verify the resume belongs to the user
        resume = await self.get_resume_by_id(resume_id, user_id)
        if not resume:
            return None
        
        query = select(ResumeVersion).where(
            ResumeVersion.resume_id == resume_id,
            ResumeVersion.version_number == version_number,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_versions(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ResumeVersion]:
        """Get all versions of a resume."""
        # First verify the resume belongs to the user
        resume = await self.get_resume_by_id(resume_id, user_id)
        if not resume:
            return []
        
        query = (
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_pdf_url(
        self,
        resume: Resume,
        pdf_url: str,
    ) -> Resume:
        """Update the PDF URL for a resume.
        
        Requirement 30.4: Export resumes in PDF format
        """
        resume.pdf_url = pdf_url
        await self.session.flush()
        return resume

    async def get_resume_count(self, user_id: uuid.UUID) -> int:
        """Get the total number of resumes for a user."""
        query = select(func.count(Resume.id)).where(Resume.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar() or 0
