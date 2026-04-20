"""Tests for profile module.

Validates: Requirements 2.1, 2.4, 2.5
"""

from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.schemas.profile import (
    CareerPreferencesCreate,
    CareerPreferencesResponse,
    CareerPreferencesUpdate,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.services.auth import create_tokens


# Schema validation tests

class TestProfileSchemas:
    """Tests for profile schema validation."""
    
    def test_profile_create_valid(self):
        """Test valid profile creation schema."""
        data = ProfileCreate(
            first_name="John",
            last_name="Doe",
            gender="male",
        )
        assert data.first_name == "John"
        assert data.last_name == "Doe"
        assert data.gender == "male"
    
    def test_profile_create_empty(self):
        """Test profile creation with no data."""
        data = ProfileCreate()
        assert data.first_name is None
        assert data.last_name is None
    
    def test_student_profile_cgpa_valid(self):
        """Test valid CGPA values.
        
        Validates: Requirements 2.4
        """
        # Test boundary values
        data_min = StudentProfileCreate(cgpa=Decimal("0.0"))
        assert data_min.cgpa == Decimal("0.0")
        
        data_max = StudentProfileCreate(cgpa=Decimal("10.0"))
        assert data_max.cgpa == Decimal("10.0")
        
        data_mid = StudentProfileCreate(cgpa=Decimal("7.5"))
        assert data_mid.cgpa == Decimal("7.5")
    
    def test_student_profile_cgpa_invalid_below_range(self):
        """Test CGPA below valid range.
        
        Validates: Requirements 2.4
        """
        with pytest.raises(ValidationError) as exc_info:
            StudentProfileCreate(cgpa=Decimal("-0.1"))
        
        # Verify the error is about CGPA being out of range
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("cgpa",)
        assert "greater_than_equal" in errors[0]["type"]
    
    def test_student_profile_cgpa_invalid_above_range(self):
        """Test CGPA above valid range.
        
        Validates: Requirements 2.4
        """
        with pytest.raises(ValidationError) as exc_info:
            StudentProfileCreate(cgpa=Decimal("10.1"))
        
        # Verify the error is about CGPA being out of range
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("cgpa",)
        assert "less_than_equal" in errors[0]["type"]
    
    def test_career_preferences_valid(self):
        """Test valid career preferences.
        
        Validates: Requirements 2.5
        """
        data = CareerPreferencesCreate(
            preferred_roles=["Software Engineer", "Data Scientist"],
            preferred_locations=["San Francisco", "Remote"],
            min_salary=Decimal("80000"),
            max_salary=Decimal("150000"),
            job_type="full-time",
        )
        assert data.preferred_roles == ["Software Engineer", "Data Scientist"]
        assert data.min_salary == Decimal("80000")
        assert data.max_salary == Decimal("150000")
    
    def test_career_preferences_salary_range_invalid(self):
        """Test invalid salary range (max < min).
        
        Validates: Requirements 2.5
        """
        with pytest.raises(ValueError, match="max_salary must be greater than or equal to min_salary"):
            CareerPreferencesCreate(
                min_salary=Decimal("100000"),
                max_salary=Decimal("50000"),
            )


# Endpoint tests

class TestProfileEndpoints:
    """Tests for profile API endpoints."""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def auth_headers(self, mock_user):
        """Create valid auth headers using real JWT tokens."""
        tokens = create_tokens(mock_user.id, mock_user.email)
        return {"Authorization": f"Bearer {tokens.access_token}"}
    
    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, client: AsyncClient, mock_user, auth_headers):
        """Test getting profile when it doesn't exist."""
        from app.core.exceptions import NotFoundError
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.profile.ProfileRepository") as mock_profile_repo_class:
                mock_profile_repo = MagicMock()
                mock_profile_repo.get_profile_by_user_id = AsyncMock(return_value=None)
                mock_profile_repo_class.return_value = mock_profile_repo
                
                response = await client.get(
                    "/api/v1/profile",
                    headers=auth_headers,
                )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_profile_success(self, client: AsyncClient, mock_user, auth_headers):
        """Test updating profile successfully.
        
        Validates: Requirements 2.1
        """
        profile_id = uuid4()
        
        # Create a mock profile model
        mock_profile = MagicMock()
        mock_profile.id = profile_id
        mock_profile.user_id = mock_user.id
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.gender = "male"
        mock_profile.date_of_birth = None
        mock_profile.avatar_url = None
        mock_profile.completion_percentage = 30
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.profile.ProfileRepository") as mock_profile_repo_class:
                mock_profile_repo = MagicMock()
                mock_profile_repo.get_profile_by_user_id = AsyncMock(return_value=None)
                mock_profile_repo.create_profile = AsyncMock(return_value=mock_profile)
                mock_profile_repo.update_profile = AsyncMock(return_value=mock_profile)
                mock_profile_repo.update_completion_percentage = AsyncMock(return_value=mock_profile)
                mock_profile_repo_class.return_value = mock_profile_repo
                
                with patch("app.services.profile.StudentProfileRepository") as mock_student_repo_class:
                    mock_student_repo = MagicMock()
                    mock_student_repo.get_student_profile_by_user_id = AsyncMock(return_value=None)
                    mock_student_repo_class.return_value = mock_student_repo
                    
                    with patch("app.services.profile.CareerPreferencesRepository") as mock_career_repo_class:
                        mock_career_repo = MagicMock()
                        mock_career_repo.get_career_preferences_by_user_id = AsyncMock(return_value=None)
                        mock_career_repo_class.return_value = mock_career_repo
                        
                        response = await client.put(
                            "/api/v1/profile",
                            headers=auth_headers,
                            json={
                                "first_name": "John",
                                "last_name": "Doe",
                                "gender": "male",
                            },
                        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["gender"] == "male"
    
    @pytest.mark.asyncio
    async def test_get_student_profile_not_found(self, client: AsyncClient, mock_user, auth_headers):
        """Test getting student profile when it doesn't exist."""
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.profile.StudentProfileRepository") as mock_student_repo_class:
                mock_student_repo = MagicMock()
                mock_student_repo.get_student_profile_by_user_id = AsyncMock(return_value=None)
                mock_student_repo_class.return_value = mock_student_repo
                
                response = await client.get(
                    "/api/v1/profile/student",
                    headers=auth_headers,
                )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_student_profile_success(self, client: AsyncClient, mock_user, auth_headers):
        """Test updating student profile successfully.
        
        Validates: Requirements 2.1, 2.4
        """
        profile_id = uuid4()
        
        # Create a mock student profile model
        mock_student_profile = MagicMock()
        mock_student_profile.id = profile_id
        mock_student_profile.user_id = mock_user.id
        mock_student_profile.institution = "MIT"
        mock_student_profile.degree = "B.Tech"
        mock_student_profile.branch = "Computer Science"
        mock_student_profile.cgpa = Decimal("8.5")
        mock_student_profile.backlogs = 0
        mock_student_profile.graduation_year = 2024
        
        # Create a mock profile model for completion percentage update
        mock_profile = MagicMock()
        mock_profile.id = uuid4()
        mock_profile.user_id = mock_user.id
        mock_profile.first_name = None
        mock_profile.last_name = None
        mock_profile.date_of_birth = None
        mock_profile.gender = None
        mock_profile.avatar_url = None
        mock_profile.completion_percentage = 30
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.profile.StudentProfileRepository") as mock_student_repo_class:
                mock_student_repo = MagicMock()
                mock_student_repo.get_student_profile_by_user_id = AsyncMock(return_value=None)
                mock_student_repo.create_student_profile = AsyncMock(return_value=mock_student_profile)
                mock_student_repo.update_student_profile = AsyncMock(return_value=mock_student_profile)
                mock_student_repo_class.return_value = mock_student_repo
                
                with patch("app.services.profile.ProfileRepository") as mock_profile_repo_class:
                    mock_profile_repo = MagicMock()
                    mock_profile_repo.get_profile_by_user_id = AsyncMock(return_value=None)
                    mock_profile_repo.create_profile = AsyncMock(return_value=mock_profile)
                    mock_profile_repo.update_completion_percentage = AsyncMock(return_value=mock_profile)
                    mock_profile_repo_class.return_value = mock_profile_repo
                    
                    with patch("app.services.profile.CareerPreferencesRepository") as mock_career_repo_class:
                        mock_career_repo = MagicMock()
                        mock_career_repo.get_career_preferences_by_user_id = AsyncMock(return_value=None)
                        mock_career_repo_class.return_value = mock_career_repo
                        
                        response = await client.put(
                            "/api/v1/profile/student",
                            headers=auth_headers,
                            json={
                                "institution": "MIT",
                                "degree": "B.Tech",
                                "branch": "Computer Science",
                                "cgpa": "8.5",
                                "graduation_year": 2024,
                            },
                        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["institution"] == "MIT"
        assert data["degree"] == "B.Tech"
        assert data["cgpa"] == "8.5"
    
    @pytest.mark.asyncio
    async def test_update_student_profile_invalid_cgpa(self, client: AsyncClient, mock_user, auth_headers):
        """Test updating student profile with invalid CGPA.
        
        Validates: Requirements 2.4
        """
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            response = await client.put(
                "/api/v1/profile/student",
                headers=auth_headers,
                json={"cgpa": "11.0"},
            )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_career_preferences_not_found(self, client: AsyncClient, mock_user, auth_headers):
        """Test getting career preferences when they don't exist."""
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.profile.CareerPreferencesRepository") as mock_career_repo_class:
                mock_career_repo = MagicMock()
                mock_career_repo.get_career_preferences_by_user_id = AsyncMock(return_value=None)
                mock_career_repo_class.return_value = mock_career_repo
                
                response = await client.get(
                    "/api/v1/profile/career",
                    headers=auth_headers,
                )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_career_preferences_success(self, client: AsyncClient, mock_user, auth_headers):
        """Test updating career preferences successfully.
        
        Validates: Requirements 2.5
        """
        preferences_id = uuid4()
        
        # Create a mock career preferences model
        mock_career_prefs = MagicMock()
        mock_career_prefs.id = preferences_id
        mock_career_prefs.user_id = mock_user.id
        mock_career_prefs.preferred_roles = ["Software Engineer", "Backend Developer"]
        mock_career_prefs.preferred_locations = ["San Francisco", "New York"]
        mock_career_prefs.min_salary = Decimal("80000")
        mock_career_prefs.max_salary = Decimal("150000")
        mock_career_prefs.job_type = "full-time"
        
        # Create a mock profile model for completion percentage update
        mock_profile = MagicMock()
        mock_profile.id = uuid4()
        mock_profile.user_id = mock_user.id
        mock_profile.first_name = None
        mock_profile.last_name = None
        mock_profile.date_of_birth = None
        mock_profile.gender = None
        mock_profile.avatar_url = None
        mock_profile.completion_percentage = 30
        
        with patch("app.core.dependencies.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            with patch("app.services.profile.CareerPreferencesRepository") as mock_career_repo_class:
                mock_career_repo = MagicMock()
                mock_career_repo.get_career_preferences_by_user_id = AsyncMock(return_value=None)
                mock_career_repo.create_career_preferences = AsyncMock(return_value=mock_career_prefs)
                mock_career_repo.update_career_preferences = AsyncMock(return_value=mock_career_prefs)
                mock_career_repo_class.return_value = mock_career_repo
                
                with patch("app.services.profile.ProfileRepository") as mock_profile_repo_class:
                    mock_profile_repo = MagicMock()
                    mock_profile_repo.get_profile_by_user_id = AsyncMock(return_value=None)
                    mock_profile_repo.create_profile = AsyncMock(return_value=mock_profile)
                    mock_profile_repo.update_completion_percentage = AsyncMock(return_value=mock_profile)
                    mock_profile_repo_class.return_value = mock_profile_repo
                    
                    with patch("app.services.profile.StudentProfileRepository") as mock_student_repo_class:
                        mock_student_repo = MagicMock()
                        mock_student_repo.get_student_profile_by_user_id = AsyncMock(return_value=None)
                        mock_student_repo_class.return_value = mock_student_repo
                        
                        response = await client.put(
                            "/api/v1/profile/career",
                            headers=auth_headers,
                            json={
                                "preferred_roles": ["Software Engineer", "Backend Developer"],
                                "preferred_locations": ["San Francisco", "New York"],
                                "min_salary": "80000",
                                "max_salary": "150000",
                                "job_type": "full-time",
                            },
                        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["preferred_roles"] == ["Software Engineer", "Backend Developer"]
        assert data["preferred_locations"] == ["San Francisco", "New York"]
        assert data["min_salary"] == "80000"
        assert data["max_salary"] == "150000"
        assert data["job_type"] == "full-time"
    
    @pytest.mark.asyncio
    async def test_profile_requires_authentication(self, client: AsyncClient):
        """Test that profile endpoints require authentication."""
        # Test all profile endpoints without auth
        response = await client.get("/api/v1/profile")
        assert response.status_code == 403
        
        response = await client.put("/api/v1/profile", json={})
        assert response.status_code == 403
        
        response = await client.get("/api/v1/profile/student")
        assert response.status_code == 403
        
        response = await client.put("/api/v1/profile/student", json={})
        assert response.status_code == 403
        
        response = await client.get("/api/v1/profile/career")
        assert response.status_code == 403
        
        response = await client.put("/api/v1/profile/career", json={})
        assert response.status_code == 403


class TestProfileService:
    """Tests for profile service functions."""
    
    def test_profile_response_from_attributes(self):
        """Test ProfileResponse can be created from model attributes."""
        profile_id = uuid4()
        user_id = uuid4()
        
        response = ProfileResponse(
            id=profile_id,
            user_id=user_id,
            first_name="John",
            last_name="Doe",
            date_of_birth=None,
            gender="male",
            avatar_url=None,
            completion_percentage=50,
        )
        
        assert response.id == profile_id
        assert response.user_id == user_id
        assert response.first_name == "John"
        assert response.completion_percentage == 50
    
    def test_student_profile_response_from_attributes(self):
        """Test StudentProfileResponse can be created from model attributes."""
        profile_id = uuid4()
        user_id = uuid4()
        
        response = StudentProfileResponse(
            id=profile_id,
            user_id=user_id,
            institution="MIT",
            degree="B.Tech",
            branch="Computer Science",
            cgpa=Decimal("8.5"),
            backlogs=0,
            graduation_year=2024,
        )
        
        assert response.id == profile_id
        assert response.institution == "MIT"
        assert response.cgpa == Decimal("8.5")
    
    def test_career_preferences_response_from_attributes(self):
        """Test CareerPreferencesResponse can be created from model attributes."""
        preferences_id = uuid4()
        user_id = uuid4()
        
        response = CareerPreferencesResponse(
            id=preferences_id,
            user_id=user_id,
            preferred_roles=["Software Engineer"],
            preferred_locations=["Remote"],
            min_salary=Decimal("80000"),
            max_salary=Decimal("150000"),
            job_type="full-time",
        )
        
        assert response.id == preferences_id
        assert response.preferred_roles == ["Software Engineer"]
        assert response.min_salary == Decimal("80000")


class TestProfileCompletionCalculation:
    """Tests for profile completion percentage calculation.
    
    Validates: Requirements 2.2, 2.3
    """
    
    def test_is_field_filled_with_none(self):
        """Test that None values are not considered filled."""
        from app.services.profile import ProfileService
        
        service = ProfileService(db=MagicMock())
        assert service._is_field_filled(None) is False
    
    def test_is_field_filled_with_empty_string(self):
        """Test that empty strings are not considered filled."""
        from app.services.profile import ProfileService
        
        service = ProfileService(db=MagicMock())
        assert service._is_field_filled("") is False
        assert service._is_field_filled("   ") is False
    
    def test_is_field_filled_with_empty_list(self):
        """Test that empty lists are not considered filled."""
        from app.services.profile import ProfileService
        
        service = ProfileService(db=MagicMock())
        assert service._is_field_filled([]) is False
    
    def test_is_field_filled_with_valid_values(self):
        """Test that valid values are considered filled."""
        from app.services.profile import ProfileService
        
        service = ProfileService(db=MagicMock())
        assert service._is_field_filled("John") is True
        assert service._is_field_filled(["Software Engineer"]) is True
        assert service._is_field_filled(Decimal("8.5")) is True
        assert service._is_field_filled(0) is True  # 0 is a valid value
        assert service._is_field_filled(2024) is True
    
    def test_count_filled_fields_with_none_model(self):
        """Test counting filled fields when model is None."""
        from app.services.profile import ProfileService, BASIC_PROFILE_FIELDS
        
        service = ProfileService(db=MagicMock())
        count = service._count_filled_fields(None, BASIC_PROFILE_FIELDS)
        assert count == 0
    
    def test_count_filled_fields_with_partial_data(self):
        """Test counting filled fields with partial data."""
        from app.services.profile import ProfileService, BASIC_PROFILE_FIELDS
        
        service = ProfileService(db=MagicMock())
        
        mock_profile = MagicMock()
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.date_of_birth = None
        mock_profile.gender = "male"
        mock_profile.avatar_url = None
        
        count = service._count_filled_fields(mock_profile, BASIC_PROFILE_FIELDS)
        assert count == 3  # first_name, last_name, gender
    
    def test_count_filled_fields_with_all_data(self):
        """Test counting filled fields with all data filled."""
        from app.services.profile import ProfileService, BASIC_PROFILE_FIELDS
        from datetime import date
        
        service = ProfileService(db=MagicMock())
        
        mock_profile = MagicMock()
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.date_of_birth = date(1995, 6, 15)
        mock_profile.gender = "male"
        mock_profile.avatar_url = "https://example.com/avatar.jpg"
        
        count = service._count_filled_fields(mock_profile, BASIC_PROFILE_FIELDS)
        assert count == 5  # All fields filled
    
    def test_check_completion_badge_at_100_percent(self):
        """Test that completion badge is awarded at 100%.
        
        Validates: Requirements 2.3
        """
        from app.services.profile import ProfileService
        
        service = ProfileService(db=MagicMock())
        assert service.check_completion_badge(100) is True
    
    def test_check_completion_badge_below_100_percent(self):
        """Test that completion badge is not awarded below 100%.
        
        Validates: Requirements 2.3
        """
        from app.services.profile import ProfileService
        
        service = ProfileService(db=MagicMock())
        assert service.check_completion_badge(0) is False
        assert service.check_completion_badge(50) is False
        assert service.check_completion_badge(99) is False
    
    @pytest.mark.asyncio
    async def test_calculate_completion_percentage_empty_profiles(self):
        """Test completion percentage with no data filled.
        
        Validates: Requirements 2.2
        """
        from app.services.profile import ProfileService
        
        mock_db = MagicMock()
        service = ProfileService(db=mock_db)
        
        # Mock all repositories to return None (no profiles exist)
        service.profile_repo.get_profile_by_user_id = AsyncMock(return_value=None)
        service.student_profile_repo.get_student_profile_by_user_id = AsyncMock(return_value=None)
        service.career_preferences_repo.get_career_preferences_by_user_id = AsyncMock(return_value=None)
        
        user_id = uuid4()
        percentage = await service.calculate_completion_percentage(user_id)
        
        assert percentage == 0
    
    @pytest.mark.asyncio
    async def test_calculate_completion_percentage_partial_basic_profile(self):
        """Test completion percentage with partial basic profile.
        
        Validates: Requirements 2.2
        """
        from app.services.profile import ProfileService
        
        mock_db = MagicMock()
        service = ProfileService(db=mock_db)
        
        # Create mock profile with 3 out of 5 fields filled
        mock_profile = MagicMock()
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.date_of_birth = None
        mock_profile.gender = "male"
        mock_profile.avatar_url = None
        
        service.profile_repo.get_profile_by_user_id = AsyncMock(return_value=mock_profile)
        service.student_profile_repo.get_student_profile_by_user_id = AsyncMock(return_value=None)
        service.career_preferences_repo.get_career_preferences_by_user_id = AsyncMock(return_value=None)
        
        user_id = uuid4()
        percentage = await service.calculate_completion_percentage(user_id)
        
        # 3/5 * 40 = 24%
        assert percentage == 24
    
    @pytest.mark.asyncio
    async def test_calculate_completion_percentage_full_profile(self):
        """Test completion percentage with all profiles fully filled.
        
        Validates: Requirements 2.2
        """
        from app.services.profile import ProfileService
        from datetime import date
        
        mock_db = MagicMock()
        service = ProfileService(db=mock_db)
        
        # Create fully filled basic profile (5/5 fields = 40%)
        mock_profile = MagicMock()
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.date_of_birth = date(1995, 6, 15)
        mock_profile.gender = "male"
        mock_profile.avatar_url = "https://example.com/avatar.jpg"
        
        # Create fully filled student profile (5/5 fields = 30%)
        mock_student_profile = MagicMock()
        mock_student_profile.institution = "MIT"
        mock_student_profile.degree = "B.Tech"
        mock_student_profile.branch = "Computer Science"
        mock_student_profile.cgpa = Decimal("8.5")
        mock_student_profile.graduation_year = 2024
        
        # Create fully filled career preferences (4/4 fields = 30%)
        mock_career_prefs = MagicMock()
        mock_career_prefs.preferred_roles = ["Software Engineer"]
        mock_career_prefs.preferred_locations = ["San Francisco"]
        mock_career_prefs.min_salary = Decimal("80000")
        mock_career_prefs.job_type = "full-time"
        
        service.profile_repo.get_profile_by_user_id = AsyncMock(return_value=mock_profile)
        service.student_profile_repo.get_student_profile_by_user_id = AsyncMock(return_value=mock_student_profile)
        service.career_preferences_repo.get_career_preferences_by_user_id = AsyncMock(return_value=mock_career_prefs)
        
        user_id = uuid4()
        percentage = await service.calculate_completion_percentage(user_id)
        
        # 40 + 30 + 30 = 100%
        assert percentage == 100
    
    @pytest.mark.asyncio
    async def test_calculate_completion_percentage_mixed_profiles(self):
        """Test completion percentage with mixed profile data.
        
        Validates: Requirements 2.2
        """
        from app.services.profile import ProfileService
        from datetime import date
        
        mock_db = MagicMock()
        service = ProfileService(db=mock_db)
        
        # Create partially filled basic profile (4/5 fields = 32%)
        mock_profile = MagicMock()
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.date_of_birth = date(1995, 6, 15)
        mock_profile.gender = "male"
        mock_profile.avatar_url = None
        
        # Create partially filled student profile (3/5 fields = 18%)
        mock_student_profile = MagicMock()
        mock_student_profile.institution = "MIT"
        mock_student_profile.degree = "B.Tech"
        mock_student_profile.branch = "Computer Science"
        mock_student_profile.cgpa = None
        mock_student_profile.graduation_year = None
        
        # Create partially filled career preferences (2/4 fields = 15%)
        mock_career_prefs = MagicMock()
        mock_career_prefs.preferred_roles = ["Software Engineer"]
        mock_career_prefs.preferred_locations = []  # Empty list = not filled
        mock_career_prefs.min_salary = Decimal("80000")
        mock_career_prefs.job_type = None
        
        service.profile_repo.get_profile_by_user_id = AsyncMock(return_value=mock_profile)
        service.student_profile_repo.get_student_profile_by_user_id = AsyncMock(return_value=mock_student_profile)
        service.career_preferences_repo.get_career_preferences_by_user_id = AsyncMock(return_value=mock_career_prefs)
        
        user_id = uuid4()
        percentage = await service.calculate_completion_percentage(user_id)
        
        # 4/5 * 40 + 3/5 * 30 + 2/4 * 30 = 32 + 18 + 15 = 65%
        assert percentage == 65
