"""Property-based tests for Weekly Summary module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 34.3**
"""

from decimal import Decimal
from typing import Optional

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.schemas.weekly_summary import (
    WeeklySummaryComparisons,
    WeeklySummaryMetrics,
)
from app.services.weekly_summary import WeeklySummaryService


# ============================================================================
# Hypothesis Strategies for Weekly Summary Data
# ============================================================================

@st.composite
def valid_weekly_summary_metrics(draw):
    """Generate valid WeeklySummaryMetrics for testing.
    
    Generates realistic metrics values within reasonable bounds.
    """
    # Money module
    expenses_total = Decimal(str(draw(st.integers(min_value=0, max_value=100000))))
    expenses_count = draw(st.integers(min_value=0, max_value=200))
    
    # Documents module
    documents_added = draw(st.integers(min_value=0, max_value=50))
    
    # Health module
    health_records_logged = draw(st.integers(min_value=0, max_value=30))
    medicine_doses_taken = draw(st.integers(min_value=0, max_value=100))
    vitals_logged = draw(st.integers(min_value=0, max_value=50))
    
    # Wardrobe module
    wardrobe_items_added = draw(st.integers(min_value=0, max_value=20))
    outfits_worn = draw(st.integers(min_value=0, max_value=14))
    
    # Career module
    skills_updated = draw(st.integers(min_value=0, max_value=20))
    courses_progress_hours = Decimal(str(draw(st.integers(min_value=0, max_value=100))))
    job_applications = draw(st.integers(min_value=0, max_value=30))
    achievements_added = draw(st.integers(min_value=0, max_value=10))
    
    # Exams module
    exams_bookmarked = draw(st.integers(min_value=0, max_value=20))
    exams_applied = draw(st.integers(min_value=0, max_value=10))
    
    # Overall
    life_score = draw(st.integers(min_value=0, max_value=100))
    
    # Calculate total activities
    total_activities = (
        expenses_count +
        documents_added +
        health_records_logged +
        medicine_doses_taken +
        vitals_logged +
        wardrobe_items_added +
        outfits_worn +
        skills_updated +
        job_applications +
        achievements_added +
        exams_bookmarked +
        exams_applied
    )
    
    return WeeklySummaryMetrics(
        expenses_total=expenses_total,
        expenses_count=expenses_count,
        documents_added=documents_added,
        health_records_logged=health_records_logged,
        medicine_doses_taken=medicine_doses_taken,
        vitals_logged=vitals_logged,
        wardrobe_items_added=wardrobe_items_added,
        outfits_worn=outfits_worn,
        skills_updated=skills_updated,
        courses_progress_hours=courses_progress_hours,
        job_applications=job_applications,
        achievements_added=achievements_added,
        exams_bookmarked=exams_bookmarked,
        exams_applied=exams_applied,
        life_score=life_score,
        total_activities=total_activities,
    )


# ============================================================================
# Property 42: Weekly Summary Comparison
# ============================================================================

class TestWeeklySummaryComparisonProperty:
    """Property 42: Weekly Summary Comparison.
    
    **Validates: Requirements 34.3**
    
    For any weekly summary, the comparison metrics SHALL accurately reflect
    the difference between current week and previous week values.
    """
    
    @given(
        current=valid_weekly_summary_metrics(),
        previous=valid_weekly_summary_metrics(),
    )
    @settings(max_examples=100, deadline=None)
    def test_change_values_equal_current_minus_previous(
        self,
        current: WeeklySummaryMetrics,
        previous: WeeklySummaryMetrics,
    ):
        """For any two valid metrics, change values SHALL equal current - previous.
        
        **Validates: Requirements 34.3**
        
        This test verifies that:
        1. All numeric change fields equal current - previous
        2. The calculation is consistent for all metric types
        3. Both positive and negative changes are handled correctly
        """
        # Use the actual service method to calculate comparisons
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, current, previous
        )
        
        # Verify Money module changes
        assert comparisons.expenses_total_change == current.expenses_total - previous.expenses_total, (
            f"expenses_total_change {comparisons.expenses_total_change} should equal "
            f"current ({current.expenses_total}) - previous ({previous.expenses_total}) = "
            f"{current.expenses_total - previous.expenses_total}"
        )
        assert comparisons.expenses_count_change == current.expenses_count - previous.expenses_count, (
            f"expenses_count_change {comparisons.expenses_count_change} should equal "
            f"current ({current.expenses_count}) - previous ({previous.expenses_count})"
        )
        
        # Verify Documents module changes
        assert comparisons.documents_added_change == current.documents_added - previous.documents_added, (
            f"documents_added_change {comparisons.documents_added_change} should equal "
            f"current ({current.documents_added}) - previous ({previous.documents_added})"
        )
        
        # Verify Health module changes
        assert comparisons.health_records_logged_change == current.health_records_logged - previous.health_records_logged, (
            f"health_records_logged_change should equal current - previous"
        )
        assert comparisons.medicine_doses_taken_change == current.medicine_doses_taken - previous.medicine_doses_taken, (
            f"medicine_doses_taken_change should equal current - previous"
        )
        assert comparisons.vitals_logged_change == current.vitals_logged - previous.vitals_logged, (
            f"vitals_logged_change should equal current - previous"
        )
        
        # Verify Wardrobe module changes
        assert comparisons.wardrobe_items_added_change == current.wardrobe_items_added - previous.wardrobe_items_added, (
            f"wardrobe_items_added_change should equal current - previous"
        )
        assert comparisons.outfits_worn_change == current.outfits_worn - previous.outfits_worn, (
            f"outfits_worn_change should equal current - previous"
        )
        
        # Verify Career module changes
        assert comparisons.skills_updated_change == current.skills_updated - previous.skills_updated, (
            f"skills_updated_change should equal current - previous"
        )
        assert comparisons.courses_progress_hours_change == current.courses_progress_hours - previous.courses_progress_hours, (
            f"courses_progress_hours_change should equal current - previous"
        )
        assert comparisons.job_applications_change == current.job_applications - previous.job_applications, (
            f"job_applications_change should equal current - previous"
        )
        assert comparisons.achievements_added_change == current.achievements_added - previous.achievements_added, (
            f"achievements_added_change should equal current - previous"
        )
        
        # Verify Exams module changes
        assert comparisons.exams_bookmarked_change == current.exams_bookmarked - previous.exams_bookmarked, (
            f"exams_bookmarked_change should equal current - previous"
        )
        assert comparisons.exams_applied_change == current.exams_applied - previous.exams_applied, (
            f"exams_applied_change should equal current - previous"
        )
        
        # Verify Overall changes
        assert comparisons.life_score_change == current.life_score - previous.life_score, (
            f"life_score_change {comparisons.life_score_change} should equal "
            f"current ({current.life_score}) - previous ({previous.life_score})"
        )
        assert comparisons.total_activities_change == current.total_activities - previous.total_activities, (
            f"total_activities_change should equal current - previous"
        )
    
    @given(
        current=valid_weekly_summary_metrics(),
        previous=valid_weekly_summary_metrics(),
    )
    @settings(max_examples=100, deadline=None)
    def test_percentage_change_none_when_previous_is_zero(
        self,
        current: WeeklySummaryMetrics,
        previous: WeeklySummaryMetrics,
    ):
        """For any metrics where previous value is 0, percentage change SHALL be None.
        
        **Validates: Requirements 34.3**
        
        This test verifies that:
        1. When previous expenses_total is 0, percentage change is None
        2. Division by zero is handled correctly
        3. The behavior is consistent
        """
        # Force previous expenses_total to 0 to test this case
        previous_with_zero = WeeklySummaryMetrics(
            expenses_total=Decimal("0"),
            expenses_count=previous.expenses_count,
            documents_added=previous.documents_added,
            health_records_logged=previous.health_records_logged,
            medicine_doses_taken=previous.medicine_doses_taken,
            vitals_logged=previous.vitals_logged,
            wardrobe_items_added=previous.wardrobe_items_added,
            outfits_worn=previous.outfits_worn,
            skills_updated=previous.skills_updated,
            courses_progress_hours=previous.courses_progress_hours,
            job_applications=previous.job_applications,
            achievements_added=previous.achievements_added,
            exams_bookmarked=previous.exams_bookmarked,
            exams_applied=previous.exams_applied,
            life_score=previous.life_score,
            total_activities=previous.total_activities,
        )
        
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, current, previous_with_zero
        )
        
        # When previous is 0, percentage change should be None
        assert comparisons.expenses_total_change_percent is None, (
            f"expenses_total_change_percent should be None when previous is 0, "
            f"but got {comparisons.expenses_total_change_percent}"
        )
    
    @given(
        current=valid_weekly_summary_metrics(),
        previous=valid_weekly_summary_metrics(),
    )
    @settings(max_examples=100, deadline=None)
    def test_percentage_change_calculated_correctly_when_previous_nonzero(
        self,
        current: WeeklySummaryMetrics,
        previous: WeeklySummaryMetrics,
    ):
        """For any metrics where previous value is non-zero, percentage change
        SHALL be calculated correctly.
        
        **Validates: Requirements 34.3**
        
        This test verifies that:
        1. Percentage change = (current - previous) / previous * 100
        2. The calculation is rounded to 2 decimal places
        3. Both positive and negative percentages are handled
        """
        # Ensure previous expenses_total is non-zero
        assume(previous.expenses_total > 0)
        
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, current, previous
        )
        
        # Calculate expected percentage change
        expected_percent = round(
            (current.expenses_total - previous.expenses_total) / previous.expenses_total * 100,
            2
        )
        
        assert comparisons.expenses_total_change_percent is not None, (
            f"expenses_total_change_percent should not be None when previous > 0"
        )
        assert comparisons.expenses_total_change_percent == Decimal(str(expected_percent)), (
            f"expenses_total_change_percent {comparisons.expenses_total_change_percent} "
            f"should equal {expected_percent}"
        )
    
    @given(
        metrics=valid_weekly_summary_metrics(),
    )
    @settings(max_examples=50, deadline=None)
    def test_comparison_is_deterministic(
        self,
        metrics: WeeklySummaryMetrics,
    ):
        """For any two identical metrics, comparison SHALL be consistent.
        
        **Validates: Requirements 34.3**
        
        This test verifies that:
        1. Comparing identical metrics produces zero changes
        2. The comparison is deterministic (same inputs = same outputs)
        3. Running the comparison multiple times yields the same result
        """
        # Compare metrics with itself
        comparisons1 = WeeklySummaryService._calculate_comparisons(
            None, metrics, metrics
        )
        comparisons2 = WeeklySummaryService._calculate_comparisons(
            None, metrics, metrics
        )
        
        # All changes should be zero when comparing identical metrics
        assert comparisons1.expenses_total_change == Decimal("0"), (
            f"expenses_total_change should be 0 when comparing identical metrics"
        )
        assert comparisons1.expenses_count_change == 0
        assert comparisons1.documents_added_change == 0
        assert comparisons1.health_records_logged_change == 0
        assert comparisons1.medicine_doses_taken_change == 0
        assert comparisons1.vitals_logged_change == 0
        assert comparisons1.wardrobe_items_added_change == 0
        assert comparisons1.outfits_worn_change == 0
        assert comparisons1.skills_updated_change == 0
        assert comparisons1.courses_progress_hours_change == Decimal("0")
        assert comparisons1.job_applications_change == 0
        assert comparisons1.achievements_added_change == 0
        assert comparisons1.exams_bookmarked_change == 0
        assert comparisons1.exams_applied_change == 0
        assert comparisons1.life_score_change == 0
        assert comparisons1.total_activities_change == 0
        
        # Results should be identical (deterministic)
        assert comparisons1.expenses_total_change == comparisons2.expenses_total_change
        assert comparisons1.expenses_count_change == comparisons2.expenses_count_change
        assert comparisons1.life_score_change == comparisons2.life_score_change
        assert comparisons1.total_activities_change == comparisons2.total_activities_change
    
    @given(
        current=valid_weekly_summary_metrics(),
        previous=valid_weekly_summary_metrics(),
    )
    @settings(max_examples=50, deadline=None)
    def test_comparison_sign_reflects_direction_of_change(
        self,
        current: WeeklySummaryMetrics,
        previous: WeeklySummaryMetrics,
    ):
        """For any comparison, the sign of change SHALL reflect direction.
        
        **Validates: Requirements 34.3**
        
        This test verifies that:
        1. Positive change when current > previous
        2. Negative change when current < previous
        3. Zero change when current == previous
        """
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, current, previous
        )
        
        # Verify sign for expenses_total
        if current.expenses_total > previous.expenses_total:
            assert comparisons.expenses_total_change > 0, (
                f"Change should be positive when current > previous"
            )
        elif current.expenses_total < previous.expenses_total:
            assert comparisons.expenses_total_change < 0, (
                f"Change should be negative when current < previous"
            )
        else:
            assert comparisons.expenses_total_change == 0, (
                f"Change should be zero when current == previous"
            )
        
        # Verify sign for life_score
        if current.life_score > previous.life_score:
            assert comparisons.life_score_change > 0
        elif current.life_score < previous.life_score:
            assert comparisons.life_score_change < 0
        else:
            assert comparisons.life_score_change == 0
        
        # Verify sign for total_activities
        if current.total_activities > previous.total_activities:
            assert comparisons.total_activities_change > 0
        elif current.total_activities < previous.total_activities:
            assert comparisons.total_activities_change < 0
        else:
            assert comparisons.total_activities_change == 0


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestWeeklySummaryComparisonEdgeCases:
    """Edge case tests for Weekly Summary Comparison.
    
    **Validates: Requirements 34.3**
    """
    
    def test_zero_metrics_comparison(self):
        """When both weeks have zero metrics, all changes SHALL be zero.
        
        **Validates: Requirements 34.3**
        """
        zero_metrics = WeeklySummaryMetrics()
        
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, zero_metrics, zero_metrics
        )
        
        assert comparisons.expenses_total_change == Decimal("0")
        assert comparisons.expenses_total_change_percent is None  # 0/0 case
        assert comparisons.expenses_count_change == 0
        assert comparisons.documents_added_change == 0
        assert comparisons.life_score_change == 0
        assert comparisons.total_activities_change == 0
    
    def test_large_positive_change(self):
        """When current is much larger than previous, change SHALL be large positive.
        
        **Validates: Requirements 34.3**
        """
        previous = WeeklySummaryMetrics(
            expenses_total=Decimal("100"),
            expenses_count=5,
            life_score=20,
            total_activities=10,
        )
        current = WeeklySummaryMetrics(
            expenses_total=Decimal("10000"),
            expenses_count=100,
            life_score=95,
            total_activities=200,
        )
        
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, current, previous
        )
        
        assert comparisons.expenses_total_change == Decimal("9900")
        assert comparisons.expenses_total_change_percent == Decimal("9900.00")
        assert comparisons.expenses_count_change == 95
        assert comparisons.life_score_change == 75
        assert comparisons.total_activities_change == 190
    
    def test_large_negative_change(self):
        """When current is much smaller than previous, change SHALL be large negative.
        
        **Validates: Requirements 34.3**
        """
        previous = WeeklySummaryMetrics(
            expenses_total=Decimal("10000"),
            expenses_count=100,
            life_score=95,
            total_activities=200,
        )
        current = WeeklySummaryMetrics(
            expenses_total=Decimal("100"),
            expenses_count=5,
            life_score=20,
            total_activities=10,
        )
        
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, current, previous
        )
        
        assert comparisons.expenses_total_change == Decimal("-9900")
        assert comparisons.expenses_total_change_percent == Decimal("-99.00")
        assert comparisons.expenses_count_change == -95
        assert comparisons.life_score_change == -75
        assert comparisons.total_activities_change == -190
    
    def test_percentage_change_precision(self):
        """Percentage change SHALL be rounded to 2 decimal places.
        
        **Validates: Requirements 34.3**
        """
        previous = WeeklySummaryMetrics(
            expenses_total=Decimal("300"),
        )
        current = WeeklySummaryMetrics(
            expenses_total=Decimal("400"),
        )
        
        comparisons = WeeklySummaryService._calculate_comparisons(
            None, current, previous
        )
        
        # (400 - 300) / 300 * 100 = 33.333...
        # Should be rounded to 33.33
        assert comparisons.expenses_total_change_percent == Decimal("33.33"), (
            f"Percentage should be 33.33, got {comparisons.expenses_total_change_percent}"
        )
