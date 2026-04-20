"""Add scheduled_at column to notifications table.

Revision ID: 003
Revises: 002
Create Date: 2024-01-15

Validates: Requirements 32.5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scheduled_at column to notifications table."""
    op.add_column(
        "notifications",
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Add index for efficient querying of scheduled notifications
    op.create_index(
        "ix_notifications_scheduled_at",
        "notifications",
        ["scheduled_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove scheduled_at column from notifications table."""
    op.drop_index("ix_notifications_scheduled_at", table_name="notifications")
    op.drop_column("notifications", "scheduled_at")
