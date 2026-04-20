"""Life Score tables for gamification.

Revision ID: 020
Revises: 019
Create Date: 2024-01-01 00:00:00.000000

Requirement 33: Life Score Gamification
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create life_scores table."""
    op.create_table(
        "life_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False, default=0),
        sa.Column("module_scores", postgresql.JSON(), nullable=False, default={}),
        sa.Column("activity_count", sa.Integer(), nullable=False, default=0),
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
        sa.UniqueConstraint("user_id", "score_date", name="uq_life_score_user_date"),
    )
    
    # Create indexes for efficient querying
    op.create_index(
        "ix_life_scores_user_id",
        "life_scores",
        ["user_id"],
    )
    op.create_index(
        "ix_life_scores_score_date",
        "life_scores",
        ["score_date"],
    )
    op.create_index(
        "ix_life_scores_user_date",
        "life_scores",
        ["user_id", "score_date"],
    )


def downgrade() -> None:
    """Drop life_scores table."""
    op.drop_index("ix_life_scores_user_date", table_name="life_scores")
    op.drop_index("ix_life_scores_score_date", table_name="life_scores")
    op.drop_index("ix_life_scores_user_id", table_name="life_scores")
    op.drop_table("life_scores")
