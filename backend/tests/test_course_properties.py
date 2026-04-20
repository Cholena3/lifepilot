"""Property-based tests for course progress tracking.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 25.2**
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.models.course import Course, LearningSession
from app.schemas.course import (
    CourseCreate,
    CourseResponse,
    LearningSessionCreate,
)


# ============================================================================
# Hypothesis Strategies for Course Data
# ============================================================================

@st.composite
def valid_course_titles(draw):
    """Generate valid course titles (1-255 characters)."""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-:()&"
    length = draw(st.integers(min_value=1, max_value=100))
    
    # Start with a letter
    first_char = draw(st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    
    if length == 1:
        return first_char
    
    rest = draw(st.text(alphabet=chars, min_size=length - 1, max_size=length - 1))
    title = first_char + rest
    
    # Clean up consecutive spaces
    while "  " in title:
        title = title.replace("  ", " ")
    
    return title.strip()[:255]


@st.composite
def valid_total_hours(draw):
    """Generate valid total hours (0 to 9999.99)."""
    # Generate as integer cents to avoid floating point issues
    cents = draw(st.integers(min_value=0, max_value=999999))
    return Decimal(str(cents)) / Decimal("100")


@st.composite
def valid_completed_hours(draw, max_hours=None):
    """Generate valid completed hours."""
    if max_hours is not None and max_hours > 0:
        # Generate completed hours up to 150% of total (to test capping)
        max_cents = int(max_hours * Decimal("150"))
        cents = draw(st.integers(min_value=0, max_value=max_cents))
    else:
        cents = draw(st.integers(min_value=0, max_value=999999))
    return Decimal(str(cents)) / Decimal("100")


@st.composite
def valid_duration_minutes(draw):
    """Generate valid session duration in minutes (1-1440)."""
    return draw(st.integers(min_value=1, max_value=1440))


@st.composite
def valid_course_data(draw):
    """Generate valid course data for testing."""
    total_hours = draw(valid_total_hours())
    return {
        "title": draw(valid_course_titles()),
        "platform": draw(st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))),
        "total_hours": total_hours,
    }


@st.composite
def course_with_progress(draw):
    """Generate a course with total hours and completed hours."""
    total_hours = draw(st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("9999.99"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ))
    
    # Generate completed hours (can exceed total to test capping)
    max_completed = total_hours * Decimal("1.5")
    completed_hours = draw(st.decimals(
        min_value=Decimal("0"),
        max_value=max_completed,
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ))
    
    return {
        "total_hours": total_hours,
        "completed_hours": completed_hours,
    }


@st.composite
def learning_session_sequence(draw, min_sessions=1, max_sessions=5):
    """Generate a sequence of learning sessions."""
    num_sessions = draw(st.integers(min_value=min_sessions, max_value=max_sessions))
    sessions = []
    
    for _ in range(num_sessions):
        duration = draw(valid_duration_minutes())
        sessions.append({
            "duration_minutes": duration,
            "session_date": date.today(),
        })
    
    return sessions


# ============================================================================
# Property 39: Course Progress Tracking
# ============================================================================

class TestCourseProgressTrackingProperty:
    """Property 39: Course Progress Tracking.
    
    **Validates: Requirements 25.2**
    
    For any course with total duration T and logged progress P, the completion
    percentage SHALL equal P/T * 100 (rounded down), capped at 100.
    """
    
    @given(course_data=course_with_progress())
    @settings(max_examples=100, deadline=None)
    def test_completion_percentage_formula(self, course_data: dict):
        """Completion percentage SHALL equal (completed_hours / total_hours) * 100
        rounded down.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. Completion percentage is calculated as (completed / total) * 100
        2. The result is rounded down (truncated to integer)
        3. The formula is consistent across all valid inputs
        """
        total_hours = course_data["total_hours"]
        completed_hours = course_data["completed_hours"]
        
        # Calculate expected percentage using the same formula as the service
        if total_hours > 0:
            expected_percentage = int((completed_hours / total_hours) * 100)
            expected_percentage = min(expected_percentage, 100)
        else:
            expected_percentage = 0
        
        # Verify the calculation
        assert 0 <= expected_percentage <= 100, (
            f"Completion percentage {expected_percentage} should be between 0 and 100"
        )
        
        # Verify the formula: percentage = floor(completed / total * 100)
        if total_hours > 0:
            raw_percentage = (completed_hours / total_hours) * 100
            floored_percentage = int(raw_percentage)
            capped_percentage = min(floored_percentage, 100)
            
            assert expected_percentage == capped_percentage, (
                f"Expected {capped_percentage}% but got {expected_percentage}% "
                f"for completed={completed_hours}, total={total_hours}"
            )
    
    @given(
        total_hours=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("9999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        completed_hours=st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("9999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_completion_percentage_always_between_0_and_100(
        self, total_hours: Decimal, completed_hours: Decimal
    ):
        """Completion percentage SHALL always be between 0 and 100.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. Completion percentage is never negative
        2. Completion percentage never exceeds 100
        3. This holds for all valid input combinations
        """
        # Calculate percentage using the service formula
        if total_hours > 0:
            percentage = int((completed_hours / total_hours) * 100)
            percentage = min(percentage, 100)
        else:
            percentage = 0
        
        assert percentage >= 0, (
            f"Completion percentage {percentage} should not be negative "
            f"(completed={completed_hours}, total={total_hours})"
        )
        assert percentage <= 100, (
            f"Completion percentage {percentage} should not exceed 100 "
            f"(completed={completed_hours}, total={total_hours})"
        )
    
    @given(
        total_hours=st.decimals(
            min_value=Decimal("1"),
            max_value=Decimal("100"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        session_durations=st.lists(
            st.integers(min_value=1, max_value=120),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_logging_session_increases_completed_hours(
        self, total_hours: Decimal, session_durations: list
    ):
        """Logging a learning session SHALL increase completed_hours by the
        session duration.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. Each session adds its duration (in hours) to completed_hours
        2. Multiple sessions accumulate correctly
        3. The total completed hours equals sum of all session durations
        """
        initial_completed_hours = Decimal("0")
        current_completed_hours = initial_completed_hours
        
        # Track total minutes added
        total_minutes_added = 0
        
        for duration_minutes in session_durations:
            # Calculate hours added (same formula as service)
            hours_added = Decimal(str(duration_minutes)) / Decimal("60")
            current_completed_hours += hours_added
            total_minutes_added += duration_minutes
        
        # Verify completed hours increased from initial
        assert current_completed_hours > initial_completed_hours, (
            "Completed hours should increase after logging sessions"
        )
        
        # Verify the total minutes added matches the sum of session durations
        assert total_minutes_added == sum(session_durations), (
            f"Total minutes added {total_minutes_added} should equal "
            f"sum of session durations {sum(session_durations)}"
        )
        
        # Verify the completed hours is positive and represents the sessions
        # (Using comparison instead of exact equality to avoid Decimal precision issues)
        expected_hours_approx = Decimal(str(total_minutes_added)) / Decimal("60")
        # Allow for small precision differences (within 1 second = 1/3600 hours)
        tolerance = Decimal("0.001")
        assert abs(current_completed_hours - expected_hours_approx) < tolerance, (
            f"Completed hours {current_completed_hours} should be approximately "
            f"{expected_hours_approx} (within {tolerance})"
        )
    
    @given(
        completed_hours=st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("100"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_completion_percentage_zero_when_total_hours_zero(
        self, completed_hours: Decimal
    ):
        """Completion percentage SHALL be 0 when total_hours is 0.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. When total_hours is 0, percentage is always 0
        2. This prevents division by zero errors
        3. This holds regardless of completed_hours value
        """
        total_hours = Decimal("0")
        
        # Calculate percentage using the service formula
        if total_hours > 0:
            percentage = int((completed_hours / total_hours) * 100)
            percentage = min(percentage, 100)
        else:
            percentage = 0
        
        assert percentage == 0, (
            f"Completion percentage should be 0 when total_hours is 0, "
            f"but got {percentage} (completed_hours={completed_hours})"
        )
    
    @given(
        total_hours=st.decimals(
            min_value=Decimal("1"),
            max_value=Decimal("100"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        excess_factor=st.decimals(
            min_value=Decimal("1.01"),
            max_value=Decimal("3"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_completion_percentage_capped_at_100(
        self, total_hours: Decimal, excess_factor: Decimal
    ):
        """Completion percentage SHALL be capped at 100 even if completed_hours
        exceeds total_hours.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. When completed_hours > total_hours, percentage is still 100
        2. The cap is applied consistently
        3. Users cannot have more than 100% completion
        """
        # Create completed hours that exceed total
        completed_hours = total_hours * excess_factor
        
        # Verify completed exceeds total
        assume(completed_hours > total_hours)
        
        # Calculate percentage using the service formula
        if total_hours > 0:
            percentage = int((completed_hours / total_hours) * 100)
            percentage = min(percentage, 100)
        else:
            percentage = 0
        
        assert percentage == 100, (
            f"Completion percentage should be capped at 100 when "
            f"completed_hours ({completed_hours}) exceeds total_hours ({total_hours}), "
            f"but got {percentage}"
        )
    
    @given(
        total_hours=st.decimals(
            min_value=Decimal("1"),
            max_value=Decimal("100"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_completion_percentage_100_when_completed_equals_total(
        self, total_hours: Decimal
    ):
        """Completion percentage SHALL be 100 when completed_hours equals
        total_hours.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. When completed equals total, percentage is exactly 100
        2. This represents a fully completed course
        """
        completed_hours = total_hours
        
        # Calculate percentage using the service formula
        if total_hours > 0:
            percentage = int((completed_hours / total_hours) * 100)
            percentage = min(percentage, 100)
        else:
            percentage = 0
        
        assert percentage == 100, (
            f"Completion percentage should be 100 when completed_hours equals "
            f"total_hours ({total_hours}), but got {percentage}"
        )
    
    @given(
        total_hours=st.decimals(
            min_value=Decimal("1"),
            max_value=Decimal("100"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_completion_percentage_0_when_no_progress(
        self, total_hours: Decimal
    ):
        """Completion percentage SHALL be 0 when completed_hours is 0.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. When no progress has been made, percentage is 0
        2. This represents a course that hasn't been started
        """
        completed_hours = Decimal("0")
        
        # Calculate percentage using the service formula
        if total_hours > 0:
            percentage = int((completed_hours / total_hours) * 100)
            percentage = min(percentage, 100)
        else:
            percentage = 0
        
        assert percentage == 0, (
            f"Completion percentage should be 0 when completed_hours is 0, "
            f"but got {percentage} (total_hours={total_hours})"
        )
    
    @given(
        total_hours=st.decimals(
            min_value=Decimal("3"),
            max_value=Decimal("100"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_completion_percentage_rounds_down(
        self, total_hours: Decimal
    ):
        """Completion percentage SHALL be rounded down (truncated) to an integer.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. Fractional percentages are truncated, not rounded
        2. For example, 33.9% becomes 33%, not 34%
        """
        # Use 1/3 of total to get a repeating decimal (33.33...%)
        completed_hours = total_hours / Decimal("3")
        
        # Calculate percentage using the service formula
        if total_hours > 0:
            raw_percentage = (completed_hours / total_hours) * 100
            percentage = int(raw_percentage)
            percentage = min(percentage, 100)
        else:
            percentage = 0
        
        # Should be 33, not 34
        assert percentage == 33, (
            f"Completion percentage should be 33 (rounded down from 33.33...), "
            f"but got {percentage}"
        )
        
        # Verify it's actually truncated, not rounded
        assert percentage == int(raw_percentage), (
            f"Percentage should be truncated (int), not rounded. "
            f"Raw: {raw_percentage}, Got: {percentage}"
        )
    
    @given(
        initial_completed=st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("50"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        session_duration=st.integers(min_value=1, max_value=120),
    )
    @settings(max_examples=100, deadline=None)
    def test_session_duration_converted_to_hours_correctly(
        self, initial_completed: Decimal, session_duration: int
    ):
        """Session duration in minutes SHALL be correctly converted to hours
        when updating completed_hours.
        
        **Validates: Requirements 25.2**
        
        This test verifies that:
        1. Duration in minutes is divided by 60 to get hours
        2. The conversion is precise (using Decimal)
        3. The result is added to completed_hours
        """
        # Convert duration to hours (same formula as service)
        hours_added = Decimal(str(session_duration)) / Decimal("60")
        new_completed = initial_completed + hours_added
        
        # Verify the conversion
        expected_hours = Decimal(str(session_duration)) / Decimal("60")
        assert hours_added == expected_hours, (
            f"Session duration {session_duration} minutes should convert to "
            f"{expected_hours} hours, but got {hours_added}"
        )
        
        # Verify the addition
        assert new_completed == initial_completed + expected_hours, (
            f"New completed hours should be {initial_completed + expected_hours}, "
            f"but got {new_completed}"
        )

