"""Profile repository for database operations.

Validates: Requirements 2.1, 2.4, 2.5
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import CareerPreferences, Profile, StudentProfile
from app.schemas.profile import (
    CareerPreferencesCreate,
    CareerPreferencesUpdate,
    ProfileCreate,
    ProfileUpdate,
    StudentProfileCreate,
    StudentProfileUpdate,
)


class ProfileRepository:
    """Repository for Profile database operations."""
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    # Profile CRUD operations
    
    async def get_profile_by_user_id(self, user_id: UUID) -> Optional[Profile]:
        """Get profile by user ID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Profile if found, None otherwise
        """
        stmt = select(Profile).where(Profile.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_profile(
        self,
        user_id: UUID,
        data: ProfileCreate,
    ) -> Profile:
        """Create a new profile for a user.
        
        Validates: Requirements 2.1
        
        Args:
            user_id: User's UUID
            data: Profile creation data
            
        Returns:
            Created Profile model instance
        """
        profile = Profile(
            user_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            avatar_url=data.avatar_url,
            completion_percentage=0,
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile
    
    async def update_profile(
        self,
        profile: Profile,
        data: ProfileUpdate,
    ) -> Profile:
        """Update an existing profile.
        
        Validates: Requirements 2.1
        
        Args:
            profile: Existing Profile model instance
            data: Profile update data
            
        Returns:
            Updated Profile model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        await self.db.flush()
        await self.db.refresh(profile)
        return profile
    
    async def update_completion_percentage(
        self,
        profile: Profile,
        percentage: int,
    ) -> Profile:
        """Update profile completion percentage.
        
        Args:
            profile: Profile model instance
            percentage: New completion percentage
            
        Returns:
            Updated Profile model instance
        """
        profile.completion_percentage = percentage
        await self.db.flush()
        await self.db.refresh(profile)
        return profile


class StudentProfileRepository:
    """Repository for StudentProfile database operations."""
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def get_student_profile_by_user_id(
        self,
        user_id: UUID,
    ) -> Optional[StudentProfile]:
        """Get student profile by user ID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            StudentProfile if found, None otherwise
        """
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_student_profile(
        self,
        user_id: UUID,
        data: StudentProfileCreate,
    ) -> StudentProfile:
        """Create a new student profile for a user.
        
        Validates: Requirements 2.1
        
        Args:
            user_id: User's UUID
            data: Student profile creation data
            
        Returns:
            Created StudentProfile model instance
        """
        student_profile = StudentProfile(
            user_id=user_id,
            institution=data.institution,
            degree=data.degree,
            branch=data.branch,
            cgpa=data.cgpa,
            backlogs=data.backlogs,
            graduation_year=data.graduation_year,
        )
        self.db.add(student_profile)
        await self.db.flush()
        await self.db.refresh(student_profile)
        return student_profile
    
    async def update_student_profile(
        self,
        student_profile: StudentProfile,
        data: StudentProfileUpdate,
    ) -> StudentProfile:
        """Update an existing student profile.
        
        Validates: Requirements 2.1, 2.4
        
        Args:
            student_profile: Existing StudentProfile model instance
            data: Student profile update data
            
        Returns:
            Updated StudentProfile model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(student_profile, field, value)
        
        await self.db.flush()
        await self.db.refresh(student_profile)
        return student_profile


class CareerPreferencesRepository:
    """Repository for CareerPreferences database operations."""
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def get_career_preferences_by_user_id(
        self,
        user_id: UUID,
    ) -> Optional[CareerPreferences]:
        """Get career preferences by user ID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            CareerPreferences if found, None otherwise
        """
        stmt = select(CareerPreferences).where(CareerPreferences.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_career_preferences(
        self,
        user_id: UUID,
        data: CareerPreferencesCreate,
    ) -> CareerPreferences:
        """Create new career preferences for a user.
        
        Validates: Requirements 2.5
        
        Args:
            user_id: User's UUID
            data: Career preferences creation data
            
        Returns:
            Created CareerPreferences model instance
        """
        career_preferences = CareerPreferences(
            user_id=user_id,
            preferred_roles=data.preferred_roles,
            preferred_locations=data.preferred_locations,
            min_salary=data.min_salary,
            max_salary=data.max_salary,
            job_type=data.job_type,
        )
        self.db.add(career_preferences)
        await self.db.flush()
        await self.db.refresh(career_preferences)
        return career_preferences
    
    async def update_career_preferences(
        self,
        career_preferences: CareerPreferences,
        data: CareerPreferencesUpdate,
    ) -> CareerPreferences:
        """Update existing career preferences.
        
        Validates: Requirements 2.5
        
        Args:
            career_preferences: Existing CareerPreferences model instance
            data: Career preferences update data
            
        Returns:
            Updated CareerPreferences model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(career_preferences, field, value)
        
        await self.db.flush()
        await self.db.refresh(career_preferences)
        return career_preferences
