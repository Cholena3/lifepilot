"""Tests for weekly summary functionality.

Validates: Requirements 34.1, 34.2, 34.3, 34.4, 34.5
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.weekly_summary import WeeklySummary
from app.schemas.weekly_summary import (
    WeeklySummaryComparisons,
    WeeklySummaryMetrics,
)
from app.services.weekly_summary import (
    get_last_completed_week,
    get_week_boundaries,
)


class TestWeekBoundaries:
    """Tests for week boundary calculation functions."""

    def test_get_week_boundaries_monday(self):
        """Test that Monday returns correct week boundaries."""
        monday = date(2024, 1, 8)  # A Monday
        week_start, week_end = get_week_boundaries(monday)
        
        assert week_start == date(2024, 1, 8)
        assert week_end == date(2024, 1, 14)
        assert week_start.weekday() == 0  # Monday
        assert week_end.weekday() == 6  # Sunday

    def test_get_week_boundaries_wednesday(self):
        """Test that Wednesday returns correct week boundaries."""
        wednesday = date(2024, 1, 10)  # A Wednesday
        week_start, week_end = get_week_boundaries(wednesday)
        
        assert week_start == date(2024, 1, 8)
        assert week_end == date(2024, 1, 14)

    def test_get_week_boundaries_sunday(self):
        """Test that Sunday returns correct week boundaries."""
        sunday = date(2024, 1, 14)  # A Sunday
        week_start, week_end = get_week_boundaries(sunday)
        
        assert week_start == date(2024, 1, 8)
        assert week_end == date(2024, 1, 14)

    def test_get_last_completed_week(self):
        """Test that last completed week is calculated correctly."""
        week_start, week_end = get_last_completed_week()
        
        today = date.today()
        # Week start should be a Monday
        assert week_start.weekday() == 0
        # Week end should be a Sunday
        assert week_end.weekday() == 6
        # Week should be in the past
        assert week_end < today
        # Week should be exactly 7 days
        assert (week_end - week_start).days == 6


class TestWeeklySummaryMetrics:
    """Tests for WeeklySummaryMetrics schema."""

    def test_default_values(self):
        """Test that metrics have correct default values."""
        metrics = WeeklySummaryMetrics()
        
        assert metrics.expenses_total == Decimal("0")
        assert metrics.expenses_count == 0
        assert metrics.documents_added == 0
        assert metrics.health_records_logged == 0
        assert metrics.medicine_doses_taken == 0
        assert metrics.vitals_logged == 0
        assert metrics.wardrobe_items_added == 0
        assert metrics.outfits_worn == 0
        assert metrics.skills_updated == 0
        assert metrics.courses_progress_hours == Decimal("0")
        assert metrics.job_applications == 0
        assert metrics.achievements_added == 0
        assert metrics.exams_bookmarked == 0
        assert metrics.exams_applied == 0
        assert metrics.life_score == 0
        assert metrics.total_activities == 0

    def test_custom_values(self):
        """Test that metrics accept custom values."""
        metrics = WeeklySummaryMetrics(
            expenses_total=Decimal("1500.50"),
            expenses_count=15,
            documents_added=3,
            health_records_logged=5,
            life_score=75,
            total_activities=50,
        )
        
        assert metrics.expenses_total == Decimal("1500.50")
        assert metrics.expenses_count == 15
        assert metrics.documents_added == 3
        assert metrics.health_records_logged == 5
        assert metrics.life_score == 75
        assert metrics.total_activities == 50


class TestWeeklySummaryComparisons:
    """Tests for WeeklySummaryComparisons schema."""

    def test_default_values(self):
        """Test that comparisons have correct default values."""
        comparisons = WeeklySummaryComparisons()
        
        assert comparisons.expenses_total_change == Decimal("0")
        assert comparisons.expenses_total_change_percent is None
        assert comparisons.expenses_count_change == 0
        assert comparisons.documents_added_change == 0
        assert comparisons.life_score_change == 0
        assert comparisons.total_activities_change == 0

    def test_positive_changes(self):
        """Test that positive changes are represented correctly."""
        comparisons = WeeklySummaryComparisons(
            expenses_total_change=Decimal("200.00"),
            expenses_total_change_percent=Decimal("15.5"),
            expenses_count_change=5,
            life_score_change=10,
        )
        
        assert comparisons.expenses_total_change == Decimal("200.00")
        assert comparisons.expenses_total_change_percent == Decimal("15.5")
        assert comparisons.expenses_count_change == 5
        assert comparisons.life_score_change == 10

    def test_negative_changes(self):
        """Test that negative changes are represented correctly."""
        comparisons = WeeklySummaryComparisons(
            expenses_total_change=Decimal("-100.00"),
            expenses_total_change_percent=Decimal("-10.0"),
            expenses_count_change=-3,
            life_score_change=-5,
        )
        
        assert comparisons.expenses_total_change == Decimal("-100.00")
        assert comparisons.expenses_total_change_percent == Decimal("-10.0")
        assert comparisons.expenses_count_change == -3
        assert comparisons.life_score_change == -5


class TestWeeklySummaryModel:
    """Tests for WeeklySummary model."""

    def test_model_repr(self):
        """Test the model string representation."""
        summary = WeeklySummary(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            week_start=date(2024, 1, 8),
            week_end=date(2024, 1, 14),
            metrics={},
            comparisons={},
            generated_at=datetime.now(timezone.utc),
        )
        
        repr_str = repr(summary)
        assert "WeeklySummary" in repr_str
        assert "2024-01-08" in repr_str
        assert "2024-01-14" in repr_str
