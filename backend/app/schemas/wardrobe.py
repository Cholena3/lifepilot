"""Pydantic schemas for wardrobe module.

Includes schemas for wardrobe item, outfit, outfit plan, and packing list management.

Validates: Requirements 19.1-19.6, 20.1-20.6, 21.1-21.5, 22.1-22.5, 23.1-23.5
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ClothingType:
    """Valid clothing types."""
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    FOOTWEAR = "footwear"
    ACCESSORY = "accessory"
    ACTIVEWEAR = "activewear"
    SLEEPWEAR = "sleepwear"
    SWIMWEAR = "swimwear"
    FORMAL = "formal"
    OTHER = "other"
    
    ALL = [TOP, BOTTOM, DRESS, OUTERWEAR, FOOTWEAR, ACCESSORY, ACTIVEWEAR, SLEEPWEAR, SWIMWEAR, FORMAL, OTHER]


class ClothingPattern:
    """Valid clothing patterns."""
    SOLID = "solid"
    STRIPED = "striped"
    PLAID = "plaid"
    FLORAL = "floral"
    POLKA_DOT = "polka_dot"
    GEOMETRIC = "geometric"
    ABSTRACT = "abstract"
    ANIMAL_PRINT = "animal_print"
    CAMOUFLAGE = "camouflage"
    OTHER = "other"
    
    ALL = [SOLID, STRIPED, PLAID, FLORAL, POLKA_DOT, GEOMETRIC, ABSTRACT, ANIMAL_PRINT, CAMOUFLAGE, OTHER]


class Occasion:
    """Valid occasions for clothing."""
    CASUAL = "casual"
    FORMAL = "formal"
    BUSINESS = "business"
    PARTY = "party"
    SPORTS = "sports"
    BEACH = "beach"
    WEDDING = "wedding"
    DATE = "date"
    INTERVIEW = "interview"
    OTHER = "other"
    
    ALL = [CASUAL, FORMAL, BUSINESS, PARTY, SPORTS, BEACH, WEDDING, DATE, INTERVIEW, OTHER]


# ============================================================================
# Wardrobe Item Schemas
# ============================================================================

class WardrobeItemCreate(BaseModel):
    """Schema for creating a new wardrobe item.
    
    Validates: Requirements 19.1, 19.4
    """
    
    item_type: str = Field(..., description="Type of clothing item")
    name: Optional[str] = Field(None, max_length=255, description="Name/description of the item")
    primary_color: Optional[str] = Field(None, max_length=50, description="Primary color")
    pattern: Optional[str] = Field(None, max_length=50, description="Pattern type")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    price: Optional[Decimal] = Field(None, ge=0, description="Purchase price")
    purchase_date: Optional[date] = Field(None, description="Date of purchase")
    occasions: Optional[List[str]] = Field(None, description="Suitable occasions")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, v: str) -> str:
        if v not in ClothingType.ALL:
            raise ValueError(f"Item type must be one of: {', '.join(ClothingType.ALL)}")
        return v
    
    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ClothingPattern.ALL:
            raise ValueError(f"Pattern must be one of: {', '.join(ClothingPattern.ALL)}")
        return v
    
    @field_validator("occasions")
    @classmethod
    def validate_occasions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            for occasion in v:
                if occasion not in Occasion.ALL:
                    raise ValueError(f"Occasion must be one of: {', '.join(Occasion.ALL)}")
        return v


class WardrobeItemUpdate(BaseModel):
    """Schema for updating a wardrobe item."""
    
    item_type: Optional[str] = None
    name: Optional[str] = Field(None, max_length=255)
    primary_color: Optional[str] = Field(None, max_length=50)
    pattern: Optional[str] = Field(None, max_length=50)
    brand: Optional[str] = Field(None, max_length=100)
    price: Optional[Decimal] = Field(None, ge=0)
    purchase_date: Optional[date] = None
    occasions: Optional[List[str]] = None
    notes: Optional[str] = None
    
    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ClothingType.ALL:
            raise ValueError(f"Item type must be one of: {', '.join(ClothingType.ALL)}")
        return v
    
    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ClothingPattern.ALL:
            raise ValueError(f"Pattern must be one of: {', '.join(ClothingPattern.ALL)}")
        return v


class WardrobeItemResponse(BaseModel):
    """Response schema for a wardrobe item.
    
    Validates: Requirements 19.1-19.6
    """
    
    id: UUID
    user_id: UUID
    image_url: str
    processed_image_url: Optional[str] = None
    item_type: str
    name: Optional[str] = None
    primary_color: Optional[str] = None
    pattern: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[Decimal] = None
    purchase_date: Optional[date] = None
    in_laundry: bool
    wear_count: int
    last_worn: Optional[datetime] = None
    occasions: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class WardrobeItemWithStatsResponse(WardrobeItemResponse):
    """Response schema for a wardrobe item with statistics."""
    
    cost_per_wear: Optional[Decimal] = None
    days_since_last_worn: Optional[int] = None


# ============================================================================
# Wear Log Schemas
# ============================================================================

class WearLogCreate(BaseModel):
    """Schema for creating a wear log entry.
    
    Validates: Requirements 19.6
    """
    
    worn_date: date = Field(..., description="Date the item was worn")
    occasion: Optional[str] = Field(None, max_length=50, description="Occasion for wearing")
    
    @field_validator("occasion")
    @classmethod
    def validate_occasion(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in Occasion.ALL:
            raise ValueError(f"Occasion must be one of: {', '.join(Occasion.ALL)}")
        return v


class WearLogResponse(BaseModel):
    """Response schema for a wear log entry."""
    
    id: UUID
    item_id: UUID
    worn_date: date
    occasion: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Outfit Schemas
# ============================================================================

class OutfitCreate(BaseModel):
    """Schema for creating a new outfit.
    
    Validates: Requirements 20.6
    """
    
    name: str = Field(..., min_length=1, max_length=255, description="Outfit name")
    occasion: Optional[str] = Field(None, max_length=50, description="Occasion for the outfit")
    item_ids: List[UUID] = Field(..., min_length=1, description="List of wardrobe item IDs")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator("occasion")
    @classmethod
    def validate_occasion(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in Occasion.ALL:
            raise ValueError(f"Occasion must be one of: {', '.join(Occasion.ALL)}")
        return v


class OutfitUpdate(BaseModel):
    """Schema for updating an outfit."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    occasion: Optional[str] = Field(None, max_length=50)
    item_ids: Optional[List[UUID]] = None
    notes: Optional[str] = None


class OutfitItemResponse(BaseModel):
    """Response schema for an outfit item."""
    
    id: UUID
    wardrobe_item_id: UUID
    wardrobe_item: Optional[WardrobeItemResponse] = None
    
    model_config = {"from_attributes": True}


class OutfitResponse(BaseModel):
    """Response schema for an outfit.
    
    Validates: Requirements 20.6
    """
    
    id: UUID
    user_id: UUID
    name: str
    occasion: Optional[str] = None
    notes: Optional[str] = None
    items: List[OutfitItemResponse] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Outfit Plan Schemas
# ============================================================================

class OutfitPlanCreate(BaseModel):
    """Schema for creating an outfit plan.
    
    Validates: Requirements 21.1
    """
    
    outfit_id: UUID = Field(..., description="ID of the outfit to plan")
    planned_date: date = Field(..., description="Date to wear the outfit")
    event_name: Optional[str] = Field(None, max_length=255, description="Event name")
    notes: Optional[str] = Field(None, description="Additional notes")


class OutfitPlanUpdate(BaseModel):
    """Schema for updating an outfit plan."""
    
    outfit_id: Optional[UUID] = None
    planned_date: Optional[date] = None
    event_name: Optional[str] = Field(None, max_length=255)
    is_completed: Optional[bool] = None
    notes: Optional[str] = None


class OutfitPlanResponse(BaseModel):
    """Response schema for an outfit plan.
    
    Validates: Requirements 21.1-21.5
    """
    
    id: UUID
    user_id: UUID
    outfit_id: UUID
    planned_date: date
    event_name: Optional[str] = None
    is_completed: bool
    notes: Optional[str] = None
    outfit: Optional[OutfitResponse] = None
    laundry_conflicts: Optional[List[UUID]] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Packing List Schemas
# ============================================================================

class PackingListItemCreate(BaseModel):
    """Schema for creating a packing list item."""
    
    wardrobe_item_id: Optional[UUID] = Field(None, description="ID of wardrobe item")
    custom_item_name: Optional[str] = Field(None, max_length=255, description="Custom item name")
    quantity: int = Field(default=1, ge=1, description="Quantity to pack")


class PackingListCreate(BaseModel):
    """Schema for creating a packing list.
    
    Validates: Requirements 23.1
    """
    
    name: str = Field(..., min_length=1, max_length=255, description="Packing list name")
    destination: Optional[str] = Field(None, max_length=255, description="Trip destination")
    trip_start: Optional[date] = Field(None, description="Trip start date")
    trip_end: Optional[date] = Field(None, description="Trip end date")
    is_template: bool = Field(default=False, description="Save as template")
    notes: Optional[str] = Field(None, description="Additional notes")
    items: Optional[List[PackingListItemCreate]] = Field(None, description="Initial items")


class PackingListUpdate(BaseModel):
    """Schema for updating a packing list."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    destination: Optional[str] = Field(None, max_length=255)
    trip_start: Optional[date] = None
    trip_end: Optional[date] = None
    is_template: Optional[bool] = None
    notes: Optional[str] = None


class PackingListItemResponse(BaseModel):
    """Response schema for a packing list item."""
    
    id: UUID
    packing_list_id: UUID
    wardrobe_item_id: Optional[UUID] = None
    custom_item_name: Optional[str] = None
    quantity: int
    is_packed: bool
    wardrobe_item: Optional[WardrobeItemResponse] = None
    
    model_config = {"from_attributes": True}


class PackingListResponse(BaseModel):
    """Response schema for a packing list.
    
    Validates: Requirements 23.1-23.5
    """
    
    id: UUID
    user_id: UUID
    name: str
    destination: Optional[str] = None
    trip_start: Optional[date] = None
    trip_end: Optional[date] = None
    is_template: bool
    notes: Optional[str] = None
    items: List[PackingListItemResponse] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Statistics Schemas
# ============================================================================

class WardrobeStatsResponse(BaseModel):
    """Response schema for wardrobe statistics.
    
    Validates: Requirements 22.1-22.5
    """
    
    total_items: int = Field(..., description="Total number of items")
    total_value: Decimal = Field(..., description="Total wardrobe value")
    items_by_type: dict = Field(..., description="Count of items by type")
    items_by_color: dict = Field(..., description="Count of items by color")
    most_worn_items: List[WardrobeItemWithStatsResponse] = Field(..., description="Most worn items")
    least_worn_items: List[WardrobeItemWithStatsResponse] = Field(..., description="Least worn items")
    unworn_items: List[WardrobeItemResponse] = Field(..., description="Items not worn in 6+ months")
    items_in_laundry: int = Field(..., description="Number of items in laundry")
    average_cost_per_wear: Optional[Decimal] = Field(None, description="Average cost per wear")


# ============================================================================
# Outfit Suggestion Schemas
# ============================================================================

class OutfitSuggestionRequest(BaseModel):
    """Request schema for outfit suggestions.
    
    Validates: Requirements 20.1-20.5
    """
    
    occasion: Optional[str] = Field(None, description="Occasion filter")
    location: Optional[str] = Field(None, description="Location for weather lookup")
    
    @field_validator("occasion")
    @classmethod
    def validate_occasion(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in Occasion.ALL:
            raise ValueError(f"Occasion must be one of: {', '.join(Occasion.ALL)}")
        return v


class WeatherInfo(BaseModel):
    """Weather information for outfit suggestions."""
    
    temperature: float = Field(..., description="Temperature in Celsius")
    condition: str = Field(..., description="Weather condition")
    humidity: Optional[float] = Field(None, description="Humidity percentage")


class OutfitSuggestionResponse(BaseModel):
    """Response schema for outfit suggestions.
    
    Validates: Requirements 20.1-20.5
    """
    
    items: List[WardrobeItemResponse] = Field(..., description="Suggested outfit items")
    weather: Optional[WeatherInfo] = Field(None, description="Current weather info")
    occasion: Optional[str] = Field(None, description="Occasion for the suggestion")
    score: float = Field(..., description="Suggestion score/confidence")


# ============================================================================
# Filter and Pagination Schemas
# ============================================================================

class WardrobeItemFilters(BaseModel):
    """Schema for wardrobe item filter parameters."""
    
    item_type: Optional[str] = Field(None, description="Filter by item type")
    primary_color: Optional[str] = Field(None, description="Filter by color")
    pattern: Optional[str] = Field(None, description="Filter by pattern")
    occasion: Optional[str] = Field(None, description="Filter by occasion")
    in_laundry: Optional[bool] = Field(None, description="Filter by laundry status")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedWardrobeItemResponse(BaseModel):
    """Paginated response for wardrobe items."""
    
    items: List[WardrobeItemResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)
    
    @classmethod
    def create(cls, items: List[WardrobeItemResponse], total: int, page: int, page_size: int):
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


class PaginatedOutfitResponse(BaseModel):
    """Paginated response for outfits."""
    
    items: List[OutfitResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)


class PaginatedPackingListResponse(BaseModel):
    """Paginated response for packing lists."""
    
    items: List[PackingListResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)
