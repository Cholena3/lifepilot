"""Spending analytics service for the Money Manager module.

Provides business logic for spending analytics including category breakdown,
spending trends, period comparison, and unusual spending detection.

Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expense import Expense, ExpenseCategory
from app.schemas.analytics import (
    CategoryBreakdownResponse,
    CategorySpending,
    DailySpending,
    PeriodComparisonResponse,
    PeriodSpending,
    SpendingAnalyticsResponse,
    SpendingTrendsResponse,
    UnusualSpendingPattern,
    UnusualSpendingResponse,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for spending analytics.
    
    Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
    """
    
    # Thresholds for unusual spending detection
    HIGH_EXPENSE_MULTIPLIER = 3.0  # Expense > 3x average is unusual
    CATEGORY_SPIKE_MULTIPLIER = 2.0  # Category spending > 2x historical average
    DAILY_SPIKE_MULTIPLIER = 2.5  # Daily spending > 2.5x average
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the analytics service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def get_category_breakdown(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> CategoryBreakdownResponse:
        """Get spending breakdown by category for a date range.
        
        Validates: Requirements 12.1, 12.4
        
        Args:
            user_id: User's UUID
            start_date: Start date of the analysis period
            end_date: End date of the analysis period
            
        Returns:
            Category breakdown response with spending per category
        """
        # Query expenses grouped by category
        stmt = (
            select(
                Expense.category_id,
                ExpenseCategory.name,
                ExpenseCategory.color,
                ExpenseCategory.icon,
                func.sum(Expense.amount).label("total_amount"),
                func.count(Expense.id).label("expense_count"),
            )
            .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date,
                )
            )
            .group_by(
                Expense.category_id,
                ExpenseCategory.name,
                ExpenseCategory.color,
                ExpenseCategory.icon,
            )
            .order_by(func.sum(Expense.amount).desc())
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        # Calculate totals
        total_spending = sum(Decimal(str(row.total_amount)) for row in rows)
        total_expenses = sum(row.expense_count for row in rows)
        
        # Build category breakdown
        categories = []
        for row in rows:
            amount = Decimal(str(row.total_amount))
            percentage = (amount / total_spending * 100) if total_spending > 0 else Decimal("0")
            
            categories.append(CategorySpending(
                category_id=row.category_id,
                category_name=row.name,
                category_color=row.color,
                category_icon=row.icon,
                total_amount=amount,
                expense_count=row.expense_count,
                percentage=round(percentage, 2),
            ))
        
        return CategoryBreakdownResponse(
            start_date=start_date,
            end_date=end_date,
            total_spending=total_spending,
            total_expenses=total_expenses,
            categories=categories,
        )
    
    async def get_spending_trends(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> SpendingTrendsResponse:
        """Get spending trends over time for a date range.
        
        Validates: Requirements 12.2, 12.4
        
        Args:
            user_id: User's UUID
            start_date: Start date of the analysis period
            end_date: End date of the analysis period
            
        Returns:
            Spending trends response with daily spending data
        """
        # Query expenses grouped by date
        stmt = (
            select(
                Expense.expense_date,
                func.sum(Expense.amount).label("total_amount"),
                func.count(Expense.id).label("expense_count"),
            )
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date,
                )
            )
            .group_by(Expense.expense_date)
            .order_by(Expense.expense_date)
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        # Create a map of date to spending
        spending_by_date: Dict[date, Tuple[Decimal, int]] = {
            row.expense_date: (Decimal(str(row.total_amount)), row.expense_count)
            for row in rows
        }
        
        # Fill in all dates in the range (including days with no spending)
        daily_spending = []
        current_date = start_date
        total_spending = Decimal("0")
        
        while current_date <= end_date:
            if current_date in spending_by_date:
                amount, count = spending_by_date[current_date]
                total_spending += amount
            else:
                amount, count = Decimal("0"), 0
            
            daily_spending.append(DailySpending(
                spending_date=current_date,
                total_amount=amount,
                expense_count=count,
            ))
            current_date += timedelta(days=1)
        
        # Calculate average daily spending
        num_days = (end_date - start_date).days + 1
        average_daily = total_spending / num_days if num_days > 0 else Decimal("0")
        
        return SpendingTrendsResponse(
            start_date=start_date,
            end_date=end_date,
            total_spending=total_spending,
            average_daily_spending=round(average_daily, 2),
            daily_spending=daily_spending,
        )
    
    async def get_period_comparison(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> PeriodComparisonResponse:
        """Compare current period spending with previous period.
        
        Validates: Requirements 12.3, 12.4
        
        The previous period is calculated as the same duration immediately
        before the current period.
        
        Args:
            user_id: User's UUID
            start_date: Start date of the current period
            end_date: End date of the current period
            
        Returns:
            Period comparison response
        """
        # Calculate period duration
        period_days = (end_date - start_date).days + 1
        
        # Calculate previous period dates
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_days - 1)
        
        # Get current period stats
        current_stats = await self._get_period_stats(user_id, start_date, end_date)
        
        # Get previous period stats
        previous_stats = await self._get_period_stats(user_id, prev_start_date, prev_end_date)
        
        # Calculate changes
        spending_change = current_stats.total_spending - previous_stats.total_spending
        expense_count_change = current_stats.expense_count - previous_stats.expense_count
        
        # Calculate percentage change (None if previous period had no spending)
        if previous_stats.total_spending > 0:
            spending_change_percentage = round(
                (spending_change / previous_stats.total_spending) * 100, 2
            )
        else:
            spending_change_percentage = None
        
        return PeriodComparisonResponse(
            current_period=current_stats,
            previous_period=previous_stats,
            spending_change=spending_change,
            spending_change_percentage=spending_change_percentage,
            expense_count_change=expense_count_change,
        )
    
    async def _get_period_stats(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> PeriodSpending:
        """Get spending statistics for a period.
        
        Args:
            user_id: User's UUID
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            Period spending statistics
        """
        stmt = (
            select(
                func.coalesce(func.sum(Expense.amount), 0).label("total_spending"),
                func.count(Expense.id).label("expense_count"),
            )
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date,
                )
            )
        )
        
        result = await self.db.execute(stmt)
        row = result.one()
        
        total_spending = Decimal(str(row.total_spending))
        expense_count = row.expense_count
        average_expense = (
            round(total_spending / expense_count, 2) 
            if expense_count > 0 
            else Decimal("0")
        )
        
        return PeriodSpending(
            start_date=start_date,
            end_date=end_date,
            total_spending=total_spending,
            expense_count=expense_count,
            average_expense=average_expense,
        )

    async def detect_unusual_spending(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> UnusualSpendingResponse:
        """Detect unusual spending patterns in the given period.
        
        Validates: Requirements 12.5
        
        Detects the following patterns:
        - High single expenses (> 3x average expense)
        - Category spending spikes (> 2x historical average for category)
        - Daily spending spikes (> 2.5x average daily spending)
        - New categories (first expense in a category)
        
        Args:
            user_id: User's UUID
            start_date: Start date of the analysis period
            end_date: End date of the analysis period
            
        Returns:
            Unusual spending response with detected patterns
        """
        patterns: List[UnusualSpendingPattern] = []
        
        # Get expenses in the period with category info
        stmt = (
            select(Expense)
            .options(selectinload(Expense.category))
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date,
                )
            )
            .order_by(Expense.expense_date)
        )
        
        result = await self.db.execute(stmt)
        expenses = list(result.scalars().all())
        
        if not expenses:
            return UnusualSpendingResponse(
                start_date=start_date,
                end_date=end_date,
                patterns=[],
                has_unusual_patterns=False,
            )
        
        # Calculate average expense amount
        amounts = [Decimal(str(e.amount)) for e in expenses]
        avg_expense = sum(amounts) / len(amounts) if amounts else Decimal("0")
        
        # Detect high single expenses
        high_expense_threshold = avg_expense * Decimal(str(self.HIGH_EXPENSE_MULTIPLIER))
        for expense in expenses:
            amount = Decimal(str(expense.amount))
            if amount > high_expense_threshold and avg_expense > 0:
                patterns.append(UnusualSpendingPattern(
                    pattern_type="high_single_expense",
                    description=f"Expense of {amount:.2f} is {(amount / avg_expense):.1f}x higher than your average expense",
                    severity="warning",
                    category_id=expense.category_id,
                    category_name=expense.category.name if expense.category else None,
                    expense_id=expense.id,
                    amount=amount,
                    pattern_date=expense.expense_date,
                    threshold=high_expense_threshold,
                ))
        
        # Detect category spending spikes (compare to historical average)
        patterns.extend(await self._detect_category_spikes(
            user_id, start_date, end_date, expenses
        ))
        
        # Detect daily spending spikes
        patterns.extend(self._detect_daily_spikes(expenses, start_date, end_date))
        
        # Detect new categories
        patterns.extend(await self._detect_new_categories(
            user_id, start_date, end_date, expenses
        ))
        
        # Sort patterns by severity (alert > warning > info)
        severity_order = {"alert": 0, "warning": 1, "info": 2}
        patterns.sort(key=lambda p: severity_order.get(p.severity, 3))
        
        return UnusualSpendingResponse(
            start_date=start_date,
            end_date=end_date,
            patterns=patterns,
            has_unusual_patterns=len(patterns) > 0,
        )
    
    async def _detect_category_spikes(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        current_expenses: List[Expense],
    ) -> List[UnusualSpendingPattern]:
        """Detect category spending spikes compared to historical average.
        
        Args:
            user_id: User's UUID
            start_date: Current period start date
            end_date: Current period end date
            current_expenses: Expenses in the current period
            
        Returns:
            List of detected category spike patterns
        """
        patterns = []
        
        # Calculate current period duration
        period_days = (end_date - start_date).days + 1
        
        # Get historical data (90 days before the current period)
        historical_end = start_date - timedelta(days=1)
        historical_start = historical_end - timedelta(days=89)
        
        # Get historical spending by category
        stmt = (
            select(
                Expense.category_id,
                ExpenseCategory.name,
                func.sum(Expense.amount).label("total_amount"),
            )
            .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.expense_date >= historical_start,
                    Expense.expense_date <= historical_end,
                )
            )
            .group_by(Expense.category_id, ExpenseCategory.name)
        )
        
        result = await self.db.execute(stmt)
        historical_rows = result.all()
        
        # Calculate historical daily average per category
        historical_days = (historical_end - historical_start).days + 1
        historical_avg_by_category: Dict[UUID, Tuple[Decimal, str]] = {}
        
        for row in historical_rows:
            daily_avg = Decimal(str(row.total_amount)) / historical_days
            historical_avg_by_category[row.category_id] = (daily_avg, row.name)
        
        # Calculate current period spending by category
        current_by_category: Dict[UUID, Tuple[Decimal, str]] = defaultdict(
            lambda: (Decimal("0"), "")
        )
        for expense in current_expenses:
            cat_id = expense.category_id
            current_amount, _ = current_by_category[cat_id]
            current_by_category[cat_id] = (
                current_amount + Decimal(str(expense.amount)),
                expense.category.name if expense.category else "",
            )
        
        # Compare current vs historical
        for cat_id, (current_total, cat_name) in current_by_category.items():
            if cat_id in historical_avg_by_category:
                hist_daily_avg, _ = historical_avg_by_category[cat_id]
                expected_spending = hist_daily_avg * period_days
                
                if expected_spending > 0:
                    ratio = current_total / expected_spending
                    if ratio > Decimal(str(self.CATEGORY_SPIKE_MULTIPLIER)):
                        patterns.append(UnusualSpendingPattern(
                            pattern_type="category_spike",
                            description=f"Spending in '{cat_name}' is {ratio:.1f}x higher than your historical average",
                            severity="warning" if ratio < 3 else "alert",
                            category_id=cat_id,
                            category_name=cat_name,
                            amount=current_total,
                            threshold=expected_spending,
                        ))
        
        return patterns
    
    def _detect_daily_spikes(
        self,
        expenses: List[Expense],
        start_date: date,
        end_date: date,
    ) -> List[UnusualSpendingPattern]:
        """Detect days with unusually high spending.
        
        Args:
            expenses: Expenses in the period
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            List of detected daily spike patterns
        """
        patterns = []
        
        # Group expenses by date
        spending_by_date: Dict[date, Decimal] = defaultdict(Decimal)
        for expense in expenses:
            spending_by_date[expense.expense_date] += Decimal(str(expense.amount))
        
        if not spending_by_date:
            return patterns
        
        # Calculate average daily spending (only for days with expenses)
        daily_amounts = list(spending_by_date.values())
        if len(daily_amounts) < 3:
            # Not enough data points for meaningful analysis
            return patterns
        
        avg_daily = sum(daily_amounts) / len(daily_amounts)
        threshold = avg_daily * Decimal(str(self.DAILY_SPIKE_MULTIPLIER))
        
        # Find spike days
        for expense_date, amount in spending_by_date.items():
            if amount > threshold and avg_daily > 0:
                patterns.append(UnusualSpendingPattern(
                    pattern_type="daily_spike",
                    description=f"Spending on {expense_date.strftime('%b %d')} was {(amount / avg_daily):.1f}x higher than your average daily spending",
                    severity="info",
                    amount=amount,
                    pattern_date=expense_date,
                    threshold=threshold,
                ))
        
        return patterns
    
    async def _detect_new_categories(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        current_expenses: List[Expense],
    ) -> List[UnusualSpendingPattern]:
        """Detect first-time spending in categories.
        
        Args:
            user_id: User's UUID
            start_date: Current period start date
            end_date: Current period end date
            current_expenses: Expenses in the current period
            
        Returns:
            List of detected new category patterns
        """
        patterns = []
        
        # Get categories used in current period
        current_categories = {e.category_id for e in current_expenses}
        
        if not current_categories:
            return patterns
        
        # Check which categories have no expenses before the current period
        stmt = (
            select(Expense.category_id)
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.expense_date < start_date,
                    Expense.category_id.in_(current_categories),
                )
            )
            .distinct()
        )
        
        result = await self.db.execute(stmt)
        existing_categories = {row[0] for row in result.all()}
        
        # Find new categories
        new_categories = current_categories - existing_categories
        
        # Get category names and first expense amounts
        for expense in current_expenses:
            if expense.category_id in new_categories:
                # Only add once per category
                new_categories.discard(expense.category_id)
                patterns.append(UnusualSpendingPattern(
                    pattern_type="new_category",
                    description=f"First expense in '{expense.category.name if expense.category else 'Unknown'}' category",
                    severity="info",
                    category_id=expense.category_id,
                    category_name=expense.category.name if expense.category else None,
                ))
        
        return patterns
    
    async def get_full_analytics(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> SpendingAnalyticsResponse:
        """Get comprehensive spending analytics for a date range.
        
        Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
        
        Args:
            user_id: User's UUID
            start_date: Start date of the analysis period
            end_date: End date of the analysis period
            
        Returns:
            Complete spending analytics response
        """
        # Get all analytics components
        category_breakdown = await self.get_category_breakdown(user_id, start_date, end_date)
        spending_trends = await self.get_spending_trends(user_id, start_date, end_date)
        period_comparison = await self.get_period_comparison(user_id, start_date, end_date)
        unusual_patterns = await self.detect_unusual_spending(user_id, start_date, end_date)
        
        return SpendingAnalyticsResponse(
            start_date=start_date,
            end_date=end_date,
            category_breakdown=category_breakdown,
            spending_trends=spending_trends,
            period_comparison=period_comparison,
            unusual_patterns=unusual_patterns,
        )
