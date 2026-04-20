"""Profile service for user profile management.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.profile import CareerPreferences, Profile, StudentProfile
from app.repositories.profile import (
    CareerPreferencesRepository,
    ProfileRepository,
    StudentProfileRepository,
)
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


# Profile completion weights
BASIC_PROFILE_WEIGHT = 40  # 40% for basic profile fields
STUDENT_PROFILE_WEIGHT = 30  # 30% for student profile fields
CAREER_PREFERENCES_WEIGHT = 30  # 30% for career preferences fields

# Fields to check for each profile type
BASIC_PROFILE_FIELDS = ["first_name", "last_name", "date_of_birth", "gender", "avatar_url"]
STUDENT_PROFILE_FIELDS = ["institution", "degree", "branch", "cgpa", "graduation_year"]
CAREER_PREFERENCES_FIELDS = ["preferred_roles", "preferred_locations", "min_salary", "job_type"]


class ProfileService:
    """Service for profile management operations."""
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.student_profile_repo = StudentProfileRepository(db)
        self.career_preferences_repo = CareerPreferencesRepository(db)
    
    # Profile operations
    
    async def get_profile(self, user_id: UUID) -> ProfileResponse:
        """Get user's profile.
        
        Validates: Requirements 2.1
        
        Args:
            user_id: User's UUID
            
        Returns:
            ProfileResponse with profile data
            
        Raises:
            NotFoundError: If profile doesn't exist
        """
        profile = await self.profile_repo.get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundError(resource="Profile", identifier=str(user_id))
        return ProfileResponse.model_validate(profile)
    
    async def get_or_create_profile(self, user_id: UUID) -> Profile:
        """Get existing profile or create a new one.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Profile model instance
        """
        profile = await self.profile_repo.get_profile_by_user_id(user_id)
        if not profile:
            profile = await self.profile_repo.create_profile(
                user_id=user_id,
                data=ProfileCreate(),
            )
        return profile
    
    async def update_profile(
        self,
        user_id: UUID,
        data: ProfileUpdate,
    ) -> ProfileResponse:
        """Update user's profile.
        
        Validates: Requirements 2.1, 2.2
        
        Args:
            user_id: User's UUID
            data: Profile update data
            
        Returns:
            ProfileResponse with updated profile data
        """
        # Get or create profile
        profile = await self.get_or_create_profile(user_id)
        
        # Update profile
        updated_profile = await self.profile_repo.update_profile(profile, data)
        
        # Recalculate and update completion percentage
        completion_percentage = await self.calculate_completion_percentage(user_id)
        updated_profile = await self.profile_repo.update_completion_percentage(
            updated_profile, completion_percentage
        )
        
        return ProfileResponse.model_validate(updated_profile)
    
    # Student Profile operations
    
    async def get_student_profile(self, user_id: UUID) -> StudentProfileResponse:
        """Get user's student profile.
        
        Validates: Requirements 2.1
        
        Args:
            user_id: User's UUID
            
        Returns:
            StudentProfileResponse with student profile data
            
        Raises:
            NotFoundError: If student profile doesn't exist
        """
        student_profile = await self.student_profile_repo.get_student_profile_by_user_id(
            user_id
        )
        if not student_profile:
            raise NotFoundError(resource="StudentProfile", identifier=str(user_id))
        return StudentProfileResponse.model_validate(student_profile)
    
    async def get_or_create_student_profile(self, user_id: UUID) -> StudentProfile:
        """Get existing student profile or create a new one.
        
        Args:
            user_id: User's UUID
            
        Returns:
            StudentProfile model instance
        """
        student_profile = await self.student_profile_repo.get_student_profile_by_user_id(
            user_id
        )
        if not student_profile:
            student_profile = await self.student_profile_repo.create_student_profile(
                user_id=user_id,
                data=StudentProfileCreate(),
            )
        return student_profile
    
    async def update_student_profile(
        self,
        user_id: UUID,
        data: StudentProfileUpdate,
    ) -> StudentProfileResponse:
        """Update user's student profile.
        
        Validates: Requirements 2.1, 2.2, 2.4
        
        Args:
            user_id: User's UUID
            data: Student profile update data
            
        Returns:
            StudentProfileResponse with updated student profile data
        """
        # Get or create student profile
        student_profile = await self.get_or_create_student_profile(user_id)
        
        # Update student profile
        updated_student_profile = await self.student_profile_repo.update_student_profile(
            student_profile, data
        )
        
        # Recalculate and update completion percentage in main profile
        await self._update_profile_completion(user_id)
        
        return StudentProfileResponse.model_validate(updated_student_profile)
    
    # Career Preferences operations
    
    async def get_career_preferences(self, user_id: UUID) -> CareerPreferencesResponse:
        """Get user's career preferences.
        
        Validates: Requirements 2.5
        
        Args:
            user_id: User's UUID
            
        Returns:
            CareerPreferencesResponse with career preferences data
            
        Raises:
            NotFoundError: If career preferences don't exist
        """
        career_preferences = (
            await self.career_preferences_repo.get_career_preferences_by_user_id(user_id)
        )
        if not career_preferences:
            raise NotFoundError(resource="CareerPreferences", identifier=str(user_id))
        return CareerPreferencesResponse.model_validate(career_preferences)
    
    async def get_or_create_career_preferences(
        self,
        user_id: UUID,
    ) -> CareerPreferences:
        """Get existing career preferences or create new ones.
        
        Args:
            user_id: User's UUID
            
        Returns:
            CareerPreferences model instance
        """
        career_preferences = (
            await self.career_preferences_repo.get_career_preferences_by_user_id(user_id)
        )
        if not career_preferences:
            career_preferences = (
                await self.career_preferences_repo.create_career_preferences(
                    user_id=user_id,
                    data=CareerPreferencesCreate(),
                )
            )
        return career_preferences
    
    async def update_career_preferences(
        self,
        user_id: UUID,
        data: CareerPreferencesUpdate,
    ) -> CareerPreferencesResponse:
        """Update user's career preferences.
        
        Validates: Requirements 2.2, 2.5
        
        Args:
            user_id: User's UUID
            data: Career preferences update data
            
        Returns:
            CareerPreferencesResponse with updated career preferences data
        """
        # Get or create career preferences
        career_preferences = await self.get_or_create_career_preferences(user_id)
        
        # Update career preferences
        updated_career_preferences = (
            await self.career_preferences_repo.update_career_preferences(
                career_preferences, data
            )
        )
        
        # Recalculate and update completion percentage in main profile
        await self._update_profile_completion(user_id)
        
        return CareerPreferencesResponse.model_validate(updated_career_preferences)
    
    # Profile Completion operations
    
    async def calculate_completion_percentage(self, user_id: UUID) -> int:
        """Calculate profile completion percentage based on filled fields.
        
        Validates: Requirements 2.2
        
        The completion percentage is calculated as follows:
        - Basic profile fields (first_name, last_name, date_of_birth, gender, avatar_url) = 40%
        - Student profile fields (institution, degree, branch, cgpa, graduation_year) = 30%
        - Career preferences fields (preferred_roles, preferred_locations, min_salary, job_type) = 30%
        
        Args:
            user_id: User's UUID
            
        Returns:
            Completion percentage (0-100)
        """
        # Get all profile data
        profile = await self.profile_repo.get_profile_by_user_id(user_id)
        student_profile = await self.student_profile_repo.get_student_profile_by_user_id(
            user_id
        )
        career_preferences = (
            await self.career_preferences_repo.get_career_preferences_by_user_id(user_id)
        )
        
        # Calculate basic profile completion
        basic_filled = self._count_filled_fields(profile, BASIC_PROFILE_FIELDS)
        basic_total = len(BASIC_PROFILE_FIELDS)
        basic_percentage = (basic_filled / basic_total) * BASIC_PROFILE_WEIGHT
        
        # Calculate student profile completion
        student_filled = self._count_filled_fields(student_profile, STUDENT_PROFILE_FIELDS)
        student_total = len(STUDENT_PROFILE_FIELDS)
        student_percentage = (student_filled / student_total) * STUDENT_PROFILE_WEIGHT
        
        # Calculate career preferences completion
        career_filled = self._count_filled_fields(
            career_preferences, CAREER_PREFERENCES_FIELDS
        )
        career_total = len(CAREER_PREFERENCES_FIELDS)
        career_percentage = (career_filled / career_total) * CAREER_PREFERENCES_WEIGHT
        
        # Calculate total percentage and floor it
        total_percentage = int(basic_percentage + student_percentage + career_percentage)
        
        return total_percentage
    
    def _count_filled_fields(
        self,
        model: Optional[Profile | StudentProfile | CareerPreferences],
        fields: list[str],
    ) -> int:
        """Count the number of filled fields in a model.
        
        Args:
            model: The model instance to check (can be None)
            fields: List of field names to check
            
        Returns:
            Number of filled fields
        """
        if model is None:
            return 0
        
        filled_count = 0
        for field in fields:
            value = getattr(model, field, None)
            if self._is_field_filled(value):
                filled_count += 1
        
        return filled_count
    
    def _is_field_filled(self, value) -> bool:
        """Check if a field value is considered filled.
        
        Args:
            value: The field value to check
            
        Returns:
            True if the field is filled, False otherwise
        """
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        return True
    
    async def _update_profile_completion(self, user_id: UUID) -> None:
        """Update the completion percentage in the user's profile.
        
        Args:
            user_id: User's UUID
        """
        # Get or create profile to ensure it exists
        profile = await self.get_or_create_profile(user_id)
        
        # Calculate and update completion percentage
        completion_percentage = await self.calculate_completion_percentage(user_id)
        await self.profile_repo.update_completion_percentage(profile, completion_percentage)
    
    def check_completion_badge(self, completion_percentage: int) -> bool:
        """Check if the user qualifies for the profile completion badge.
        
        Validates: Requirements 2.3
        
        Args:
            completion_percentage: The current completion percentage
            
        Returns:
            True if completion_percentage == 100, False otherwise
        """
        return completion_percentage == 100
