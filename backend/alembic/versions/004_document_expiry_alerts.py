"""Document expiry alerts tables.

Revision ID: 004
Revises: 003
Create Date: 2024-01-15

Validates: Requirements 8.1, 8.2, 8.3, 8.4
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create document expiry alert tables."""
    # Create document_expiry_alert_preferences table
    op.create_table(
        "document_expiry_alert_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("alerts_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("alert_30_days", sa.Boolean(), nullable=False, default=True),
        sa.Column("alert_14_days", sa.Boolean(), nullable=False, default=True),
        sa.Column("alert_7_days", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "category", name="uq_user_category_expiry_prefs"),
    )
    op.create_index(
        "ix_document_expiry_alert_preferences_user_id",
        "document_expiry_alert_preferences",
        ["user_id"],
    )
    
    # Create document_expiry_alerts table
    op.create_table(
        "document_expiry_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "alert_type",
            sa.Enum("days_30", "days_14", "days_7", name="expiryalerttype"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("document_id", "alert_type", name="uq_document_alert_type"),
    )
    op.create_index(
        "ix_document_expiry_alerts_document_id",
        "document_expiry_alerts",
        ["document_id"],
    )
    op.create_index(
        "ix_document_expiry_alerts_user_id",
        "document_expiry_alerts",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop document expiry alert tables."""
    op.drop_index("ix_document_expiry_alerts_user_id", table_name="document_expiry_alerts")
    op.drop_index("ix_document_expiry_alerts_document_id", table_name="document_expiry_alerts")
    op.drop_table("document_expiry_alerts")
    
    op.drop_index(
        "ix_document_expiry_alert_preferences_user_id",
        table_name="document_expiry_alert_preferences",
    )
    op.drop_table("document_expiry_alert_preferences")
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS expiryalerttype")
