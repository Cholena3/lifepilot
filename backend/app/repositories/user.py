"""User repository for database operations.

Validates: Requirements 1.1, 1.3
"""

from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository for User database operations."""
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create_user(self, email: str, password_hash: str) -> User:
        """Create a new user in the database.
        
        Validates: Requirements 1.1
        
        Args:
            email: User's email address
            password_hash: Bcrypt hashed password
            
        Returns:
            Created User model instance
        """
        user = User(
            email=email,
            password_hash=password_hash,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def create_oauth_user(
        self,
        email: str,
        oauth_provider: str,
        oauth_id: str,
    ) -> User:
        """Create a new user via OAuth provider.
        
        Validates: Requirements 1.3
        
        Args:
            email: User's email address from OAuth provider
            oauth_provider: OAuth provider name (e.g., 'google')
            oauth_id: OAuth provider user ID
            
        Returns:
            Created User model instance
        """
        user = User(
            email=email.lower(),
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def get_user_by_email(self, email: str) -> User | None:
        """Find a user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(User.email == email.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: str) -> User | None:
        """Find a user by ID.
        
        Args:
            user_id: User's UUID as string
            
        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_oauth(
        self,
        provider: str,
        oauth_id: str,
    ) -> User | None:
        """Find a user by OAuth provider and ID.
        
        Validates: Requirements 1.3
        
        Args:
            provider: OAuth provider name (e.g., 'google')
            oauth_id: OAuth provider user ID
            
        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(
            and_(
                User.oauth_provider == provider,
                User.oauth_id == oauth_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def link_oauth(
        self,
        user_id: UUID,
        provider: str,
        oauth_id: str,
    ) -> User:
        """Link OAuth provider to existing user account.
        
        Validates: Requirements 1.3
        
        Args:
            user_id: User's UUID
            provider: OAuth provider name (e.g., 'google')
            oauth_id: OAuth provider user ID
            
        Returns:
            Updated User model instance
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one()
        
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        
        await self.db.flush()
        await self.db.refresh(user)
        return user
