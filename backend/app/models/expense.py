"""Expense models for the Money Manager module.

Includes Expense and ExpenseCategory models for tracking user expenses.

Validates: Requirements 10.1, 10.4, 10.5, 10.6
"""

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ExpenseCategory(Base, UUIDMixin, TimestampMixin):
    """Expense category model for customizable expense categories.
    
    Validates: Requirements 10.4
    
    Attributes:
        id: Unique identifier for the category
        user_id: Foreign key to the user who owns the category (null for default categories)
        name: Category name
        icon: Icon identifier for the category
        color: Color hex code for the category
        is_default: Whether this is a system default category
        created_at: Timestamp when category was created
        updated_at: Timestamp when category was last updated
    """
    
    __tablename__ = "expense_categories"
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    icon: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    color: Mapped[Optional[str]] = mapped_column(
        String(7),  # Hex color code like #FF5733
        nullable=True,
    )
    
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class Expense(Base, UUIDMixin, TimestampMixin):
    """Expense model for tracking user expenses.
    
    Validates: Requirements 10.1, 10.5, 10.6
    
    Attributes:
        id: Unique identifier for the expense
        user_id: Foreign key to the user who owns the expense
        category_id: Foreign key to the expense category
        amount: Expense amount (decimal with 2 decimal places)
        description: Description of the expense
        expense_date: Date when the expense occurred
        receipt_url: URL to the receipt image in storage
        ocr_data: JSON field for OCR extracted data from receipt
        created_at: Timestamp when expense was created
        updated_at: Timestamp when expense was last updated
    """
    
    __tablename__ = "expenses"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    expense_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    
    receipt_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    ocr_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    # Relationships
    category: Mapped["ExpenseCategory"] = relationship(
        "ExpenseCategory",
        back_populates="expenses",
    )
