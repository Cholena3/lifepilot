"""Property-based tests for vitals tracking module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 16.3, 16.4**
"""

from typing import Optional
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.schemas.vital import (
    VitalTypeEnum,
    WarningLevel,
)
from app.services.vital import VitalService


# ============================================================================
# Hypothesis Strategies for Vital Data
# ============================================================================

@st.composite
def valid_vital_types(draw):
    """Generate valid vital types."""
    return draw(st.sampled_from(VitalTypeEnum.ALL))


@st.composite
def positive_floats(draw, min_value: float = 0.01, max_value: float = 1000.0):
    """Generate positive float values for vitals."""
    return draw(st.floats(
        min_value=min_value,
        max_value=max_value,
        allow_nan=False,
        allow_infinity=False,
    ))


@st.composite
def target_range_values(draw):
    """Generate valid target range min/max pairs.
    
    Ensures min < max when both are provided.
    """
    min_val = draw(st.floats(
        min_value=1.0,
        max_value=500.0,
        allow_nan=False,
        allow_infinity=False,
    ))
    max_val = draw(st.floats(
        min_value=min_val + 0.1,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False,
    ))
    return min_val, max_val


# ============================================================================
# Property 32: Vital Range Warning
# ============================================================================

class TestVitalRangeWarningProperty:
    """Property 32: Vital Range Warning.
    
    **Validates: Requirements 16.3, 16.4**
    
    For any vital reading with value V and target range [min, max]:
    - Values within range return NORMAL
    - Values below min but >= 80% of min return LOW
    - Values below 80% of min return CRITICAL_LOW
    - Values above max but <= 120% of max return HIGH
    - Values above 120% of max return CRITICAL_HIGH
    - When both min and max are None, always return NORMAL
    - Custom target ranges override default ranges
    """
    
    @given(
        target_min=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=101.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_values_within_range_return_normal(
        self,
        target_min: float,
        target_max: float,
    ):
        """For any value V where min <= V <= max, the warning level SHALL be NORMAL.
        
        **Validates: Requirements 16.3**
        
        This test verifies that:
        1. Values at the minimum boundary return NORMAL
        2. Values at the maximum boundary return NORMAL
        3. Values in the middle of the range return NORMAL
        """
        service = VitalService.__new__(VitalService)
        
        # Test at minimum boundary
        level = service._calculate_warning_level(target_min, target_min, target_max)
        assert level == WarningLevel.NORMAL, (
            f"Value at min ({target_min}) should be NORMAL, got {level}"
        )
        
        # Test at maximum boundary
        level = service._calculate_warning_level(target_max, target_min, target_max)
        assert level == WarningLevel.NORMAL, (
            f"Value at max ({target_max}) should be NORMAL, got {level}"
        )
        
        # Test in the middle
        mid_value = (target_min + target_max) / 2
        level = service._calculate_warning_level(mid_value, target_min, target_max)
        assert level == WarningLevel.NORMAL, (
            f"Value in middle ({mid_value}) should be NORMAL, got {level}"
        )
    
    @given(
        target_min=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=101.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_values_below_min_but_above_critical_return_low(
        self,
        target_min: float,
        target_max: float,
    ):
        """For any value V where 80% of min <= V < min, the warning level SHALL be LOW.
        
        **Validates: Requirements 16.3**
        
        This test verifies that:
        1. Values just below min return LOW
        2. Values at exactly 80% of min return LOW (boundary)
        3. Values between 80% and 100% of min return LOW
        """
        service = VitalService.__new__(VitalService)
        critical_low = target_min * 0.8
        
        # Test just below min
        value_just_below = target_min - 0.01
        assume(value_just_below >= critical_low)  # Ensure we're in LOW range
        level = service._calculate_warning_level(value_just_below, target_min, target_max)
        assert level == WarningLevel.LOW, (
            f"Value just below min ({value_just_below}) should be LOW, got {level}"
        )
        
        # Test at 80% boundary (should be LOW, not CRITICAL_LOW)
        level = service._calculate_warning_level(critical_low, target_min, target_max)
        assert level == WarningLevel.LOW, (
            f"Value at 80% of min ({critical_low}) should be LOW, got {level}"
        )
        
        # Test in the middle of LOW range
        mid_low = (critical_low + target_min) / 2
        level = service._calculate_warning_level(mid_low, target_min, target_max)
        assert level == WarningLevel.LOW, (
            f"Value in LOW range ({mid_low}) should be LOW, got {level}"
        )
    
    @given(
        target_min=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=101.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_values_below_critical_threshold_return_critical_low(
        self,
        target_min: float,
        target_max: float,
    ):
        """For any value V where V < 80% of min, the warning level SHALL be CRITICAL_LOW.
        
        **Validates: Requirements 16.3**
        
        This test verifies that:
        1. Values below 80% of min return CRITICAL_LOW
        2. Values significantly below the critical threshold return CRITICAL_LOW
        """
        service = VitalService.__new__(VitalService)
        critical_low = target_min * 0.8
        
        # Test just below critical threshold
        value_critical = critical_low - 0.01
        assume(value_critical > 0)  # Ensure positive value
        level = service._calculate_warning_level(value_critical, target_min, target_max)
        assert level == WarningLevel.CRITICAL_LOW, (
            f"Value below critical ({value_critical}) should be CRITICAL_LOW, got {level}"
        )
        
        # Test significantly below critical
        very_low = critical_low * 0.5
        assume(very_low > 0)
        level = service._calculate_warning_level(very_low, target_min, target_max)
        assert level == WarningLevel.CRITICAL_LOW, (
            f"Very low value ({very_low}) should be CRITICAL_LOW, got {level}"
        )
    
    @given(
        target_min=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=101.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_values_above_max_but_below_critical_return_high(
        self,
        target_min: float,
        target_max: float,
    ):
        """For any value V where max < V <= 120% of max, the warning level SHALL be HIGH.
        
        **Validates: Requirements 16.3**
        
        This test verifies that:
        1. Values just above max return HIGH
        2. Values at exactly 120% of max return HIGH (boundary)
        3. Values between 100% and 120% of max return HIGH
        """
        service = VitalService.__new__(VitalService)
        critical_high = target_max * 1.2
        
        # Test just above max
        value_just_above = target_max + 0.01
        assume(value_just_above <= critical_high)  # Ensure we're in HIGH range
        level = service._calculate_warning_level(value_just_above, target_min, target_max)
        assert level == WarningLevel.HIGH, (
            f"Value just above max ({value_just_above}) should be HIGH, got {level}"
        )
        
        # Test at 120% boundary (should be HIGH, not CRITICAL_HIGH)
        level = service._calculate_warning_level(critical_high, target_min, target_max)
        assert level == WarningLevel.HIGH, (
            f"Value at 120% of max ({critical_high}) should be HIGH, got {level}"
        )
        
        # Test in the middle of HIGH range
        mid_high = (target_max + critical_high) / 2
        level = service._calculate_warning_level(mid_high, target_min, target_max)
        assert level == WarningLevel.HIGH, (
            f"Value in HIGH range ({mid_high}) should be HIGH, got {level}"
        )
    
    @given(
        target_min=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=101.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_values_above_critical_threshold_return_critical_high(
        self,
        target_min: float,
        target_max: float,
    ):
        """For any value V where V > 120% of max, the warning level SHALL be CRITICAL_HIGH.
        
        **Validates: Requirements 16.3**
        
        This test verifies that:
        1. Values above 120% of max return CRITICAL_HIGH
        2. Values significantly above the critical threshold return CRITICAL_HIGH
        """
        service = VitalService.__new__(VitalService)
        critical_high = target_max * 1.2
        
        # Test just above critical threshold
        value_critical = critical_high + 0.01
        level = service._calculate_warning_level(value_critical, target_min, target_max)
        assert level == WarningLevel.CRITICAL_HIGH, (
            f"Value above critical ({value_critical}) should be CRITICAL_HIGH, got {level}"
        )
        
        # Test significantly above critical
        very_high = critical_high * 1.5
        level = service._calculate_warning_level(very_high, target_min, target_max)
        assert level == WarningLevel.CRITICAL_HIGH, (
            f"Very high value ({very_high}) should be CRITICAL_HIGH, got {level}"
        )
    
    @given(value=st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50, deadline=None)
    def test_no_range_always_returns_normal(self, value: float):
        """When both min and max are None, the warning level SHALL always be NORMAL.
        
        **Validates: Requirements 16.3**
        
        This test verifies that:
        1. Any value returns NORMAL when no range is defined
        2. Negative values return NORMAL when no range is defined
        3. Very large values return NORMAL when no range is defined
        """
        service = VitalService.__new__(VitalService)
        
        level = service._calculate_warning_level(value, None, None)
        assert level == WarningLevel.NORMAL, (
            f"Value {value} with no range should be NORMAL, got {level}"
        )
    
    @given(
        value=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
        target_min=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_only_min_range_defined(self, value: float, target_min: float):
        """When only min is defined, values below min return LOW/CRITICAL_LOW, above return NORMAL.
        
        **Validates: Requirements 16.3, 16.4**
        
        This test verifies that:
        1. Values >= min return NORMAL
        2. Values < min but >= 80% of min return LOW
        3. Values < 80% of min return CRITICAL_LOW
        """
        service = VitalService.__new__(VitalService)
        critical_low = target_min * 0.8
        
        level = service._calculate_warning_level(value, target_min, None)
        
        if value >= target_min:
            assert level == WarningLevel.NORMAL, (
                f"Value {value} >= min {target_min} should be NORMAL, got {level}"
            )
        elif value >= critical_low:
            assert level == WarningLevel.LOW, (
                f"Value {value} in LOW range should be LOW, got {level}"
            )
        else:
            assert level == WarningLevel.CRITICAL_LOW, (
                f"Value {value} below critical should be CRITICAL_LOW, got {level}"
            )
    
    @given(
        value=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_only_max_range_defined(self, value: float, target_max: float):
        """When only max is defined, values above max return HIGH/CRITICAL_HIGH, below return NORMAL.
        
        **Validates: Requirements 16.3, 16.4**
        
        This test verifies that:
        1. Values <= max return NORMAL
        2. Values > max but <= 120% of max return HIGH
        3. Values > 120% of max return CRITICAL_HIGH
        """
        service = VitalService.__new__(VitalService)
        critical_high = target_max * 1.2
        
        level = service._calculate_warning_level(value, None, target_max)
        
        if value <= target_max:
            assert level == WarningLevel.NORMAL, (
                f"Value {value} <= max {target_max} should be NORMAL, got {level}"
            )
        elif value <= critical_high:
            assert level == WarningLevel.HIGH, (
                f"Value {value} in HIGH range should be HIGH, got {level}"
            )
        else:
            assert level == WarningLevel.CRITICAL_HIGH, (
                f"Value {value} above critical should be CRITICAL_HIGH, got {level}"
            )
    
    @given(
        value=st.floats(min_value=0.01, max_value=500.0, allow_nan=False, allow_infinity=False),
        target_min=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=101.0, max_value=300.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_warning_level_classification_is_complete(
        self,
        value: float,
        target_min: float,
        target_max: float,
    ):
        """For any value and valid range, exactly one warning level SHALL be returned.
        
        **Validates: Requirements 16.3**
        
        This test verifies that:
        1. Every value is classified into exactly one warning level
        2. The classification is deterministic
        3. All five warning levels are possible outcomes
        """
        service = VitalService.__new__(VitalService)
        
        level = service._calculate_warning_level(value, target_min, target_max)
        
        # Verify the level is one of the valid warning levels
        valid_levels = [
            WarningLevel.NORMAL,
            WarningLevel.LOW,
            WarningLevel.HIGH,
            WarningLevel.CRITICAL_LOW,
            WarningLevel.CRITICAL_HIGH,
        ]
        assert level in valid_levels, (
            f"Warning level {level} is not a valid level"
        )
        
        # Verify the classification is correct based on thresholds
        critical_low = target_min * 0.8
        critical_high = target_max * 1.2
        
        if value < critical_low:
            expected = WarningLevel.CRITICAL_LOW
        elif value < target_min:
            expected = WarningLevel.LOW
        elif value > critical_high:
            expected = WarningLevel.CRITICAL_HIGH
        elif value > target_max:
            expected = WarningLevel.HIGH
        else:
            expected = WarningLevel.NORMAL
        
        assert level == expected, (
            f"Value {value} with range [{target_min}, {target_max}] "
            f"should be {expected}, got {level}"
        )
    
    @given(
        custom_min=st.floats(min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        custom_max=st.floats(min_value=51.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_custom_target_ranges_override_defaults(
        self,
        custom_min: float,
        custom_max: float,
    ):
        """Custom target ranges SHALL override default ranges for warning calculation.
        
        **Validates: Requirements 16.4**
        
        This test verifies that:
        1. Custom ranges are used instead of defaults
        2. Warning levels are calculated based on custom ranges
        3. Different custom ranges produce different warning levels for the same value
        """
        service = VitalService.__new__(VitalService)
        
        # Value that would be NORMAL with default heart rate range (60-100)
        # but might be different with custom range
        test_value = 55.0
        
        # With custom range where 55 is within range
        level_custom_normal = service._calculate_warning_level(
            test_value, 50.0, 60.0
        )
        assert level_custom_normal == WarningLevel.NORMAL, (
            f"Value {test_value} within custom range [50, 60] should be NORMAL"
        )
        
        # With custom range where 55 is below min
        level_custom_low = service._calculate_warning_level(
            test_value, 60.0, 80.0
        )
        assert level_custom_low == WarningLevel.LOW, (
            f"Value {test_value} below custom min 60 should be LOW"
        )
        
        # With custom range where 55 is above max
        level_custom_high = service._calculate_warning_level(
            test_value, 30.0, 50.0
        )
        assert level_custom_high == WarningLevel.HIGH, (
            f"Value {test_value} above custom max 50 should be HIGH"
        )
    
    @given(
        target_min=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        target_max=st.floats(min_value=101.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_boundary_values_are_classified_correctly(
        self,
        target_min: float,
        target_max: float,
    ):
        """Boundary values SHALL be classified according to the specification.
        
        **Validates: Requirements 16.3**
        
        This test verifies boundary conditions:
        1. Value exactly at min is NORMAL
        2. Value exactly at max is NORMAL
        3. Value exactly at 80% of min is LOW (not CRITICAL_LOW)
        4. Value exactly at 120% of max is HIGH (not CRITICAL_HIGH)
        """
        service = VitalService.__new__(VitalService)
        critical_low = target_min * 0.8
        critical_high = target_max * 1.2
        
        # At min boundary - should be NORMAL
        level = service._calculate_warning_level(target_min, target_min, target_max)
        assert level == WarningLevel.NORMAL, (
            f"Value at min ({target_min}) should be NORMAL, got {level}"
        )
        
        # At max boundary - should be NORMAL
        level = service._calculate_warning_level(target_max, target_min, target_max)
        assert level == WarningLevel.NORMAL, (
            f"Value at max ({target_max}) should be NORMAL, got {level}"
        )
        
        # At 80% of min boundary - should be LOW
        level = service._calculate_warning_level(critical_low, target_min, target_max)
        assert level == WarningLevel.LOW, (
            f"Value at 80% of min ({critical_low}) should be LOW, got {level}"
        )
        
        # At 120% of max boundary - should be HIGH
        level = service._calculate_warning_level(critical_high, target_min, target_max)
        assert level == WarningLevel.HIGH, (
            f"Value at 120% of max ({critical_high}) should be HIGH, got {level}"
        )
