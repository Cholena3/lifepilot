"""Add account deletion fields to users table.

Revision ID: 024
Revises: 023
Create Date: 2024-01-01 00:00:00.000000

Requirement 36.6: Account deletion with 30-day data removal
- Track when deletion was requested
- Track when deletion is scheduled to occur
- Support cancellation within grace period
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add deletion tracking columns to users table."""
    # Add deletion_requested_at column
    op.add_column(
        "users",
        sa.Column(
            "deletion_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    
    # Add deletion_scheduled_at column
    op.add_column(
        "users",
        sa.Column(
            "deletion_scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    
    # Create indexes for efficient querying of pending deletions
    op.create_index(
        "ix_users_deletion_requested_at",
        "users",
        ["deletion_requested_at"],
    )
    op.create_index(
        "ix_users_deletion_scheduled_at",
        "users",
        ["deletion_scheduled_at"],
    )


def downgrade() -> None:
    """Remove deletion tracking columns from users table."""
    op.drop_index("ix_users_deletion_scheduled_at", table_name="users")
    op.drop_index("ix_users_deletion_requested_at", table_name="users")
    op.drop_column("users", "deletion_scheduled_at")
    op.drop_column("users", "deletion_requested_at")
