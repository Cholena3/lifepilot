"""Weekly Summary tables for analytics.

Revision ID: 022
Revises: 021
Create Date: 2024-01-01 00:00:00.000000

Requirement 34: Weekly Summary
- Generate summary of activities across all modules
- Include expenses total, documents added, health records logged, and career progress
- Compare metrics with previous week
- Store past summaries for viewing
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create weekly_summaries table."""
    op.create_table(
        "weekly_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("metrics", postgresql.JSON(), nullable=False, default={}),
        sa.Column("comparisons", postgresql.JSON(), nullable=False, default={}),
        sa.Column(
            "generated_at",
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
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_summary_user_week"),
    )
    
    # Create indexes for efficient querying
    op.create_index(
        "ix_weekly_summaries_user_id",
        "weekly_summaries",
        ["user_id"],
    )
    op.create_index(
        "ix_weekly_summaries_week_start",
        "weekly_summaries",
        ["week_start"],
    )
    op.create_index(
        "ix_weekly_summaries_user_week",
        "weekly_summaries",
        ["user_id", "week_start"],
    )


def downgrade() -> None:
    """Drop weekly_summaries table."""
    op.drop_index("ix_weekly_summaries_user_week", table_name="weekly_summaries")
    op.drop_index("ix_weekly_summaries_week_start", table_name="weekly_summaries")
    op.drop_index("ix_weekly_summaries_user_id", table_name="weekly_summaries")
    op.drop_table("weekly_summaries")
