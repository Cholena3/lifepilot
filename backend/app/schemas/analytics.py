"""Pydantic schemas for spending analytics module.

Provides schemas for spending analytics including category breakdown,
spending trends, period comparison, and unusual spending detection.

Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CategorySpending(BaseModel):
    """Spending breakdown for a single category.
    
    Validates: Requirements 12.1
    """
    
    category_id: UUID = Field(..., description="Category UUID")
    category_name: str = Field(..., description="Category name")
    category_color: Optional[str] = Field(None, description="Category color hex code")
    category_icon: Optional[str] = Field(None, description="Category icon identifier")
    total_amount: Decimal = Field(..., description="Total spending in this category")
    expense_count: int = Field(..., description="Number of expenses in this category")
    percentage: Decimal = Field(..., description="Percentage of total spending")


class CategoryBreakdownResponse(BaseModel):
    """Response schema for spending breakdown by category.
    
    Validates: Requirements 12.1, 12.4
    """
    
    start_date: date = Field(..., description="Start date of the analysis period")
    end_date: date = Field(..., description="End date of the analysis period")
    total_spending: Decimal = Field(..., description="Total spending in the period")
    total_expenses: int = Field(..., description="Total number of expenses")
    categories: List[CategorySpending] = Field(
        default_factory=list,
        description="Spending breakdown by category"
    )


class DailySpending(BaseModel):
    """Spending data for a single day.
    
    Validates: Requirements 12.2
    """
    
    spending_date: date = Field(..., description="Date")
    total_amount: Decimal = Field(..., description="Total spending on this date")
    expense_count: int = Field(..., description="Number of expenses on this date")


class SpendingTrendsResponse(BaseModel):
    """Response schema for spending trends over time.
    
    Validates: Requirements 12.2, 12.4
    """
    
    start_date: date = Field(..., description="Start date of the analysis period")
    end_date: date = Field(..., description="End date of the analysis period")
    total_spending: Decimal = Field(..., description="Total spending in the period")
    average_daily_spending: Decimal = Field(..., description="Average daily spending")
    daily_spending: List[DailySpending] = Field(
        default_factory=list,
        description="Daily spending data for line chart"
    )


class PeriodSpending(BaseModel):
    """Spending summary for a period.
    
    Validates: Requirements 12.3
    """
    
    start_date: date = Field(..., description="Period start date")
    end_date: date = Field(..., description="Period end date")
    total_spending: Decimal = Field(..., description="Total spending in the period")
    expense_count: int = Field(..., description="Number of expenses in the period")
    average_expense: Decimal = Field(..., description="Average expense amount")


class PeriodComparisonResponse(BaseModel):
    """Response schema for comparing current vs previous period spending.
    
    Validates: Requirements 12.3, 12.4
    """
    
    current_period: PeriodSpending = Field(..., description="Current period spending data")
    previous_period: PeriodSpending = Field(..., description="Previous period spending data")
    spending_change: Decimal = Field(
        ..., 
        description="Absolute change in spending (current - previous)"
    )
    spending_change_percentage: Optional[Decimal] = Field(
        None,
        description="Percentage change in spending (None if previous period had no spending)"
    )
    expense_count_change: int = Field(
        ...,
        description="Change in number of expenses"
    )


class UnusualSpendingPattern(BaseModel):
    """An unusual spending pattern detected.
    
    Validates: Requirements 12.5
    """
    
    pattern_type: str = Field(
        ..., 
        description="Type of unusual pattern: 'high_single_expense', 'category_spike', 'daily_spike', 'new_category'"
    )
    description: str = Field(..., description="Human-readable description of the pattern")
    severity: str = Field(
        ..., 
        description="Severity level: 'info', 'warning', 'alert'"
    )
    category_id: Optional[UUID] = Field(None, description="Related category ID if applicable")
    category_name: Optional[str] = Field(None, description="Related category name if applicable")
    expense_id: Optional[UUID] = Field(None, description="Related expense ID if applicable")
    amount: Optional[Decimal] = Field(None, description="Related amount if applicable")
    pattern_date: Optional[date] = Field(None, description="Related date if applicable")
    threshold: Optional[Decimal] = Field(None, description="Threshold that was exceeded")


class UnusualSpendingResponse(BaseModel):
    """Response schema for unusual spending patterns.
    
    Validates: Requirements 12.5
    """
    
    start_date: date = Field(..., description="Start date of the analysis period")
    end_date: date = Field(..., description="End date of the analysis period")
    patterns: List[UnusualSpendingPattern] = Field(
        default_factory=list,
        description="List of detected unusual spending patterns"
    )
    has_unusual_patterns: bool = Field(
        ...,
        description="Whether any unusual patterns were detected"
    )


class SpendingAnalyticsResponse(BaseModel):
    """Combined response schema for all spending analytics.
    
    Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
    """
    
    start_date: date = Field(..., description="Start date of the analysis period")
    end_date: date = Field(..., description="End date of the analysis period")
    category_breakdown: CategoryBreakdownResponse = Field(
        ...,
        description="Spending breakdown by category"
    )
    spending_trends: SpendingTrendsResponse = Field(
        ...,
        description="Spending trends over time"
    )
    period_comparison: PeriodComparisonResponse = Field(
        ...,
        description="Comparison with previous period"
    )
    unusual_patterns: UnusualSpendingResponse = Field(
        ...,
        description="Detected unusual spending patterns"
    )
