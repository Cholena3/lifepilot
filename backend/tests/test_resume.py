"""Tests for resume builder.

Requirement 30: Resume Builder
"""

import uuid
from datetime import date, datetime
from typing import Any

import pytest
from httpx import AsyncClient

from app.models.resume import ResumeTemplate
from app.schemas.resume import (
    ResumeCreate,
    ResumeUpdate,
    ResumeContent,
    PersonalInfo,
    EducationEntry,
    SkillEntry,
    AchievementEntry,
    ResumePopulateRequest,
)


# Test fixtures
@pytest.fixture
def sample_content() -> dict[str, Any]:
    """Sample resume content for testing."""
    return {
        "personal_info": {
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-123-4567",
            "location": "San Francisco, CA",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "github_url": "https://github.com/johndoe",
        },
        "summary": "Experienced software engineer with 5+ years of experience.",
        "education": [
            {
                "institution": "MIT",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "start_date": "2015-09-01",
                "end_date": "2019-05-15",
                "gpa": "3.8",
            }
        ],
        "experience": [
            {
                "company": "Tech Corp",
                "role": "Senior Software Engineer",
                "location": "San Francisco, CA",
                "start_date": "2020-01-15",
                "is_current": True,
                "description": "Leading backend development team.",
                "highlights": [
                    "Improved API performance by 40%",
                    "Mentored 3 junior developers",
                ],
            }
        ],
        "skills": [
            {"name": "Python", "category": "Programming", "proficiency": "Expert"},
            {"name": "FastAPI", "category": "Framework", "proficiency": "Advanced"},
        ],
        "achievements": [
            {
                "title": "Best Innovation Award",
                "description": "Recognized for innovative solution",
                "date": "2023-06-15",
                "category": "Award",
            }
        ],
    }


class TestResumeAPI:
    """Tests for Resume API endpoints."""

    @pytest.mark.asyncio
    async def test_get_templates(self, client: AsyncClient):
        """Test getting available templates.
        
        Requirement 30.2: Support multiple resume templates
        """
        response = await client.get("/api/v1/career/resumes/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) == 5
        
        template_ids = [t["id"] for t in data["templates"]]
        assert "classic" in template_ids
        assert "modern" in template_ids
        assert "minimal" in template_ids
        assert "professional" in template_ids
        assert "creative" in template_ids

    @pytest.mark.asyncio
    async def test_create_resume(
        self,
        client: AsyncClient,
        sample_content: dict[str, Any],
    ):
        """Test creating a resume.
        
        Requirement 30.1: Populate resume from profile, skills, achievements
        """
        response = await client.post(
            "/api/v1/career/resumes",
            json={
                "name": "My Resume",
                "template": "classic",
                "content": sample_content,
                "populate_from_profile": False,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Resume"
        assert data["template"] == "classic"
        assert data["version"] == 1
        assert data["content"]["personal_info"]["full_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_list_resumes(
        self,
        client: AsyncClient,
        sample_content: dict[str, Any],
    ):
        """Test listing resumes.
        
        Requirement 30.5: Allow saving multiple resume versions
        """
        # Create a resume first
        await client.post(
            "/api/v1/career/resumes",
            json={
                "name": "Test Resume",
                "template": "modern",
                "content": sample_content,
                "populate_from_profile": False,
            },
        )
        
        response = await client.get("/api/v1/career/resumes")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_resume(
        self,
        client: AsyncClient,
        sample_content: dict[str, Any],
    ):
        """Test getting a specific resume."""
        # Create a resume
        create_response = await client.post(
            "/api/v1/career/resumes",
            json={
                "name": "Get Test Resume",
                "template": "classic",
                "content": sample_content,
                "populate_from_profile": False,
            },
        )
        resume_id = create_response.json()["id"]
        
        # Get the resume
        response = await client.get(f"/api/v1/career/resumes/{resume_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == resume_id
        assert data["name"] == "Get Test Resume"

    @pytest.mark.asyncio
    async def test_update_resume(
        self,
        client: AsyncClient,
        sample_content: dict[str, Any],
    ):
        """Test updating a resume.
        
        Requirement 30.3: Edit resume content without affecting source data
        """
        # Create a resume
        create_response = await client.post(
            "/api/v1/career/resumes",
            json={
                "name": "Update Test Resume",
                "template": "classic",
                "content": sample_content,
                "populate_from_profile": False,
            },
        )
        resume_id = create_response.json()["id"]
        
        # Update the resume
        response = await client.put(
            f"/api/v1/career/resumes/{resume_id}",
            json={
                "name": "Updated Resume Name",
                "content": {
                    "summary": "Updated professional summary",
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Resume Name"
        assert data["content"]["summary"] == "Updated professional summary"
        assert data["version"] == 2  # Version incremented

    @pytest.mark.asyncio
    async def test_delete_resume(
        self,
        client: AsyncClient,
        sample_content: dict[str, Any],
    ):
        """Test deleting a resume."""
        # Create a resume
        create_response = await client.post(
            "/api/v1/career/resumes",
            json={
                "name": "Delete Test Resume",
                "template": "classic",
                "content": sample_content,
                "populate_from_profile": False,
            },
        )
        resume_id = create_response.json()["id"]
        
        # Delete the resume
        response = await client.delete(f"/api/v1/career/resumes/{resume_id}")
        assert response.status_code == 204
        
        # Verify deleted
        get_response = await client.get(f"/api/v1/career/resumes/{resume_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_resume_versions(
        self,
        client: AsyncClient,
        sample_content: dict[str, Any],
    ):
        """Test getting resume versions.
        
        Requirement 30.5: Allow saving multiple resume versions
        """
        # Create a resume
        create_response = await client.post(
            "/api/v1/career/resumes",
            json={
                "name": "Version Test Resume",
                "template": "classic",
                "content": sample_content,
                "populate_from_profile": False,
            },
        )
        resume_id = create_response.json()["id"]
        
        # Update to create new version
        await client.put(
            f"/api/v1/career/resumes/{resume_id}",
            json={
                "content": {"summary": "Version 2"},
            },
        )
        
        # Get versions
        response = await client.get(f"/api/v1/career/resumes/{resume_id}/versions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["version_number"] == 2  # Most recent first

    @pytest.mark.asyncio
    async def test_export_pdf(
        self,
        client: AsyncClient,
        sample_content: dict[str, Any],
    ):
        """Test exporting resume as PDF.
        
        Requirement 30.4: Export resumes in PDF format
        """
        # Create a resume
        create_response = await client.post(
            "/api/v1/career/resumes",
            json={
                "name": "PDF Test Resume",
                "template": "classic",
                "content": sample_content,
                "populate_from_profile": False,
            },
        )
        resume_id = create_response.json()["id"]
        
        # Export PDF
        response = await client.get(f"/api/v1/career/resumes/{resume_id}/pdf")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        
        # Check PDF magic bytes
        assert response.content[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_resume_not_found(self, client: AsyncClient):
        """Test 404 for non-existent resume."""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/career/resumes/{fake_id}")
        assert response.status_code == 404


class TestResumeContentValidation:
    """Tests for resume content validation."""

    def test_personal_info_validation(self):
        """Test personal info validation."""
        info = PersonalInfo(
            full_name="John Doe",
            email="john@example.com",
        )
        assert info.full_name == "John Doe"
        assert info.email == "john@example.com"

    def test_education_entry_validation(self):
        """Test education entry validation."""
        edu = EducationEntry(
            institution="MIT",
            degree="BS Computer Science",
            gpa="3.8",
        )
        assert edu.institution == "MIT"
        assert edu.degree == "BS Computer Science"

    def test_skill_entry_validation(self):
        """Test skill entry validation."""
        skill = SkillEntry(
            name="Python",
            category="Programming",
            proficiency="Expert",
        )
        assert skill.name == "Python"
        assert skill.category == "Programming"

    def test_achievement_entry_validation(self):
        """Test achievement entry validation."""
        achievement = AchievementEntry(
            title="Best Developer Award",
            description="Recognized for excellence",
        )
        assert achievement.title == "Best Developer Award"
        assert achievement.description == "Recognized for excellence"
        
        # Test with date using alias
        achievement_with_date = AchievementEntry(
            title="Award 2",
            date="2023-06-15",  # Using alias
        )
        assert achievement_with_date.achieved_date == date(2023, 6, 15)

    def test_resume_content_full(self):
        """Test full resume content validation."""
        content = ResumeContent(
            personal_info=PersonalInfo(full_name="Test User"),
            summary="Professional summary",
            education=[
                EducationEntry(institution="University", degree="BS")
            ],
            skills=[
                SkillEntry(name="Python")
            ],
            achievements=[
                AchievementEntry(title="Award")
            ],
        )
        assert content.personal_info.full_name == "Test User"
        assert len(content.education) == 1
        assert len(content.skills) == 1
        assert len(content.achievements) == 1

    def test_resume_create_schema(self):
        """Test ResumeCreate schema validation."""
        data = ResumeCreate(
            name="  My Resume  ",  # Should be trimmed
            template=ResumeTemplate.MODERN,
            populate_from_profile=False,
        )
        assert data.name == "My Resume"
        assert data.template == ResumeTemplate.MODERN

    def test_resume_update_schema(self):
        """Test ResumeUpdate schema validation."""
        data = ResumeUpdate(
            name="  Updated Name  ",
            template=ResumeTemplate.PROFESSIONAL,
        )
        assert data.name == "Updated Name"
        assert data.template == ResumeTemplate.PROFESSIONAL
