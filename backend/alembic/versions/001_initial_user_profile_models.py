"""Initial user and profile models migration.

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

Creates the following tables:
- users: User authentication and account data
- profiles: Basic user profile information
- student_profiles: Academic information for students
- career_preferences: Job and career preferences
- documents: Document vault storage
- document_versions: Document version history

Requirements: 37.4 (Database connection pooling and efficient resource usage)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables for users and profiles."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("oauth_provider", sa.String(length=50), nullable=True),
        sa.Column("oauth_id", sa.String(length=255), nullable=True),
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
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Create profiles table
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("completion_percentage", sa.Integer(), nullable=False, default=0),
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
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="check_completion_percentage_range",
        ),
    )
    op.create_index(op.f("ix_profiles_user_id"), "profiles", ["user_id"], unique=True)

    # Create student_profiles table
    op.create_table(
        "student_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution", sa.String(length=255), nullable=True),
        sa.Column("degree", sa.String(length=100), nullable=True),
        sa.Column("branch", sa.String(length=100), nullable=True),
        sa.Column("cgpa", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("backlogs", sa.Integer(), nullable=True, default=0),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
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
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint(
            "cgpa IS NULL OR (cgpa >= 0.0 AND cgpa <= 10.0)",
            name="check_cgpa_range",
        ),
        sa.CheckConstraint(
            "backlogs IS NULL OR backlogs >= 0",
            name="check_backlogs_non_negative",
        ),
    )
    op.create_index(
        op.f("ix_student_profiles_user_id"),
        "student_profiles",
        ["user_id"],
        unique=True,
    )

    # Create career_preferences table
    op.create_table(
        "career_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preferred_roles", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "preferred_locations", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("min_salary", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("max_salary", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=True),
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
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint(
            "min_salary IS NULL OR min_salary >= 0",
            name="check_min_salary_non_negative",
        ),
        sa.CheckConstraint(
            "max_salary IS NULL OR max_salary >= 0",
            name="check_max_salary_non_negative",
        ),
        sa.CheckConstraint(
            "min_salary IS NULL OR max_salary IS NULL OR min_salary <= max_salary",
            name="check_salary_range_valid",
        ),
    )
    op.create_index(
        op.f("ix_career_preferences_user_id"),
        "career_preferences",
        ["user_id"],
        unique=True,
    )

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("encryption_key", sa.String(length=255), nullable=False),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_expired", sa.Boolean(), nullable=False, default=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False, default=1),
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
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"])
    op.create_index(op.f("ix_documents_category"), "documents", ["category"])

    # Create document_versions table
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_versions_document_id"),
        "document_versions",
        ["document_id"],
    )


def downgrade() -> None:
    """Drop all tables created in this migration."""
    # Drop document_versions first (depends on documents)
    op.drop_index(op.f("ix_document_versions_document_id"), table_name="document_versions")
    op.drop_table("document_versions")

    # Drop documents (depends on users)
    op.drop_index(op.f("ix_documents_category"), table_name="documents")
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_career_preferences_user_id"), table_name="career_preferences")
    op.drop_table("career_preferences")
    op.drop_index(op.f("ix_student_profiles_user_id"), table_name="student_profiles")
    op.drop_table("student_profiles")
    op.drop_index(op.f("ix_profiles_user_id"), table_name="profiles")
    op.drop_table("profiles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
