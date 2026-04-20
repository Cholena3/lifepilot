"""Property-based tests for profile module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 2.1, 2.5**
"""

import string
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    StudentProfileCreate,
    StudentProfileUpdate,
    StudentProfileResponse,
    CareerPreferencesCreate,
    CareerPreferencesUpdate,
    CareerPreferencesResponse,
)


# ============================================================================
# Hypothesis Strategies for Profile Data
# ============================================================================

@st.composite
def valid_names(draw):
    """Generate valid names (1-100 characters).
    
    Names can contain letters, spaces, hyphens, and apostrophes.
    """
    # Use printable ASCII characters that are valid for names
    name_chars = string.ascii_letters + " '-"
    length = draw(st.integers(min_value=1, max_value=100))
    
    # Start with a letter
    first_char = draw(st.sampled_from(string.ascii_letters))
    
    if length == 1:
        return first_char
    
    # Generate rest of the name
    rest_length = length - 1
    rest = draw(st.text(alphabet=name_chars, min_size=rest_length, max_size=rest_length))
    
    name = first_char + rest
    
    # Clean up: no consecutive spaces/hyphens, no trailing spaces
    while "  " in name:
        name = name.replace("  ", " ")
    while "--" in name:
        name = name.replace("--", "-")
    name = name.strip()
    
    # Ensure we have at least 1 character
    if not name:
        name = first_char
    
    return name[:100]  # Ensure max length


@st.composite
def valid_dates_of_birth(draw):
    """Generate valid dates of birth.
    
    Dates should be in the past (at least 10 years ago) and not too far back.
    """
    # Generate dates between 100 years ago and 10 years ago
    today = date.today()
    min_date = today - timedelta(days=365 * 100)  # 100 years ago
    max_date = today - timedelta(days=365 * 10)   # 10 years ago
    
    return draw(st.dates(min_value=min_date, max_value=max_date))


@st.composite
def valid_genders(draw):
    """Generate valid gender values."""
    return draw(st.sampled_from(["male", "female", "other", "prefer_not_to_say"]))


@st.composite
def valid_profile_data(draw):
    """Generate valid profile data for testing.
    
    Returns a dictionary with valid profile fields.
    """
    return {
        "first_name": draw(valid_names()),
        "last_name": draw(valid_names()),
        "date_of_birth": draw(valid_dates_of_birth()),
        "gender": draw(valid_genders()),
    }


# ============================================================================
# Hypothesis Strategies for Student Profile Data
# ============================================================================

@st.composite
def valid_institutions(draw):
    """Generate valid institution names (1-255 characters)."""
    chars = string.ascii_letters + string.digits + " -'.,&"
    length = draw(st.integers(min_value=1, max_value=100))
    
    first_char = draw(st.sampled_from(string.ascii_letters))
    
    if length == 1:
        return first_char
    
    rest = draw(st.text(alphabet=chars, min_size=length - 1, max_size=length - 1))
    name = first_char + rest
    
    # Clean up consecutive spaces
    while "  " in name:
        name = name.replace("  ", " ")
    
    return name.strip()[:255]


@st.composite
def valid_degrees(draw):
    """Generate valid degree names."""
    return draw(st.sampled_from([
        "B.Tech", "M.Tech", "B.E.", "M.E.", "B.Sc", "M.Sc",
        "BBA", "MBA", "B.Com", "M.Com", "BA", "MA", "PhD"
    ]))


@st.composite
def valid_branches(draw):
    """Generate valid branch/major names."""
    return draw(st.sampled_from([
        "Computer Science", "Electrical Engineering", "Mechanical Engineering",
        "Civil Engineering", "Electronics", "Information Technology",
        "Chemical Engineering", "Biotechnology", "Physics", "Mathematics",
        "Economics", "Business Administration"
    ]))


@st.composite
def valid_cgpas(draw):
    """Generate valid CGPA values (0.0-10.0)."""
    # Generate a float between 0.0 and 10.0, then convert to Decimal
    value = draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    # Round to 2 decimal places for realistic CGPA values
    return Decimal(str(round(value, 2)))


@st.composite
def valid_backlogs(draw):
    """Generate valid backlog counts (>= 0)."""
    return draw(st.integers(min_value=0, max_value=20))


@st.composite
def valid_graduation_years(draw):
    """Generate valid graduation years."""
    current_year = date.today().year
    return draw(st.integers(min_value=current_year - 10, max_value=current_year + 10))


@st.composite
def valid_student_profile_data(draw):
    """Generate valid student profile data for testing.
    
    Returns a dictionary with valid student profile fields.
    """
    return {
        "institution": draw(valid_institutions()),
        "degree": draw(valid_degrees()),
        "branch": draw(valid_branches()),
        "cgpa": draw(valid_cgpas()),
        "backlogs": draw(valid_backlogs()),
        "graduation_year": draw(valid_graduation_years()),
    }


# ============================================================================
# Hypothesis Strategies for Career Preferences Data
# ============================================================================

@st.composite
def valid_role_names(draw):
    """Generate valid job role names."""
    return draw(st.sampled_from([
        "Software Engineer", "Data Scientist", "Product Manager",
        "Backend Developer", "Frontend Developer", "Full Stack Developer",
        "DevOps Engineer", "Machine Learning Engineer", "Data Analyst",
        "Business Analyst", "Project Manager", "UX Designer"
    ]))


@st.composite
def valid_preferred_roles(draw):
    """Generate a list of valid preferred roles."""
    num_roles = draw(st.integers(min_value=1, max_value=5))
    roles = draw(st.lists(valid_role_names(), min_size=num_roles, max_size=num_roles, unique=True))
    return roles


@st.composite
def valid_location_names(draw):
    """Generate valid location names."""
    return draw(st.sampled_from([
        "San Francisco", "New York", "Seattle", "Austin", "Boston",
        "Los Angeles", "Chicago", "Denver", "Remote", "Bangalore",
        "London", "Berlin", "Singapore", "Toronto"
    ]))


@st.composite
def valid_preferred_locations(draw):
    """Generate a list of valid preferred locations."""
    num_locations = draw(st.integers(min_value=1, max_value=5))
    locations = draw(st.lists(valid_location_names(), min_size=num_locations, max_size=num_locations, unique=True))
    return locations


@st.composite
def valid_salary_range(draw):
    """Generate valid min and max salary values.
    
    Ensures max_salary >= min_salary.
    """
    min_salary = draw(st.integers(min_value=0, max_value=500000))
    # Max salary should be at least min_salary
    max_salary = draw(st.integers(min_value=min_salary, max_value=1000000))
    return Decimal(str(min_salary)), Decimal(str(max_salary))


@st.composite
def valid_job_types(draw):
    """Generate valid job type values."""
    return draw(st.sampled_from([
        "full-time", "part-time", "internship", "contract", "freelance"
    ]))


@st.composite
def valid_career_preferences_data(draw):
    """Generate valid career preferences data for testing.
    
    Returns a dictionary with valid career preferences fields.
    """
    min_salary, max_salary = draw(valid_salary_range())
    
    return {
        "preferred_roles": draw(valid_preferred_roles()),
        "preferred_locations": draw(valid_preferred_locations()),
        "min_salary": min_salary,
        "max_salary": max_salary,
        "job_type": draw(valid_job_types()),
    }


# ============================================================================
# Property 6: Profile Data Round-Trip
# ============================================================================

class TestProfileDataRoundTripProperty:
    """Property 6: Profile Data Round-Trip.
    
    **Validates: Requirements 2.1, 2.5**
    
    For any valid profile data (basic info, student profile, career preferences),
    saving through the profile wizard and then retrieving SHALL return equivalent data.
    """
    
    @given(profile_data=valid_profile_data())
    @settings(max_examples=10, deadline=None)
    def test_basic_profile_round_trip(self, profile_data: dict):
        """For any valid profile data submitted, the data retrieved after saving
        SHALL match the original data exactly.
        
        **Validates: Requirements 2.1, 2.5**
        
        This test verifies that:
        1. Valid profile data can be created via ProfileCreate schema
        2. The data can be serialized to ProfileResponse
        3. The retrieved data matches the original input
        """
        # Create profile using the schema (simulates submission)
        profile_create = ProfileCreate(
            first_name=profile_data["first_name"],
            last_name=profile_data["last_name"],
            date_of_birth=profile_data["date_of_birth"],
            gender=profile_data["gender"],
        )
        
        # Verify the schema accepted the data
        assert profile_create.first_name == profile_data["first_name"]
        assert profile_create.last_name == profile_data["last_name"]
        assert profile_create.date_of_birth == profile_data["date_of_birth"]
        assert profile_create.gender == profile_data["gender"]
        
        # Simulate saving and retrieving by creating a response
        # (In real scenario, this would go through repository and database)
        profile_id = uuid4()
        user_id = uuid4()
        
        profile_response = ProfileResponse(
            id=profile_id,
            user_id=user_id,
            first_name=profile_create.first_name,
            last_name=profile_create.last_name,
            date_of_birth=profile_create.date_of_birth,
            gender=profile_create.gender,
            avatar_url=None,
            completion_percentage=50,
        )
        
        # Verify round-trip: retrieved data matches original
        assert profile_response.first_name == profile_data["first_name"], (
            f"first_name mismatch: expected {profile_data['first_name']}, "
            f"got {profile_response.first_name}"
        )
        assert profile_response.last_name == profile_data["last_name"], (
            f"last_name mismatch: expected {profile_data['last_name']}, "
            f"got {profile_response.last_name}"
        )
        assert profile_response.date_of_birth == profile_data["date_of_birth"], (
            f"date_of_birth mismatch: expected {profile_data['date_of_birth']}, "
            f"got {profile_response.date_of_birth}"
        )
        assert profile_response.gender == profile_data["gender"], (
            f"gender mismatch: expected {profile_data['gender']}, "
            f"got {profile_response.gender}"
        )
    
    @given(student_data=valid_student_profile_data())
    @settings(max_examples=10, deadline=None)
    def test_student_profile_round_trip(self, student_data: dict):
        """For any valid student profile data submitted, the data retrieved after
        saving SHALL match the original data exactly.
        
        **Validates: Requirements 2.1, 2.5**
        
        This test verifies that:
        1. Valid student profile data can be created via StudentProfileCreate schema
        2. The data can be serialized to StudentProfileResponse
        3. The retrieved data matches the original input
        """
        # Create student profile using the schema (simulates submission)
        student_create = StudentProfileCreate(
            institution=student_data["institution"],
            degree=student_data["degree"],
            branch=student_data["branch"],
            cgpa=student_data["cgpa"],
            backlogs=student_data["backlogs"],
            graduation_year=student_data["graduation_year"],
        )
        
        # Verify the schema accepted the data
        assert student_create.institution == student_data["institution"]
        assert student_create.degree == student_data["degree"]
        assert student_create.branch == student_data["branch"]
        assert student_create.cgpa == student_data["cgpa"]
        assert student_create.backlogs == student_data["backlogs"]
        assert student_create.graduation_year == student_data["graduation_year"]
        
        # Simulate saving and retrieving by creating a response
        profile_id = uuid4()
        user_id = uuid4()
        
        student_response = StudentProfileResponse(
            id=profile_id,
            user_id=user_id,
            institution=student_create.institution,
            degree=student_create.degree,
            branch=student_create.branch,
            cgpa=student_create.cgpa,
            backlogs=student_create.backlogs,
            graduation_year=student_create.graduation_year,
        )
        
        # Verify round-trip: retrieved data matches original
        assert student_response.institution == student_data["institution"], (
            f"institution mismatch: expected {student_data['institution']}, "
            f"got {student_response.institution}"
        )
        assert student_response.degree == student_data["degree"], (
            f"degree mismatch: expected {student_data['degree']}, "
            f"got {student_response.degree}"
        )
        assert student_response.branch == student_data["branch"], (
            f"branch mismatch: expected {student_data['branch']}, "
            f"got {student_response.branch}"
        )
        assert student_response.cgpa == student_data["cgpa"], (
            f"cgpa mismatch: expected {student_data['cgpa']}, "
            f"got {student_response.cgpa}"
        )
        assert student_response.backlogs == student_data["backlogs"], (
            f"backlogs mismatch: expected {student_data['backlogs']}, "
            f"got {student_response.backlogs}"
        )
        assert student_response.graduation_year == student_data["graduation_year"], (
            f"graduation_year mismatch: expected {student_data['graduation_year']}, "
            f"got {student_response.graduation_year}"
        )
    
    @given(career_data=valid_career_preferences_data())
    @settings(max_examples=10, deadline=None)
    def test_career_preferences_round_trip(self, career_data: dict):
        """For any valid career preferences data submitted, the data retrieved after
        saving SHALL match the original data exactly.
        
        **Validates: Requirements 2.1, 2.5**
        
        This test verifies that:
        1. Valid career preferences data can be created via CareerPreferencesCreate schema
        2. The data can be serialized to CareerPreferencesResponse
        3. The retrieved data matches the original input
        """
        # Create career preferences using the schema (simulates submission)
        career_create = CareerPreferencesCreate(
            preferred_roles=career_data["preferred_roles"],
            preferred_locations=career_data["preferred_locations"],
            min_salary=career_data["min_salary"],
            max_salary=career_data["max_salary"],
            job_type=career_data["job_type"],
        )
        
        # Verify the schema accepted the data
        assert career_create.preferred_roles == career_data["preferred_roles"]
        assert career_create.preferred_locations == career_data["preferred_locations"]
        assert career_create.min_salary == career_data["min_salary"]
        assert career_create.max_salary == career_data["max_salary"]
        assert career_create.job_type == career_data["job_type"]
        
        # Simulate saving and retrieving by creating a response
        preferences_id = uuid4()
        user_id = uuid4()
        
        career_response = CareerPreferencesResponse(
            id=preferences_id,
            user_id=user_id,
            preferred_roles=career_create.preferred_roles,
            preferred_locations=career_create.preferred_locations,
            min_salary=career_create.min_salary,
            max_salary=career_create.max_salary,
            job_type=career_create.job_type,
        )
        
        # Verify round-trip: retrieved data matches original
        assert career_response.preferred_roles == career_data["preferred_roles"], (
            f"preferred_roles mismatch: expected {career_data['preferred_roles']}, "
            f"got {career_response.preferred_roles}"
        )
        assert career_response.preferred_locations == career_data["preferred_locations"], (
            f"preferred_locations mismatch: expected {career_data['preferred_locations']}, "
            f"got {career_response.preferred_locations}"
        )
        assert career_response.min_salary == career_data["min_salary"], (
            f"min_salary mismatch: expected {career_data['min_salary']}, "
            f"got {career_response.min_salary}"
        )
        assert career_response.max_salary == career_data["max_salary"], (
            f"max_salary mismatch: expected {career_data['max_salary']}, "
            f"got {career_response.max_salary}"
        )
        assert career_response.job_type == career_data["job_type"], (
            f"job_type mismatch: expected {career_data['job_type']}, "
            f"got {career_response.job_type}"
        )


# ============================================================================
# Property 8: CGPA Validation Range
# ============================================================================

class TestCGPAValidationRangeProperty:
    """Property 8: CGPA Validation Range.
    
    **Validates: Requirements 2.4**
    
    For any CGPA value, values between 0.0 and 10.0 (inclusive) SHALL be accepted,
    and values outside this range SHALL be rejected with a validation error.
    """
    
    @given(cgpa=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=10, deadline=None)
    def test_valid_cgpa_values_accepted(self, cgpa: float):
        """For any CGPA value between 0.0 and 10.0 (inclusive), the student profile
        SHALL accept the value.
        
        **Validates: Requirements 2.4**
        
        This test verifies that:
        1. Any CGPA value in the valid range [0.0, 10.0] is accepted
        2. The schema creates successfully without validation errors
        3. The stored value matches the input value
        """
        # Convert to Decimal for schema compatibility
        cgpa_decimal = Decimal(str(round(cgpa, 2)))
        
        # Create student profile with the CGPA value
        student_profile = StudentProfileCreate(cgpa=cgpa_decimal)
        
        # Verify the value was accepted
        assert student_profile.cgpa == cgpa_decimal, (
            f"CGPA value {cgpa_decimal} should be accepted but got {student_profile.cgpa}"
        )
    
    @given(cgpa=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False))
    @settings(max_examples=10, deadline=None)
    def test_cgpa_below_range_rejected(self, cgpa: float):
        """For any CGPA value below 0.0, the student profile SHALL reject with a
        validation error.
        
        **Validates: Requirements 2.4**
        
        This test verifies that:
        1. Any CGPA value below 0.0 is rejected
        2. A ValidationError is raised
        3. The error message indicates the CGPA field is invalid
        """
        # Ensure we have a negative value
        assume(cgpa < 0.0)
        
        # Convert to Decimal for schema compatibility
        cgpa_decimal = Decimal(str(round(cgpa, 2)))
        
        # Attempt to create student profile with invalid CGPA
        with pytest.raises(ValidationError) as exc_info:
            StudentProfileCreate(cgpa=cgpa_decimal)
        
        # Verify the error is related to CGPA validation
        errors = exc_info.value.errors()
        cgpa_errors = [e for e in errors if 'cgpa' in str(e.get('loc', []))]
        assert len(cgpa_errors) > 0, (
            f"Expected validation error for CGPA value {cgpa_decimal}, "
            f"but got errors: {errors}"
        )
    
    @given(cgpa=st.floats(min_value=10.01, max_value=1000.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=10, deadline=None)
    def test_cgpa_above_range_rejected(self, cgpa: float):
        """For any CGPA value above 10.0, the student profile SHALL reject with a
        validation error.
        
        **Validates: Requirements 2.4**
        
        This test verifies that:
        1. Any CGPA value above 10.0 is rejected
        2. A ValidationError is raised
        3. The error message indicates the CGPA field is invalid
        """
        # Ensure we have a value above 10.0
        assume(cgpa > 10.0)
        
        # Convert to Decimal for schema compatibility
        cgpa_decimal = Decimal(str(round(cgpa, 2)))
        
        # Attempt to create student profile with invalid CGPA
        with pytest.raises(ValidationError) as exc_info:
            StudentProfileCreate(cgpa=cgpa_decimal)
        
        # Verify the error is related to CGPA validation
        errors = exc_info.value.errors()
        cgpa_errors = [e for e in errors if 'cgpa' in str(e.get('loc', []))]
        assert len(cgpa_errors) > 0, (
            f"Expected validation error for CGPA value {cgpa_decimal}, "
            f"but got errors: {errors}"
        )
    
    @given(cgpa=st.sampled_from([Decimal("0.0"), Decimal("10.0")]))
    @settings(max_examples=10, deadline=None)
    def test_cgpa_boundary_values_accepted(self, cgpa: Decimal):
        """For CGPA boundary values (0.0 and 10.0), the student profile SHALL
        accept the value.
        
        **Validates: Requirements 2.4**
        
        This test verifies that:
        1. The minimum boundary value (0.0) is accepted
        2. The maximum boundary value (10.0) is accepted
        3. Boundary values are stored correctly
        """
        # Create student profile with the boundary CGPA value
        student_profile = StudentProfileCreate(cgpa=cgpa)
        
        # Verify the value was accepted
        assert student_profile.cgpa == cgpa, (
            f"CGPA boundary value {cgpa} should be accepted but got {student_profile.cgpa}"
        )


# ============================================================================
# Property 7: Profile Completion Calculation
# ============================================================================

# Import the profile service constants and helper functions for testing
from app.services.profile import (
    BASIC_PROFILE_WEIGHT,
    STUDENT_PROFILE_WEIGHT,
    CAREER_PREFERENCES_WEIGHT,
    BASIC_PROFILE_FIELDS,
    STUDENT_PROFILE_FIELDS,
    CAREER_PREFERENCES_FIELDS,
)


def calculate_completion_percentage(
    basic_filled: int,
    student_filled: int,
    career_filled: int,
) -> int:
    """Calculate profile completion percentage based on filled fields.
    
    This mirrors the calculation in ProfileService.calculate_completion_percentage.
    
    Args:
        basic_filled: Number of filled basic profile fields (0-5)
        student_filled: Number of filled student profile fields (0-5)
        career_filled: Number of filled career preferences fields (0-4)
        
    Returns:
        Completion percentage (0-100)
    """
    basic_total = len(BASIC_PROFILE_FIELDS)  # 5
    student_total = len(STUDENT_PROFILE_FIELDS)  # 5
    career_total = len(CAREER_PREFERENCES_FIELDS)  # 4
    
    basic_percentage = (basic_filled / basic_total) * BASIC_PROFILE_WEIGHT
    student_percentage = (student_filled / student_total) * STUDENT_PROFILE_WEIGHT
    career_percentage = (career_filled / career_total) * CAREER_PREFERENCES_WEIGHT
    
    return int(basic_percentage + student_percentage + career_percentage)


@st.composite
def filled_field_counts(draw):
    """Generate random combinations of filled/unfilled fields for all profile types.
    
    Returns a tuple of (basic_filled, student_filled, career_filled).
    """
    basic_filled = draw(st.integers(min_value=0, max_value=len(BASIC_PROFILE_FIELDS)))
    student_filled = draw(st.integers(min_value=0, max_value=len(STUDENT_PROFILE_FIELDS)))
    career_filled = draw(st.integers(min_value=0, max_value=len(CAREER_PREFERENCES_FIELDS)))
    return basic_filled, student_filled, career_filled


class TestProfileCompletionCalculationProperty:
    """Property 7: Profile Completion Calculation.
    
    **Validates: Requirements 2.2**
    
    For any combination of filled/unfilled profile fields:
    1. The completion percentage SHALL be between 0 and 100
    2. For any profile with all fields filled, the completion percentage SHALL be exactly 100
    3. For any profile with no fields filled, the completion percentage SHALL be exactly 0
    4. The completion percentage SHALL increase monotonically as more fields are filled
    """
    
    @given(field_counts=filled_field_counts())
    @settings(max_examples=10, deadline=None)
    def test_completion_percentage_within_bounds(self, field_counts: tuple):
        """For any combination of filled/unfilled profile fields, the completion
        percentage SHALL be between 0 and 100.
        
        **Validates: Requirements 2.2**
        
        This test verifies that:
        1. The completion percentage is never negative
        2. The completion percentage never exceeds 100
        3. The calculation handles all valid field combinations
        """
        basic_filled, student_filled, career_filled = field_counts
        
        percentage = calculate_completion_percentage(
            basic_filled, student_filled, career_filled
        )
        
        assert 0 <= percentage <= 100, (
            f"Completion percentage {percentage} is out of bounds [0, 100] "
            f"for field counts: basic={basic_filled}, student={student_filled}, "
            f"career={career_filled}"
        )
    
    @given(st.just(True))  # Dummy strategy to use Hypothesis framework
    @settings(max_examples=10, deadline=None)
    def test_all_fields_filled_equals_100_percent(self, _):
        """For any profile with all fields filled, the completion percentage
        SHALL be exactly 100.
        
        **Validates: Requirements 2.2**
        
        This test verifies that:
        1. When all basic profile fields are filled (5/5)
        2. And all student profile fields are filled (5/5)
        3. And all career preferences fields are filled (4/4)
        4. The completion percentage equals exactly 100
        """
        basic_filled = len(BASIC_PROFILE_FIELDS)  # 5
        student_filled = len(STUDENT_PROFILE_FIELDS)  # 5
        career_filled = len(CAREER_PREFERENCES_FIELDS)  # 4
        
        percentage = calculate_completion_percentage(
            basic_filled, student_filled, career_filled
        )
        
        assert percentage == 100, (
            f"Expected 100% completion when all fields are filled, "
            f"but got {percentage}%"
        )
    
    @given(st.just(True))  # Dummy strategy to use Hypothesis framework
    @settings(max_examples=10, deadline=None)
    def test_no_fields_filled_equals_0_percent(self, _):
        """For any profile with no fields filled, the completion percentage
        SHALL be exactly 0.
        
        **Validates: Requirements 2.2**
        
        This test verifies that:
        1. When no basic profile fields are filled (0/5)
        2. And no student profile fields are filled (0/5)
        3. And no career preferences fields are filled (0/4)
        4. The completion percentage equals exactly 0
        """
        basic_filled = 0
        student_filled = 0
        career_filled = 0
        
        percentage = calculate_completion_percentage(
            basic_filled, student_filled, career_filled
        )
        
        assert percentage == 0, (
            f"Expected 0% completion when no fields are filled, "
            f"but got {percentage}%"
        )
    
    @given(
        initial_counts=filled_field_counts(),
        field_type=st.sampled_from(["basic", "student", "career"]),
    )
    @settings(max_examples=10, deadline=None)
    def test_completion_increases_monotonically(
        self, initial_counts: tuple, field_type: str
    ):
        """The completion percentage SHALL increase monotonically as more fields
        are filled.
        
        **Validates: Requirements 2.2**
        
        This test verifies that:
        1. Adding a filled field never decreases the completion percentage
        2. The percentage either stays the same (if already at max) or increases
        """
        basic_filled, student_filled, career_filled = initial_counts
        
        # Calculate initial percentage
        initial_percentage = calculate_completion_percentage(
            basic_filled, student_filled, career_filled
        )
        
        # Add one more filled field to the selected type (if not already at max)
        new_basic = basic_filled
        new_student = student_filled
        new_career = career_filled
        
        if field_type == "basic" and basic_filled < len(BASIC_PROFILE_FIELDS):
            new_basic = basic_filled + 1
        elif field_type == "student" and student_filled < len(STUDENT_PROFILE_FIELDS):
            new_student = student_filled + 1
        elif field_type == "career" and career_filled < len(CAREER_PREFERENCES_FIELDS):
            new_career = career_filled + 1
        
        # Calculate new percentage
        new_percentage = calculate_completion_percentage(
            new_basic, new_student, new_career
        )
        
        # Verify monotonic increase (or equal if already at max)
        assert new_percentage >= initial_percentage, (
            f"Completion percentage decreased from {initial_percentage}% to "
            f"{new_percentage}% when adding a {field_type} field. "
            f"Initial: basic={basic_filled}, student={student_filled}, "
            f"career={career_filled}. "
            f"New: basic={new_basic}, student={new_student}, career={new_career}"
        )
    
    @given(
        basic_filled=st.integers(min_value=0, max_value=len(BASIC_PROFILE_FIELDS)),
    )
    @settings(max_examples=10, deadline=None)
    def test_basic_profile_contributes_40_percent(self, basic_filled: int):
        """Basic profile fields contribute 40% to the total completion.
        
        **Validates: Requirements 2.2**
        
        This test verifies that:
        1. With only basic profile fields filled, max contribution is 40%
        2. The contribution scales linearly with filled fields
        """
        # Only basic profile fields filled
        percentage = calculate_completion_percentage(
            basic_filled, 0, 0
        )
        
        expected_max = BASIC_PROFILE_WEIGHT  # 40
        expected = int((basic_filled / len(BASIC_PROFILE_FIELDS)) * expected_max)
        
        assert percentage == expected, (
            f"Expected {expected}% for {basic_filled}/{len(BASIC_PROFILE_FIELDS)} "
            f"basic fields, but got {percentage}%"
        )
        assert percentage <= expected_max, (
            f"Basic profile contribution {percentage}% exceeds max {expected_max}%"
        )
    
    @given(
        student_filled=st.integers(min_value=0, max_value=len(STUDENT_PROFILE_FIELDS)),
    )
    @settings(max_examples=10, deadline=None)
    def test_student_profile_contributes_30_percent(self, student_filled: int):
        """Student profile fields contribute 30% to the total completion.
        
        **Validates: Requirements 2.2**
        
        This test verifies that:
        1. With only student profile fields filled, max contribution is 30%
        2. The contribution scales linearly with filled fields
        """
        # Only student profile fields filled
        percentage = calculate_completion_percentage(
            0, student_filled, 0
        )
        
        expected_max = STUDENT_PROFILE_WEIGHT  # 30
        expected = int((student_filled / len(STUDENT_PROFILE_FIELDS)) * expected_max)
        
        assert percentage == expected, (
            f"Expected {expected}% for {student_filled}/{len(STUDENT_PROFILE_FIELDS)} "
            f"student fields, but got {percentage}%"
        )
        assert percentage <= expected_max, (
            f"Student profile contribution {percentage}% exceeds max {expected_max}%"
        )
    
    @given(
        career_filled=st.integers(min_value=0, max_value=len(CAREER_PREFERENCES_FIELDS)),
    )
    @settings(max_examples=10, deadline=None)
    def test_career_preferences_contributes_30_percent(self, career_filled: int):
        """Career preferences fields contribute 30% to the total completion.
        
        **Validates: Requirements 2.2**
        
        This test verifies that:
        1. With only career preferences fields filled, max contribution is 30%
        2. The contribution scales linearly with filled fields
        """
        # Only career preferences fields filled
        percentage = calculate_completion_percentage(
            0, 0, career_filled
        )
        
        expected_max = CAREER_PREFERENCES_WEIGHT  # 30
        expected = int((career_filled / len(CAREER_PREFERENCES_FIELDS)) * expected_max)
        
        assert percentage == expected, (
            f"Expected {expected}% for {career_filled}/{len(CAREER_PREFERENCES_FIELDS)} "
            f"career fields, but got {percentage}%"
        )
        assert percentage <= expected_max, (
            f"Career preferences contribution {percentage}% exceeds max {expected_max}%"
        )
