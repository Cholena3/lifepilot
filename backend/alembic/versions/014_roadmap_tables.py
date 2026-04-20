"""Create career roadmap tables.

Revision ID: 014
Revises: 013
Create Date: 2024-01-15

Validates: Requirements 26.1, 26.2, 26.3, 26.4, 26.5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create career_roadmaps table
    # Requirement 26.1: Generate roadmap from career goals
    op.create_table(
        "career_roadmaps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("target_role", sa.String(length=255), nullable=False),
        sa.Column("target_timeline_months", sa.Integer(), nullable=False, default=12),
        sa.Column("current_progress", sa.Integer(), nullable=False, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index(
        op.f("ix_career_roadmaps_user_id"),
        "career_roadmaps",
        ["user_id"],
        unique=False,
    )

    # Create roadmap_milestones table
    # Requirement 26.1: Roadmap milestones
    # Requirement 26.4: Track milestone completion
    op.create_table(
        "roadmap_milestones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("roadmap_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, default=0),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "not_started",
                "in_progress",
                "completed",
                "skipped",
                name="milestonestatus",
            ),
            nullable=False,
            default="not_started",
        ),
        sa.Column("required_skills", postgresql.ARRAY(sa.String()), nullable=True),
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
            ["roadmap_id"],
            ["career_roadmaps.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_roadmap_milestones_roadmap_id"),
        "roadmap_milestones",
        ["roadmap_id"],
        unique=False,
    )

    # Create skill_gaps table
    # Requirement 26.2: Identify skill gaps
    op.create_table(
        "skill_gaps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("roadmap_id", sa.UUID(), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("current_level", sa.String(length=50), nullable=True),
        sa.Column("required_level", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, default=1),
        sa.Column("is_filled", sa.Boolean(), nullable=False, default=False),
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
            ["roadmap_id"],
            ["career_roadmaps.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_skill_gaps_roadmap_id"),
        "skill_gaps",
        ["roadmap_id"],
        unique=False,
    )

    # Create resource_recommendations table
    # Requirement 26.3: Recommend courses and resources
    op.create_table(
        "resource_recommendations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("skill_gap_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "resource_type",
            postgresql.ENUM(
                "course",
                "book",
                "tutorial",
                "documentation",
                "video",
                "article",
                "project",
                "certification",
                "other",
                name="resourcetype",
            ),
            nullable=False,
            default="course",
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, default=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["skill_gap_id"],
            ["skill_gaps.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_resource_recommendations_skill_gap_id"),
        "resource_recommendations",
        ["skill_gap_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(
        op.f("ix_resource_recommendations_skill_gap_id"),
        table_name="resource_recommendations",
    )
    op.drop_table("resource_recommendations")

    op.drop_index(op.f("ix_skill_gaps_roadmap_id"), table_name="skill_gaps")
    op.drop_table("skill_gaps")

    op.drop_index(
        op.f("ix_roadmap_milestones_roadmap_id"), table_name="roadmap_milestones"
    )
    op.drop_table("roadmap_milestones")

    op.drop_index(op.f("ix_career_roadmaps_user_id"), table_name="career_roadmaps")
    op.drop_table("career_roadmaps")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS resourcetype")
    op.execute("DROP TYPE IF EXISTS milestonestatus")
