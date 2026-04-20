"""Create resume tables.

Revision ID: 018
Revises: 017
Create Date: 2024-01-19

Validates: Requirements 30.1, 30.2, 30.4, 30.5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create resumes table
    # Requirement 30.1: Populate resume from profile, skills, achievements
    # Requirement 30.2: Support multiple resume templates
    # Requirement 30.4: Export resumes in PDF format (pdf_url)
    # Requirement 30.5: Allow saving multiple resume versions
    op.create_table(
        "resumes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "template",
            postgresql.ENUM(
                "classic",
                "modern",
                "minimal",
                "professional",
                "creative",
                name="resumetemplate",
            ),
            nullable=False,
            server_default="classic",
        ),
        sa.Column(
            "content",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create index for efficient querying
    op.create_index(
        op.f("ix_resumes_user_id"),
        "resumes",
        ["user_id"],
        unique=False,
    )

    # Create resume_versions table
    # Requirement 30.5: Allow saving multiple resume versions
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("resume_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "content",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create index for efficient querying
    op.create_index(
        op.f("ix_resume_versions_resume_id"),
        "resume_versions",
        ["resume_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_resume_versions_resume_id"), table_name="resume_versions")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    
    # Drop tables
    op.drop_table("resume_versions")
    op.drop_table("resumes")
    
    # Drop enum
    op.execute("DROP TYPE IF EXISTS resumetemplate")
