"""Budget models for the Money Manager module.

Includes Budget and BudgetHistory models for tracking user budgets.

Validates: Requirements 11.1, 11.5, 11.6
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.expense import ExpenseCategory
    from app.models.user import User


class BudgetPeriod(str, Enum):
    """Budget period types.
    
    Validates: Requirements 11.1
    """
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Budget(Base, UUIDMixin, TimestampMixin):
    """Budget model for tracking user budgets per category.
    
    Validates: Requirements 11.1, 11.5
    
    Attributes:
        id: Unique identifier for the budget
        user_id: Foreign key to the user who owns the budget
        category_id: Foreign key to the expense category
        amount: Budget limit amount
        period: Budget period (weekly/monthly)
        start_date: Start date of the current budget period
        end_date: End date of the current budget period
        is_active: Whether the budget is currently active
        threshold_50_notified: Whether 50% threshold notification was sent
        threshold_80_notified: Whether 80% threshold notification was sent
        threshold_100_notified: Whether 100% threshold notification was sent
        created_at: Timestamp when budget was created
        updated_at: Timestamp when budget was last updated
    """
    
    __tablename__ = "budgets"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("expense_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    period: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Threshold notification tracking
    threshold_50_notified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    threshold_80_notified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    threshold_100_notified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    category: Mapped["ExpenseCategory"] = relationship(
        "ExpenseCategory",
        lazy="joined",
    )


class BudgetHistory(Base, UUIDMixin, TimestampMixin):
    """Budget history model for archived budget periods.
    
    Validates: Requirements 11.6
    
    Attributes:
        id: Unique identifier for the history record
        user_id: Foreign key to the user who owns the budget
        category_id: Foreign key to the expense category
        budget_amount: Original budget limit amount
        spent_amount: Total amount spent during the period
        period: Budget period (weekly/monthly)
        start_date: Start date of the budget period
        end_date: End date of the budget period
        archived_at: Timestamp when the budget was archived
    """
    
    __tablename__ = "budget_history"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    category_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    budget_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    spent_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    
    period: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
