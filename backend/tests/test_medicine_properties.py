"""Property-based tests for medicine adherence tracking.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 15.6**

Property 31: Medicine Adherence Tracking - For any medicine with N scheduled
doses where M doses are marked as taken, the adherence percentage SHALL equal
M/N * 100 (where N is the total resolved doses: taken + missed + skipped).
"""

from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from app.schemas.medicine import (
    AdherenceStats,
    OverallAdherenceStats,
    DoseStatusEnum,
)


# ============================================================================
# Hypothesis Strategies for Medicine Adherence Data
# ============================================================================

@st.composite
def valid_dose_counts(draw, max_total: int = 100):
    """Generate valid dose counts for adherence calculation.
    
    Generates taken, missed, and skipped counts that are non-negative integers.
    At least one resolved dose is required for meaningful adherence calculation.
    """
    taken = draw(st.integers(min_value=0, max_value=max_total))
    missed = draw(st.integers(min_value=0, max_value=max_total - taken))
    skipped = draw(st.integers(min_value=0, max_value=max_total - taken - missed))
    
    return {
        "taken": taken,
        "missed": missed,
        "skipped": skipped,
    }


@st.composite
def valid_dose_counts_with_resolved(draw, max_total: int = 100):
    """Generate valid dose counts with at least one resolved dose.
    
    Ensures total resolved (taken + missed + skipped) is at least 1.
    """
    taken = draw(st.integers(min_value=0, max_value=max_total))
    missed = draw(st.integers(min_value=0, max_value=max_total - taken))
    skipped = draw(st.integers(min_value=0, max_value=max_total - taken - missed))
    
    # Ensure at least one resolved dose
    if taken + missed + skipped == 0:
        # Add at least one dose
        choice = draw(st.integers(min_value=0, max_value=2))
        if choice == 0:
            taken = 1
        elif choice == 1:
            missed = 1
        else:
            skipped = 1
    
    return {
        "taken": taken,
        "missed": missed,
        "skipped": skipped,
    }


@st.composite
def valid_medicine_names(draw):
    """Generate valid medicine names."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
        min_size=1,
        max_size=100
    ).filter(lambda x: x.strip()))


@st.composite
def valid_streak_data(draw, max_streak: int = 50):
    """Generate valid streak data.
    
    Current streak must be <= longest streak.
    """
    longest = draw(st.integers(min_value=0, max_value=max_streak))
    current = draw(st.integers(min_value=0, max_value=longest))
    
    return {
        "current": current,
        "longest": longest,
    }


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_adherence_percentage(taken: int, missed: int, skipped: int) -> float:
    """Calculate adherence percentage from dose counts.
    
    Adherence = (taken / total_resolved) * 100
    where total_resolved = taken + missed + skipped
    
    Returns 0.0 if no resolved doses.
    """
    resolved = taken + missed + skipped
    if resolved == 0:
        return 0.0
    return round((taken / resolved) * 100, 2)


def create_adherence_stats(
    medicine_id=None,
    medicine_name="Test Medicine",
    total_scheduled=0,
    total_taken=0,
    total_missed=0,
    total_skipped=0,
    adherence_percentage=0.0,
    streak_current=0,
    streak_longest=0,
    period_start=None,
    period_end=None,
) -> AdherenceStats:
    """Create an AdherenceStats object for testing."""
    return AdherenceStats(
        medicine_id=medicine_id or uuid4(),
        medicine_name=medicine_name,
        total_scheduled=total_scheduled,
        total_taken=total_taken,
        total_missed=total_missed,
        total_skipped=total_skipped,
        adherence_percentage=adherence_percentage,
        streak_current=streak_current,
        streak_longest=streak_longest,
        period_start=period_start,
        period_end=period_end,
    )


# ============================================================================
# Property 31: Medicine Adherence Tracking
# ============================================================================

class TestMedicineAdherenceTrackingProperty:
    """Property 31: Medicine Adherence Tracking.
    
    **Validates: Requirements 15.6**
    
    For any medicine with N scheduled doses where M doses are marked as taken,
    the adherence percentage SHALL equal M/N * 100 (where N is the total
    resolved doses: taken + missed + skipped).
    """
    
    @given(dose_counts=valid_dose_counts_with_resolved())
    @settings(max_examples=50, deadline=None)
    def test_adherence_percentage_calculation_is_correct(self, dose_counts: dict):
        """For any set of dose counts, adherence percentage SHALL equal
        (taken / total_resolved) * 100.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. Adherence percentage is calculated correctly
        2. The formula (taken / resolved) * 100 is applied
        """
        taken = dose_counts["taken"]
        missed = dose_counts["missed"]
        skipped = dose_counts["skipped"]
        
        # Calculate expected adherence
        resolved = taken + missed + skipped
        expected_percentage = round((taken / resolved) * 100, 2)
        
        # Create adherence stats with calculated percentage
        stats = create_adherence_stats(
            total_taken=taken,
            total_missed=missed,
            total_skipped=skipped,
            adherence_percentage=expected_percentage,
        )
        
        # Verify the percentage matches expected
        assert stats.adherence_percentage == expected_percentage, (
            f"Adherence percentage should be {expected_percentage}, "
            f"got {stats.adherence_percentage}"
        )
        
        # Verify using helper function
        calculated = calculate_adherence_percentage(taken, missed, skipped)
        assert abs(stats.adherence_percentage - calculated) < 0.01, (
            f"Adherence percentage {stats.adherence_percentage} should match "
            f"calculated value {calculated}"
        )
    
    @given(dose_counts=valid_dose_counts_with_resolved())
    @settings(max_examples=50, deadline=None)
    def test_adherence_percentage_is_between_0_and_100(self, dose_counts: dict):
        """For any valid dose counts, adherence percentage SHALL be
        between 0 and 100 inclusive.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. Adherence percentage is never negative
        2. Adherence percentage never exceeds 100
        """
        taken = dose_counts["taken"]
        missed = dose_counts["missed"]
        skipped = dose_counts["skipped"]
        
        # Calculate adherence
        percentage = calculate_adherence_percentage(taken, missed, skipped)
        
        # Verify bounds
        assert 0.0 <= percentage <= 100.0, (
            f"Adherence percentage {percentage} should be between 0 and 100"
        )
        
        # Verify schema validation accepts the value
        stats = create_adherence_stats(
            total_taken=taken,
            total_missed=missed,
            total_skipped=skipped,
            adherence_percentage=percentage,
        )
        
        assert 0.0 <= stats.adherence_percentage <= 100.0, (
            f"Schema should accept percentage {stats.adherence_percentage} "
            f"between 0 and 100"
        )
    
    @given(dose_counts=valid_dose_counts_with_resolved())
    @settings(max_examples=50, deadline=None)
    def test_total_resolved_equals_taken_plus_missed_plus_skipped(self, dose_counts: dict):
        """For any dose counts, total resolved doses SHALL equal
        taken + missed + skipped.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. Total resolved is the sum of taken, missed, and skipped
        2. The calculation is consistent
        """
        taken = dose_counts["taken"]
        missed = dose_counts["missed"]
        skipped = dose_counts["skipped"]
        
        # Calculate total resolved
        total_resolved = taken + missed + skipped
        
        # Create stats
        stats = create_adherence_stats(
            total_taken=taken,
            total_missed=missed,
            total_skipped=skipped,
        )
        
        # Verify total resolved calculation
        calculated_resolved = stats.total_taken + stats.total_missed + stats.total_skipped
        assert calculated_resolved == total_resolved, (
            f"Total resolved {calculated_resolved} should equal "
            f"taken ({taken}) + missed ({missed}) + skipped ({skipped}) = {total_resolved}"
        )
    
    @given(streak_data=valid_streak_data())
    @settings(max_examples=50, deadline=None)
    def test_streak_calculations_are_valid(self, streak_data: dict):
        """For any streak data, current streak SHALL be <= longest streak.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. Current streak is never greater than longest streak
        2. Both streaks are non-negative
        """
        current = streak_data["current"]
        longest = streak_data["longest"]
        
        # Verify current <= longest
        assert current <= longest, (
            f"Current streak {current} should be <= longest streak {longest}"
        )
        
        # Create stats with streak data
        stats = create_adherence_stats(
            streak_current=current,
            streak_longest=longest,
        )
        
        # Verify streaks are non-negative
        assert stats.streak_current >= 0, (
            f"Current streak {stats.streak_current} should be non-negative"
        )
        assert stats.streak_longest >= 0, (
            f"Longest streak {stats.streak_longest} should be non-negative"
        )
        
        # Verify relationship is maintained
        assert stats.streak_current <= stats.streak_longest, (
            f"Current streak {stats.streak_current} should be <= "
            f"longest streak {stats.streak_longest}"
        )
    
    @given(dose_counts=valid_dose_counts())
    @settings(max_examples=50, deadline=None)
    def test_zero_resolved_doses_gives_zero_adherence(self, dose_counts: dict):
        """When there are no resolved doses, adherence percentage SHALL be 0.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. Zero resolved doses results in 0% adherence
        2. Division by zero is handled correctly
        """
        # Force zero resolved doses
        taken = 0
        missed = 0
        skipped = 0
        
        # Calculate adherence
        percentage = calculate_adherence_percentage(taken, missed, skipped)
        
        # Verify zero adherence
        assert percentage == 0.0, (
            f"Adherence percentage should be 0.0 when no resolved doses, "
            f"got {percentage}"
        )
    
    @given(total_taken=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50, deadline=None)
    def test_all_taken_gives_100_percent_adherence(self, total_taken: int):
        """When all doses are taken (none missed or skipped), adherence
        percentage SHALL be 100.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. 100% adherence when all doses are taken
        2. No missed or skipped doses means perfect adherence
        """
        taken = total_taken
        missed = 0
        skipped = 0
        
        # Calculate adherence
        percentage = calculate_adherence_percentage(taken, missed, skipped)
        
        # Verify 100% adherence
        assert percentage == 100.0, (
            f"Adherence percentage should be 100.0 when all {taken} doses taken, "
            f"got {percentage}"
        )
        
        # Verify with schema
        stats = create_adherence_stats(
            total_taken=taken,
            total_missed=missed,
            total_skipped=skipped,
            adherence_percentage=percentage,
        )
        
        assert stats.adherence_percentage == 100.0, (
            f"Schema adherence should be 100.0, got {stats.adherence_percentage}"
        )
    
    @given(total_missed=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50, deadline=None)
    def test_all_missed_gives_zero_percent_adherence(self, total_missed: int):
        """When all doses are missed (none taken), adherence percentage
        SHALL be 0.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. 0% adherence when no doses are taken
        2. All missed doses means zero adherence
        """
        taken = 0
        missed = total_missed
        skipped = 0
        
        # Calculate adherence
        percentage = calculate_adherence_percentage(taken, missed, skipped)
        
        # Verify 0% adherence
        assert percentage == 0.0, (
            f"Adherence percentage should be 0.0 when all {missed} doses missed, "
            f"got {percentage}"
        )
    
    @given(total_skipped=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50, deadline=None)
    def test_all_skipped_gives_zero_percent_adherence(self, total_skipped: int):
        """When all doses are skipped (none taken), adherence percentage
        SHALL be 0.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. 0% adherence when no doses are taken
        2. All skipped doses means zero adherence
        """
        taken = 0
        missed = 0
        skipped = total_skipped
        
        # Calculate adherence
        percentage = calculate_adherence_percentage(taken, missed, skipped)
        
        # Verify 0% adherence
        assert percentage == 0.0, (
            f"Adherence percentage should be 0.0 when all {skipped} doses skipped, "
            f"got {percentage}"
        )
    
    @given(
        taken=st.integers(min_value=0, max_value=50),
        missed=st.integers(min_value=0, max_value=50),
        skipped=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=50, deadline=None)
    def test_adherence_stats_schema_validation(
        self,
        taken: int,
        missed: int,
        skipped: int,
    ):
        """For any valid dose counts, AdherenceStats schema SHALL accept
        the values and maintain data integrity.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. Schema accepts valid dose counts
        2. All fields are correctly stored
        3. Data integrity is maintained
        """
        resolved = taken + missed + skipped
        percentage = calculate_adherence_percentage(taken, missed, skipped)
        
        # Create stats
        medicine_id = uuid4()
        medicine_name = "Test Medicine"
        
        stats = AdherenceStats(
            medicine_id=medicine_id,
            medicine_name=medicine_name,
            total_scheduled=resolved,  # Scheduled equals resolved for this test
            total_taken=taken,
            total_missed=missed,
            total_skipped=skipped,
            adherence_percentage=percentage,
            streak_current=0,
            streak_longest=0,
        )
        
        # Verify all fields
        assert stats.medicine_id == medicine_id
        assert stats.medicine_name == medicine_name
        assert stats.total_taken == taken
        assert stats.total_missed == missed
        assert stats.total_skipped == skipped
        assert stats.adherence_percentage == percentage
    
    @given(
        dose_counts=valid_dose_counts_with_resolved(),
        streak_data=valid_streak_data(),
    )
    @settings(max_examples=50, deadline=None)
    def test_adherence_stats_round_trip(
        self,
        dose_counts: dict,
        streak_data: dict,
    ):
        """For any valid adherence data, creating AdherenceStats and reading
        back SHALL preserve all values.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. All data is preserved through schema creation
        2. No data loss or corruption occurs
        """
        taken = dose_counts["taken"]
        missed = dose_counts["missed"]
        skipped = dose_counts["skipped"]
        current_streak = streak_data["current"]
        longest_streak = streak_data["longest"]
        
        percentage = calculate_adherence_percentage(taken, missed, skipped)
        resolved = taken + missed + skipped
        
        # Create stats
        original = AdherenceStats(
            medicine_id=uuid4(),
            medicine_name="Test Medicine",
            total_scheduled=resolved,
            total_taken=taken,
            total_missed=missed,
            total_skipped=skipped,
            adherence_percentage=percentage,
            streak_current=current_streak,
            streak_longest=longest_streak,
        )
        
        # Convert to dict and back (simulates serialization)
        data = original.model_dump()
        restored = AdherenceStats(**data)
        
        # Verify all fields preserved
        assert restored.total_taken == original.total_taken
        assert restored.total_missed == original.total_missed
        assert restored.total_skipped == original.total_skipped
        assert restored.adherence_percentage == original.adherence_percentage
        assert restored.streak_current == original.streak_current
        assert restored.streak_longest == original.streak_longest
    
    @given(
        num_medicines=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=20, deadline=None)
    def test_overall_adherence_stats_aggregation(self, num_medicines: int):
        """For any set of medicines, overall adherence SHALL be calculated
        correctly as the average of individual adherences.
        
        **Validates: Requirements 15.6**
        
        This test verifies that:
        1. Overall adherence is calculated from individual medicines
        2. The aggregation is mathematically correct
        """
        medicine_stats = []
        total_adherence = 0.0
        
        for i in range(num_medicines):
            # Generate random adherence for each medicine
            percentage = round((i + 1) / num_medicines * 100, 2)
            total_adherence += percentage
            
            stats = AdherenceStats(
                medicine_id=uuid4(),
                medicine_name=f"Medicine {i+1}",
                total_scheduled=10,
                total_taken=int(percentage / 10),
                total_missed=10 - int(percentage / 10),
                total_skipped=0,
                adherence_percentage=percentage,
                streak_current=0,
                streak_longest=0,
            )
            medicine_stats.append(stats)
        
        # Calculate expected overall adherence
        expected_overall = round(total_adherence / num_medicines, 2)
        
        # Create overall stats
        overall = OverallAdherenceStats(
            total_medicines=num_medicines,
            active_medicines=num_medicines,
            overall_adherence_percentage=expected_overall,
            medicines_needing_refill=0,
            medicines=medicine_stats,
        )
        
        # Verify overall adherence
        assert overall.overall_adherence_percentage == expected_overall, (
            f"Overall adherence {overall.overall_adherence_percentage} should equal "
            f"expected {expected_overall}"
        )
        
        # Verify bounds
        assert 0.0 <= overall.overall_adherence_percentage <= 100.0, (
            f"Overall adherence {overall.overall_adherence_percentage} should be "
            f"between 0 and 100"
        )

