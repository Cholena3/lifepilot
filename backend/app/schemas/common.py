"""Common Pydantic schemas used across the application."""

from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.config import get_settings

T = TypeVar("T")


def get_pagination_params(
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int | None,
        Query(description="Number of items per page")
    ] = None,
) -> "PaginationParams":
    """Dependency for pagination parameters with configurable defaults.
    
    Validates: Requirements 37.5
    
    Uses settings from config for default and max page sizes.
    
    Args:
        page: Page number (1-indexed, default 1)
        page_size: Items per page (uses config default if not specified)
        
    Returns:
        PaginationParams instance with validated values
    """
    settings = get_settings()
    
    # Use default from settings if not provided
    if page_size is None:
        page_size = settings.pagination_default_page_size
    
    # Clamp page_size to configured limits
    page_size = max(settings.pagination_min_page_size, min(page_size, settings.pagination_max_page_size))
    
    return PaginationParams(page=page, page_size=page_size)


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints (Requirement 37.5)."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @classmethod
    def from_config(cls, page: int = 1, page_size: int | None = None) -> "PaginationParams":
        """Create pagination params using config defaults.
        
        Args:
            page: Page number (1-indexed)
            page_size: Items per page (uses config default if None)
            
        Returns:
            PaginationParams with validated values
        """
        settings = get_settings()
        if page_size is None:
            page_size = settings.pagination_default_page_size
        page_size = max(settings.pagination_min_page_size, min(page_size, settings.pagination_max_page_size))
        return cls(page=page, page_size=page_size)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    detail: str
    field_errors: dict[str, str] | None = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
