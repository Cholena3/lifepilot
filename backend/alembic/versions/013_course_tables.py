"""Create course and learning session tables.

Revision ID: 013
Revises: 012
Create Date: 2024-01-15

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create course and learning_sessions tables."""
    # Create courses table
    # Requirement 25.1: Store course name, platform, URL, and total duration
    # Requirement 25.2: Track completion percentage
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("total_hours", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("completed_hours", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("completion_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
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
        op.f("ix_courses_user_id"),
        "courses",
        ["user_id"],
        unique=False,
    )

    # Create learning_sessions table
    # Requirement 25.2: Log progress updates
    # Requirement 25.3: Track total hours invested
    op.create_table(
        "learning_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_learning_sessions_course_id"),
        "learning_sessions",
        ["course_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop course and learning_sessions tables."""
    op.drop_index(op.f("ix_learning_sessions_course_id"), table_name="learning_sessions")
    op.drop_table("learning_sessions")
    op.drop_index(op.f("ix_courses_user_id"), table_name="courses")
    op.drop_table("courses")
