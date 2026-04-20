"""Badge tables for gamification achievements.

Revision ID: 021
Revises: 020
Create Date: 2024-01-01 00:00:00.000000

Requirement 33.5: Award badges for achievements and milestones
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create badges table."""
    op.create_table(
        "badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("badge_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "earned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    
    # Create indexes for efficient querying
    op.create_index(
        "ix_badges_user_id",
        "badges",
        ["user_id"],
    )
    op.create_index(
        "ix_badges_badge_type",
        "badges",
        ["badge_type"],
    )
    op.create_index(
        "ix_badges_user_badge_type",
        "badges",
        ["user_id", "badge_type"],
        unique=True,
    )
    op.create_index(
        "ix_badges_earned_at",
        "badges",
        ["earned_at"],
    )


def downgrade() -> None:
    """Drop badges table."""
    op.drop_index("ix_badges_earned_at", table_name="badges")
    op.drop_index("ix_badges_user_badge_type", table_name="badges")
    op.drop_index("ix_badges_badge_type", table_name="badges")
    op.drop_index("ix_badges_user_id", table_name="badges")
    op.drop_table("badges")
