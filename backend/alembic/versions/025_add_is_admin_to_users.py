"""Add is_admin field to users table.

Revision ID: 025
Revises: 024
Create Date: 2024-01-01 00:00:00.000000

Requirements 38.1, 38.2, 38.3, 38.4: Admin Dashboard
- Add is_admin boolean field to users table
- Enables admin-only access to analytics endpoints
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_admin column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Remove is_admin column from users table."""
    op.drop_column("users", "is_admin")
