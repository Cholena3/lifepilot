"""Create achievement tables.

Revision ID: 017
Revises: 016
Create Date: 2024-01-18

Validates: Requirements 29.1, 29.2, 29.3, 29.5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create achievements table
    # Requirement 29.1: Store title, description, date, and category
    # Requirement 29.3: Allow attaching supporting documents (via document_ids array)
    # Requirement 29.5: Display achievements on a timeline view (achieved_date indexed)
    op.create_table(
        "achievements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("achieved_date", sa.Date(), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "academic",
                "professional",
                "certification",
                "award",
                "project",
                "publication",
                "other",
                name="achievementcategory",
            ),
            nullable=False,
            default="other",
        ),
        sa.Column(
            "document_ids",
            postgresql.ARRAY(sa.UUID()),
            nullable=True,
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for efficient querying
    op.create_index(
        op.f("ix_achievements_user_id"),
        "achievements",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_achievements_achieved_date"),
        "achievements",
        ["achieved_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_achievements_category"),
        "achievements",
        ["category"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_achievements_category"), table_name="achievements")
    op.drop_index(op.f("ix_achievements_achieved_date"), table_name="achievements")
    op.drop_index(op.f("ix_achievements_user_id"), table_name="achievements")
    
    # Drop table
    op.drop_table("achievements")
    
    # Drop enum
    op.execute("DROP TYPE IF EXISTS achievementcategory")
