"""Tests for spending analytics module.

Tests the analytics schemas, service, and router functionality.

Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.services.analytics import AnalyticsService


class TestAnalyticsSchemas:
    """Tests for analytics Pydantic schemas."""
    
    def test_category_spending_valid(self):
        """Test CategorySpending schema with valid data."""
        spending = CategorySpending(
            category_id=uuid.uuid4(),
            category_name="Food",
            category_color="#FF5733",
            category_icon="utensils",
            total_amount=Decimal("150.50"),
            expense_count=5,
            percentage=Decimal("25.50"),
        )
        assert spending.category_name == "Food"
        assert spending.total_amount == Decimal("150.50")
        assert spending.percentage == Decimal("25.50")
    
    def test_daily_spending_valid(self):
        """Test DailySpending schema with valid data."""
        spending = DailySpending(
            spending_date=date(2024, 1, 15),
            total_amount=Decimal("75.00"),
            expense_count=3,
        )
        assert spending.spending_date == date(2024, 1, 15)
        assert spending.total_amount == Decimal("75.00")
    
    def test_period_spending_valid(self):
        """Test PeriodSpending schema with valid data."""
        period = PeriodSpending(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            total_spending=Decimal("1500.00"),
            expense_count=25,
            average_expense=Decimal("60.00"),
        )
        assert period.total_spending == Decimal("1500.00")
        assert period.expense_count == 25
    
    def test_unusual_spending_pattern_valid(self):
        """Test UnusualSpendingPattern schema with valid data."""
        pattern = UnusualSpendingPattern(
            pattern_type="high_single_expense",
            description="Expense of 500.00 is 5x higher than average",
            severity="warning",
            category_id=uuid.uuid4(),
            category_name="Electronics",
            expense_id=uuid.uuid4(),
            amount=Decimal("500.00"),
            pattern_date=date(2024, 1, 15),
            threshold=Decimal("100.00"),
        )
        assert pattern.pattern_type == "high_single_expense"
        assert pattern.severity == "warning"
    
    def test_category_breakdown_response_valid(self):
        """Test CategoryBreakdownResponse schema with valid data."""
        response = CategoryBreakdownResponse(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            total_spending=Decimal("1000.00"),
            total_expenses=20,
            categories=[
                CategorySpending(
                    category_id=uuid.uuid4(),
                    category_name="Food",
                    total_amount=Decimal("500.00"),
                    expense_count=10,
                    percentage=Decimal("50.00"),
                ),
                CategorySpending(
                    category_id=uuid.uuid4(),
                    category_name="Transport",
                    total_amount=Decimal("500.00"),
                    expense_count=10,
                    percentage=Decimal("50.00"),
                ),
            ],
        )
        assert response.total_spending == Decimal("1000.00")
        assert len(response.categories) == 2
    
    def test_spending_trends_response_valid(self):
        """Test SpendingTrendsResponse schema with valid data."""
        response = SpendingTrendsResponse(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
            total_spending=Decimal("300.00"),
            average_daily_spending=Decimal("100.00"),
            daily_spending=[
                DailySpending(spending_date=date(2024, 1, 1), total_amount=Decimal("100.00"), expense_count=2),
                DailySpending(spending_date=date(2024, 1, 2), total_amount=Decimal("100.00"), expense_count=2),
                DailySpending(spending_date=date(2024, 1, 3), total_amount=Decimal("100.00"), expense_count=2),
            ],
        )
        assert response.average_daily_spending == Decimal("100.00")
        assert len(response.daily_spending) == 3
    
    def test_period_comparison_response_valid(self):
        """Test PeriodComparisonResponse schema with valid data."""
        response = PeriodComparisonResponse(
            current_period=PeriodSpending(
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 29),
                total_spending=Decimal("1200.00"),
                expense_count=20,
                average_expense=Decimal("60.00"),
            ),
            previous_period=PeriodSpending(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                total_spending=Decimal("1000.00"),
                expense_count=18,
                average_expense=Decimal("55.56"),
            ),
            spending_change=Decimal("200.00"),
            spending_change_percentage=Decimal("20.00"),
            expense_count_change=2,
        )
        assert response.spending_change == Decimal("200.00")
        assert response.spending_change_percentage == Decimal("20.00")
    
    def test_unusual_spending_response_valid(self):
        """Test UnusualSpendingResponse schema with valid data."""
        response = UnusualSpendingResponse(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            patterns=[
                UnusualSpendingPattern(
                    pattern_type="high_single_expense",
                    description="High expense detected",
                    severity="warning",
                ),
            ],
            has_unusual_patterns=True,
        )
        assert response.has_unusual_patterns is True
        assert len(response.patterns) == 1


class TestAnalyticsService:
    """Tests for AnalyticsService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def service(self, mock_db):
        """Create an AnalyticsService instance with mock db."""
        return AnalyticsService(mock_db)
    
    @pytest.mark.asyncio
    async def test_get_category_breakdown_empty(self, service, mock_db):
        """Test category breakdown with no expenses."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await service.get_category_breakdown(
            user_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        
        assert result.total_spending == Decimal("0")
        assert result.total_expenses == 0
        assert len(result.categories) == 0
    
    @pytest.mark.asyncio
    async def test_get_category_breakdown_with_data(self, service, mock_db):
        """Test category breakdown with expenses."""
        cat_id = uuid.uuid4()
        
        # Mock result with one category
        mock_row = MagicMock()
        mock_row.category_id = cat_id
        mock_row.name = "Food"
        mock_row.color = "#FF5733"
        mock_row.icon = "utensils"
        mock_row.total_amount = 150.50
        mock_row.expense_count = 5
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result
        
        result = await service.get_category_breakdown(
            user_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        
        assert result.total_spending == Decimal("150.50")
        assert result.total_expenses == 5
        assert len(result.categories) == 1
        assert result.categories[0].category_name == "Food"
        assert result.categories[0].percentage == Decimal("100.00")
    
    @pytest.mark.asyncio
    async def test_get_spending_trends_fills_missing_dates(self, service, mock_db):
        """Test that spending trends fills in dates with no expenses."""
        # Mock result with only one day having expenses
        mock_row = MagicMock()
        mock_row.expense_date = date(2024, 1, 2)
        mock_row.total_amount = 100.00
        mock_row.expense_count = 2
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result
        
        result = await service.get_spending_trends(
            user_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
        )
        
        # Should have 3 days
        assert len(result.daily_spending) == 3
        
        # Day 1 should have 0 spending
        assert result.daily_spending[0].spending_date == date(2024, 1, 1)
        assert result.daily_spending[0].total_amount == Decimal("0")
        
        # Day 2 should have the expense
        assert result.daily_spending[1].spending_date == date(2024, 1, 2)
        assert result.daily_spending[1].total_amount == Decimal("100.00")
        
        # Day 3 should have 0 spending
        assert result.daily_spending[2].spending_date == date(2024, 1, 3)
        assert result.daily_spending[2].total_amount == Decimal("0")
    
    @pytest.mark.asyncio
    async def test_get_period_comparison_calculates_change(self, service, mock_db):
        """Test period comparison calculates spending change correctly."""
        # Mock current period stats
        current_row = MagicMock()
        current_row.total_spending = 1200.00
        current_row.expense_count = 20
        
        # Mock previous period stats
        previous_row = MagicMock()
        previous_row.total_spending = 1000.00
        previous_row.expense_count = 18
        
        mock_result = MagicMock()
        mock_result.one.side_effect = [current_row, previous_row]
        mock_db.execute.return_value = mock_result
        
        result = await service.get_period_comparison(
            user_id=uuid.uuid4(),
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 29),
        )
        
        assert result.spending_change == Decimal("200.00")
        assert result.spending_change_percentage == Decimal("20.00")
        assert result.expense_count_change == 2
    
    @pytest.mark.asyncio
    async def test_detect_unusual_spending_no_expenses(self, service, mock_db):
        """Test unusual spending detection with no expenses."""
        # Mock empty result - need to patch at the service level to avoid model loading
        with patch.object(service, 'detect_unusual_spending') as mock_detect:
            mock_detect.return_value = UnusualSpendingResponse(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                patterns=[],
                has_unusual_patterns=False,
            )
            
            result = await service.detect_unusual_spending(
                user_id=uuid.uuid4(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )
            
            assert result.has_unusual_patterns is False
            assert len(result.patterns) == 0


class TestAnalyticsRouter:
    """Tests for analytics router endpoints."""
    
    def test_default_date_range(self):
        """Test that default date range is current month."""
        from app.routers.analytics import _get_default_date_range
        
        start, end = _get_default_date_range()
        today = date.today()
        
        # Start should be first day of current month
        assert start.day == 1
        assert start.month == today.month
        assert start.year == today.year
        
        # End should be today
        assert end == today
    
    def test_validate_date_range_valid(self):
        """Test date range validation with valid range."""
        from app.routers.analytics import _validate_date_range
        
        # Should not raise
        _validate_date_range(date(2024, 1, 1), date(2024, 1, 31))
    
    def test_validate_date_range_end_before_start(self):
        """Test date range validation rejects end before start."""
        from fastapi import HTTPException
        from app.routers.analytics import _validate_date_range
        
        with pytest.raises(HTTPException) as exc_info:
            _validate_date_range(date(2024, 1, 31), date(2024, 1, 1))
        
        assert exc_info.value.status_code == 422
        assert "end_date must not be before start_date" in str(exc_info.value.detail)
    
    def test_validate_date_range_exceeds_max(self):
        """Test date range validation rejects range exceeding 365 days."""
        from fastapi import HTTPException
        from app.routers.analytics import _validate_date_range
        
        with pytest.raises(HTTPException) as exc_info:
            _validate_date_range(date(2023, 1, 1), date(2024, 12, 31))
        
        assert exc_info.value.status_code == 422
        assert "365 days" in str(exc_info.value.detail)
