"""Service for resume builder.

Requirement 30: Resume Builder
- Populate resume from profile, skills, achievements
- Support multiple templates
- Export as PDF
- Save multiple versions
"""

import io
import uuid
from datetime import datetime, date
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume, ResumeTemplate, ResumeVersion
from app.repositories.resume import ResumeRepository
from app.repositories.profile import ProfileRepository
from app.repositories.skill import SkillRepository
from app.repositories.achievement import AchievementRepository
from app.schemas.resume import (
    ResumeCreate,
    ResumeUpdate,
    ResumeResponse,
    ResumeSummaryResponse,
    ResumeVersionResponse,
    ResumeTemplateInfo,
    ResumeTemplatesResponse,
    ResumePDFResponse,
    ResumePopulateRequest,
    ResumeContent,
    PaginatedResumeResponse,
    PersonalInfo,
    EducationEntry,
    SkillEntry,
    AchievementEntry,
)


# Template metadata
TEMPLATE_INFO: dict[ResumeTemplate, dict[str, str]] = {
    ResumeTemplate.CLASSIC: {
        "name": "Classic",
        "description": "Traditional resume format with clear sections and professional styling.",
    },
    ResumeTemplate.MODERN: {
        "name": "Modern",
        "description": "Contemporary design with clean lines and modern typography.",
    },
    ResumeTemplate.MINIMAL: {
        "name": "Minimal",
        "description": "Simple and clean layout focusing on content over design.",
    },
    ResumeTemplate.PROFESSIONAL: {
        "name": "Professional",
        "description": "Formal business style suitable for corporate positions.",
    },
    ResumeTemplate.CREATIVE: {
        "name": "Creative",
        "description": "Unique design for creative industry positions.",
    },
}


class ResumeService:
    """Service for resume builder.
    
    Implements Requirements 30.1-30.5 for resume management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.profile_repo = ProfileRepository(session)
        self.skill_repo = SkillRepository(session)
        self.achievement_repo = AchievementRepository(session)

    async def create_resume(
        self,
        user_id: uuid.UUID,
        data: ResumeCreate,
    ) -> Resume:
        """Create a new resume for a user.
        
        Requirement 30.1: Populate resume from profile, skills, achievements
        Requirement 30.2: Support multiple resume templates
        """
        content: dict[str, Any] = {}
        
        if data.content:
            content = data.content.model_dump(mode="json")
        
        if data.populate_from_profile:
            # Populate from user's profile, skills, and achievements
            populated_content = await self._populate_from_profile(user_id)
            # Merge with provided content (provided content takes precedence)
            for key, value in populated_content.items():
                if key not in content or not content[key]:
                    content[key] = value
        
        resume = await self.resume_repo.create_resume(
            user_id=user_id,
            name=data.name,
            template=data.template,
            content=content,
        )
        return resume

    async def get_resume(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Resume]:
        """Get a resume by ID."""
        return await self.resume_repo.get_resume_by_id(resume_id, user_id)

    async def get_resumes(
        self,
        user_id: uuid.UUID,
        template: Optional[ResumeTemplate] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResumeResponse:
        """Get resumes for a user with optional filtering.
        
        Requirement 30.5: Allow saving multiple resume versions
        """
        resumes, total = await self.resume_repo.get_resumes(
            user_id=user_id,
            template=template,
            page=page,
            page_size=page_size,
        )
        
        items = [ResumeSummaryResponse.model_validate(r) for r in resumes]
        return PaginatedResumeResponse.create(items, total, page, page_size)

    async def update_resume(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ResumeUpdate,
    ) -> Optional[Resume]:
        """Update a resume.
        
        Requirement 30.3: Edit resume content without affecting source data
        """
        resume = await self.resume_repo.get_resume_by_id(resume_id, user_id)
        if not resume:
            return None

        update_data: dict[str, Any] = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.template is not None:
            update_data["template"] = data.template
        if data.content is not None:
            update_data["content"] = data.content.model_dump(mode="json")

        resume = await self.resume_repo.update_resume(resume, **update_data)
        return resume

    async def delete_resume(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a resume."""
        resume = await self.resume_repo.get_resume_by_id(resume_id, user_id)
        if not resume:
            return False
        await self.resume_repo.delete_resume(resume)
        return True

    async def get_versions(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ResumeVersionResponse]:
        """Get all versions of a resume.
        
        Requirement 30.5: Allow saving multiple resume versions
        """
        versions = await self.resume_repo.get_versions(resume_id, user_id)
        return [ResumeVersionResponse.model_validate(v) for v in versions]

    async def get_version(
        self,
        resume_id: uuid.UUID,
        version_number: int,
        user_id: uuid.UUID,
    ) -> Optional[ResumeVersionResponse]:
        """Get a specific version of a resume."""
        version = await self.resume_repo.get_version(resume_id, version_number, user_id)
        if not version:
            return None
        return ResumeVersionResponse.model_validate(version)

    def get_templates(self) -> ResumeTemplatesResponse:
        """Get available resume templates.
        
        Requirement 30.2: Support multiple resume templates
        """
        templates = [
            ResumeTemplateInfo(
                id=template,
                name=info["name"],
                description=info["description"],
            )
            for template, info in TEMPLATE_INFO.items()
        ]
        return ResumeTemplatesResponse(templates=templates)

    async def populate_resume(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        options: ResumePopulateRequest,
    ) -> Optional[Resume]:
        """Populate resume content from profile data.
        
        Requirement 30.1: Populate resume from profile, skills, achievements
        """
        resume = await self.resume_repo.get_resume_by_id(resume_id, user_id)
        if not resume:
            return None

        populated_content = await self._populate_from_profile(
            user_id,
            include_education=options.include_education,
            include_skills=options.include_skills,
            include_achievements=options.include_achievements,
            achievement_categories=options.achievement_categories,
            skill_categories=options.skill_categories,
            max_achievements=options.max_achievements,
            max_skills=options.max_skills,
        )

        # Merge with existing content
        current_content = dict(resume.content)
        for key, value in populated_content.items():
            if value:  # Only update if there's data
                current_content[key] = value

        resume = await self.resume_repo.update_resume(
            resume, content=current_content
        )
        return resume

    async def export_pdf(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[bytes]:
        """Export resume as PDF.
        
        Requirement 30.4: Export resumes in PDF format
        """
        resume = await self.resume_repo.get_resume_by_id(resume_id, user_id)
        if not resume:
            return None

        # Generate PDF based on template
        pdf_bytes = self._generate_pdf(resume)
        return pdf_bytes

    def _generate_pdf(self, resume: Resume) -> bytes:
        """Generate PDF from resume content.
        
        Requirement 30.4: Export resumes in PDF format
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        # Get styles based on template
        styles = self._get_template_styles(resume.template)
        story = []
        content = resume.content

        # Personal Info / Header
        personal_info = content.get("personal_info", {})
        if personal_info:
            name = personal_info.get("full_name", "")
            if name:
                story.append(Paragraph(name, styles["name"]))
            
            # Contact info line
            contact_parts = []
            if personal_info.get("email"):
                contact_parts.append(personal_info["email"])
            if personal_info.get("phone"):
                contact_parts.append(personal_info["phone"])
            if personal_info.get("location"):
                contact_parts.append(personal_info["location"])
            
            if contact_parts:
                story.append(Paragraph(" | ".join(contact_parts), styles["contact"]))
            
            # Links line
            link_parts = []
            if personal_info.get("linkedin_url"):
                link_parts.append(f"LinkedIn: {personal_info['linkedin_url']}")
            if personal_info.get("github_url"):
                link_parts.append(f"GitHub: {personal_info['github_url']}")
            if personal_info.get("portfolio_url"):
                link_parts.append(f"Portfolio: {personal_info['portfolio_url']}")
            
            if link_parts:
                story.append(Paragraph(" | ".join(link_parts), styles["contact"]))
            
            story.append(Spacer(1, 0.2 * inch))

        # Summary
        summary = content.get("summary")
        if summary:
            story.append(Paragraph("PROFESSIONAL SUMMARY", styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(summary, styles["body"]))
            story.append(Spacer(1, 0.2 * inch))

        # Education
        education = content.get("education", [])
        if education:
            story.append(Paragraph("EDUCATION", styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            
            for edu in education:
                degree_line = f"<b>{edu.get('degree', '')}</b>"
                if edu.get("field_of_study"):
                    degree_line += f" in {edu['field_of_study']}"
                story.append(Paragraph(degree_line, styles["item_title"]))
                
                inst_line = edu.get("institution", "")
                dates = self._format_date_range(edu.get("start_date"), edu.get("end_date"))
                if dates:
                    inst_line += f" | {dates}"
                if edu.get("gpa"):
                    inst_line += f" | GPA: {edu['gpa']}"
                story.append(Paragraph(inst_line, styles["item_subtitle"]))
                
                if edu.get("description"):
                    story.append(Paragraph(edu["description"], styles["body"]))
                story.append(Spacer(1, 0.1 * inch))
            
            story.append(Spacer(1, 0.1 * inch))

        # Experience
        experience = content.get("experience", [])
        if experience:
            story.append(Paragraph("EXPERIENCE", styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            
            for exp in experience:
                role_line = f"<b>{exp.get('role', '')}</b>"
                story.append(Paragraph(role_line, styles["item_title"]))
                
                company_line = exp.get("company", "")
                if exp.get("location"):
                    company_line += f", {exp['location']}"
                dates = self._format_date_range(
                    exp.get("start_date"),
                    exp.get("end_date"),
                    exp.get("is_current", False)
                )
                if dates:
                    company_line += f" | {dates}"
                story.append(Paragraph(company_line, styles["item_subtitle"]))
                
                if exp.get("description"):
                    story.append(Paragraph(exp["description"], styles["body"]))
                
                highlights = exp.get("highlights", [])
                for highlight in highlights:
                    story.append(Paragraph(f"• {highlight}", styles["bullet"]))
                
                story.append(Spacer(1, 0.1 * inch))
            
            story.append(Spacer(1, 0.1 * inch))

        # Skills
        skills = content.get("skills", [])
        if skills:
            story.append(Paragraph("SKILLS", styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            
            # Group skills by category
            skills_by_category: dict[str, list[str]] = {}
            for skill in skills:
                category = skill.get("category", "Other") or "Other"
                if category not in skills_by_category:
                    skills_by_category[category] = []
                skill_text = skill.get("name", "")
                if skill.get("proficiency"):
                    skill_text += f" ({skill['proficiency']})"
                skills_by_category[category].append(skill_text)
            
            for category, skill_list in skills_by_category.items():
                skills_text = f"<b>{category}:</b> {', '.join(skill_list)}"
                story.append(Paragraph(skills_text, styles["body"]))
            
            story.append(Spacer(1, 0.2 * inch))

        # Achievements
        achievements = content.get("achievements", [])
        if achievements:
            story.append(Paragraph("ACHIEVEMENTS", styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            
            for achievement in achievements:
                title = achievement.get("title", "")
                date_str = ""
                if achievement.get("date"):
                    date_str = self._format_date(achievement["date"])
                
                ach_line = f"<b>{title}</b>"
                if date_str:
                    ach_line += f" ({date_str})"
                story.append(Paragraph(ach_line, styles["item_title"]))
                
                if achievement.get("description"):
                    story.append(Paragraph(achievement["description"], styles["body"]))
                story.append(Spacer(1, 0.05 * inch))
            
            story.append(Spacer(1, 0.1 * inch))

        # Certifications
        certifications = content.get("certifications", [])
        if certifications:
            story.append(Paragraph("CERTIFICATIONS", styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            
            for cert in certifications:
                cert_line = f"<b>{cert.get('name', '')}</b>"
                if cert.get("issuer"):
                    cert_line += f" - {cert['issuer']}"
                if cert.get("issue_date"):
                    cert_line += f" ({self._format_date(cert['issue_date'])})"
                story.append(Paragraph(cert_line, styles["body"]))
            
            story.append(Spacer(1, 0.2 * inch))

        # Projects
        projects = content.get("projects", [])
        if projects:
            story.append(Paragraph("PROJECTS", styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            
            for project in projects:
                story.append(Paragraph(f"<b>{project.get('name', '')}</b>", styles["item_title"]))
                
                if project.get("description"):
                    story.append(Paragraph(project["description"], styles["body"]))
                
                technologies = project.get("technologies", [])
                if technologies:
                    tech_line = f"<i>Technologies: {', '.join(technologies)}</i>"
                    story.append(Paragraph(tech_line, styles["body"]))
                
                story.append(Spacer(1, 0.1 * inch))

        # Custom sections
        custom_sections = content.get("custom_sections", [])
        for section in custom_sections:
            story.append(Paragraph(section.get("title", "").upper(), styles["section_header"]))
            story.append(HRFlowable(width="100%", thickness=1, color=styles["line_color"]))
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(section.get("content", ""), styles["body"]))
            story.append(Spacer(1, 0.2 * inch))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _get_template_styles(self, template: ResumeTemplate) -> dict[str, Any]:
        """Get styles based on template.
        
        Requirement 30.2: Support multiple resume templates
        """
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

        # Base styles
        base_styles = {
            "name": ParagraphStyle(
                "Name",
                fontSize=18,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
                spaceAfter=6,
            ),
            "contact": ParagraphStyle(
                "Contact",
                fontSize=10,
                fontName="Helvetica",
                alignment=TA_CENTER,
                spaceAfter=3,
            ),
            "section_header": ParagraphStyle(
                "SectionHeader",
                fontSize=12,
                fontName="Helvetica-Bold",
                spaceBefore=6,
                spaceAfter=3,
            ),
            "item_title": ParagraphStyle(
                "ItemTitle",
                fontSize=11,
                fontName="Helvetica",
                spaceAfter=2,
            ),
            "item_subtitle": ParagraphStyle(
                "ItemSubtitle",
                fontSize=10,
                fontName="Helvetica",
                textColor=colors.gray,
                spaceAfter=3,
            ),
            "body": ParagraphStyle(
                "Body",
                fontSize=10,
                fontName="Helvetica",
                alignment=TA_JUSTIFY,
                spaceAfter=3,
            ),
            "bullet": ParagraphStyle(
                "Bullet",
                fontSize=10,
                fontName="Helvetica",
                leftIndent=15,
                spaceAfter=2,
            ),
            "line_color": colors.black,
        }

        # Template-specific customizations
        if template == ResumeTemplate.MODERN:
            base_styles["name"].textColor = colors.HexColor("#2563eb")
            base_styles["section_header"].textColor = colors.HexColor("#2563eb")
            base_styles["line_color"] = colors.HexColor("#2563eb")
        elif template == ResumeTemplate.MINIMAL:
            base_styles["name"].fontSize = 16
            base_styles["section_header"].fontSize = 11
            base_styles["line_color"] = colors.lightgrey
        elif template == ResumeTemplate.PROFESSIONAL:
            base_styles["name"].fontName = "Times-Bold"
            base_styles["section_header"].fontName = "Times-Bold"
            base_styles["body"].fontName = "Times-Roman"
        elif template == ResumeTemplate.CREATIVE:
            base_styles["name"].textColor = colors.HexColor("#7c3aed")
            base_styles["section_header"].textColor = colors.HexColor("#7c3aed")
            base_styles["line_color"] = colors.HexColor("#7c3aed")

        return base_styles

    async def _populate_from_profile(
        self,
        user_id: uuid.UUID,
        include_education: bool = True,
        include_skills: bool = True,
        include_achievements: bool = True,
        achievement_categories: Optional[list[str]] = None,
        skill_categories: Optional[list[str]] = None,
        max_achievements: int = 10,
        max_skills: int = 20,
    ) -> dict[str, Any]:
        """Populate resume content from user's profile data.
        
        Requirement 30.1: Populate resume from profile, skills, achievements
        """
        content: dict[str, Any] = {}

        # Get profile data
        profile = await self.profile_repo.get_profile_by_user_id(user_id)
        student_profile = await self.profile_repo.get_student_profile_by_user_id(user_id)

        # Personal info from profile
        if profile:
            personal_info: dict[str, Any] = {}
            if profile.first_name or profile.last_name:
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                personal_info["full_name"] = full_name
            content["personal_info"] = personal_info

        # Education from student profile
        if include_education and student_profile:
            education = []
            if student_profile.institution or student_profile.degree:
                edu_entry: dict[str, Any] = {}
                if student_profile.institution:
                    edu_entry["institution"] = student_profile.institution
                if student_profile.degree:
                    edu_entry["degree"] = student_profile.degree
                if student_profile.branch:
                    edu_entry["field_of_study"] = student_profile.branch
                if student_profile.cgpa:
                    edu_entry["gpa"] = str(student_profile.cgpa)
                if student_profile.graduation_year:
                    edu_entry["end_date"] = f"{student_profile.graduation_year}-06-01"
                education.append(edu_entry)
            content["education"] = education

        # Skills
        if include_skills:
            skills = await self.skill_repo.get_skills_by_user_id(user_id)
            skill_entries = []
            
            for skill in skills[:max_skills]:
                # Filter by category if specified
                if skill_categories:
                    if skill.category.value not in skill_categories:
                        continue
                
                skill_entries.append({
                    "name": skill.name,
                    "category": skill.category.value.replace("_", " ").title(),
                    "proficiency": skill.proficiency.value.title(),
                })
            
            content["skills"] = skill_entries

        # Achievements
        if include_achievements:
            achievements = await self.achievement_repo.get_all_achievements(user_id)
            achievement_entries = []
            
            for achievement in achievements[:max_achievements]:
                # Filter by category if specified
                if achievement_categories:
                    if achievement.category.value not in achievement_categories:
                        continue
                
                achievement_entries.append({
                    "title": achievement.title,
                    "description": achievement.description,
                    "date": achievement.achieved_date.isoformat() if achievement.achieved_date else None,
                    "category": achievement.category.value.title(),
                })
            
            content["achievements"] = achievement_entries

        return content

    def _format_date_range(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        is_current: bool = False,
    ) -> str:
        """Format a date range for display."""
        start_str = self._format_date(start_date) if start_date else ""
        
        if is_current:
            end_str = "Present"
        else:
            end_str = self._format_date(end_date) if end_date else ""
        
        if start_str and end_str:
            return f"{start_str} - {end_str}"
        elif start_str:
            return start_str
        elif end_str:
            return end_str
        return ""

    def _format_date(self, date_value: Optional[str]) -> str:
        """Format a date for display."""
        if not date_value:
            return ""
        
        try:
            if isinstance(date_value, str):
                # Parse ISO format date
                parsed = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                return parsed.strftime("%b %Y")
            elif isinstance(date_value, date):
                return date_value.strftime("%b %Y")
        except (ValueError, AttributeError):
            return str(date_value)
        
        return ""
