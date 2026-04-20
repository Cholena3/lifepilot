"""Pydantic schemas for budget module.

Includes schemas for budget CRUD operations and progress tracking.

Validates: Requirements 11.1, 11.5, 11.6
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class BudgetPeriod(str, Enum):
    """Budget period types.
    
    Validates: Requirements 11.1
    """
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ============================================================================
# Budget Schemas
# ============================================================================

class BudgetCreate(BaseModel):
    """Schema for creating a new budget.
    
    Validates: Requirements 11.1
    """
    
    category_id: UUID = Field(..., description="ID of the expense category")
    amount: Decimal = Field(..., gt=0, description="Budget limit amount (must be positive)")
    period: BudgetPeriod = Field(..., description="Budget period (weekly/monthly)")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and round to 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)


class BudgetUpdate(BaseModel):
    """Schema for updating a budget.
    
    Validates: Requirements 11.1
    """
    
    amount: Optional[Decimal] = Field(None, gt=0, description="Budget limit amount")
    period: Optional[BudgetPeriod] = Field(None, description="Budget period (weekly/monthly)")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate amount is positive and round to 2 decimal places."""
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be positive")
            return round(v, 2)
        return v


class BudgetCategoryResponse(BaseModel):
    """Response schema for budget category info."""
    
    id: UUID
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    
    model_config = {"from_attributes": True}


class BudgetResponse(BaseModel):
    """Response schema for a budget.
    
    Validates: Requirements 11.1
    """
    
    id: UUID
    user_id: UUID
    category_id: UUID
    amount: Decimal
    period: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BudgetWithCategoryResponse(BudgetResponse):
    """Response schema for a budget with category details."""
    
    category: BudgetCategoryResponse


class BudgetProgressResponse(BaseModel):
    """Response schema for budget progress with visual indicators.
    
    Validates: Requirements 11.5
    """
    
    id: UUID
    category_id: UUID
    category_name: str
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    budget_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: float
    period: str
    start_date: date
    end_date: date
    status: str = Field(
        ...,
        description="Budget status: 'on_track', 'warning', 'critical', 'exceeded'"
    )
    
    @classmethod
    def from_budget_and_spent(
        cls,
        budget,
        spent_amount: Decimal,
    ) -> "BudgetProgressResponse":
        """Create progress response from budget and spent amount."""
        budget_amount = Decimal(str(budget.amount))
        spent = Decimal(str(spent_amount))
        remaining = budget_amount - spent
        percentage = float(spent / budget_amount * 100) if budget_amount > 0 else 0.0
        
        # Determine status based on percentage
        if percentage >= 100:
            status = "exceeded"
        elif percentage >= 80:
            status = "critical"
        elif percentage >= 50:
            status = "warning"
        else:
            status = "on_track"
        
        return cls(
            id=budget.id,
            category_id=budget.category_id,
            category_name=budget.category.name,
            category_icon=budget.category.icon,
            category_color=budget.category.color,
            budget_amount=budget_amount,
            spent_amount=spent,
            remaining_amount=remaining,
            percentage_used=round(percentage, 2),
            period=budget.period,
            start_date=budget.start_date,
            end_date=budget.end_date,
            status=status,
        )


# ============================================================================
# Budget History Schemas
# ============================================================================

class BudgetHistoryResponse(BaseModel):
    """Response schema for archived budget history.
    
    Validates: Requirements 11.6
    """
    
    id: UUID
    user_id: UUID
    category_id: Optional[UUID] = None
    category_name: str
    budget_amount: Decimal
    spent_amount: Decimal
    period: str
    start_date: date
    end_date: date
    archived_at: datetime
    percentage_used: float = Field(default=0.0)
    
    model_config = {"from_attributes": True}
    
    @model_validator(mode="after")
    def calculate_percentage(self) -> "BudgetHistoryResponse":
        """Calculate percentage used from budget and spent amounts."""
        if self.budget_amount > 0:
            self.percentage_used = round(
                float(self.spent_amount / self.budget_amount * 100), 2
            )
        return self


# ============================================================================
# Budget Summary Schemas
# ============================================================================

class BudgetSummaryResponse(BaseModel):
    """Response schema for overall budget summary."""
    
    total_budget: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    overall_percentage: float
    budgets: List[BudgetProgressResponse]
    period_start: date
    period_end: date
