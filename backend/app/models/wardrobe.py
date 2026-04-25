"""Wardrobe module models for clothing item management.

Includes WardrobeItem, WearLog, Outfit, OutfitItem, OutfitPlan, PackingList, and PackingListItem models.

Validates: Requirements 19.1-19.6, 20.1-20.6, 21.1-21.5, 22.1-22.5, 23.1-23.5
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ClothingType(str, Enum):
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


class ClothingPattern(str, Enum):
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


class Occasion(str, Enum):
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


class WardrobeItem(Base, UUIDMixin, TimestampMixin):
    """Wardrobe item model for storing clothing items.
    
    Validates: Requirements 19.1-19.6
    """
    
    __tablename__ = "wardrobe_items"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    processed_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    item_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    primary_color: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    pattern: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    brand: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    
    purchase_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    
    in_laundry: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    wear_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    last_worn: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    occasions: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    wear_logs: Mapped[List["WearLog"]] = sa_relationship(
        "WearLog",
        back_populates="wardrobe_item",
        cascade="all, delete-orphan",
    )
    
    outfit_items: Mapped[List["OutfitItem"]] = sa_relationship(
        "OutfitItem",
        back_populates="wardrobe_item",
        cascade="all, delete-orphan",
    )
    
    packing_list_items: Mapped[List["PackingListItem"]] = sa_relationship(
        "PackingListItem",
        back_populates="wardrobe_item",
        cascade="all, delete-orphan",
    )


class WearLog(Base, UUIDMixin, TimestampMixin):
    """Wear log model for tracking when items are worn.
    
    Validates: Requirements 19.6
    """
    
    __tablename__ = "wear_logs"
    
    item_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("wardrobe_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    worn_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    
    occasion: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # Relationships
    wardrobe_item: Mapped["WardrobeItem"] = sa_relationship(
        "WardrobeItem",
        back_populates="wear_logs",
    )


class Outfit(Base, UUIDMixin, TimestampMixin):
    """Outfit model for storing saved outfit combinations.
    
    Validates: Requirements 20.6
    """
    
    __tablename__ = "outfits"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    occasion: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    items: Mapped[List["OutfitItem"]] = sa_relationship(
        "OutfitItem",
        back_populates="outfit",
        cascade="all, delete-orphan",
    )
    
    plans: Mapped[List["OutfitPlan"]] = sa_relationship(
        "OutfitPlan",
        back_populates="outfit",
        cascade="all, delete-orphan",
    )


class OutfitItem(Base, UUIDMixin):
    """Outfit item model for linking wardrobe items to outfits.
    
    Validates: Requirements 20.6
    """
    
    __tablename__ = "outfit_items"
    
    outfit_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("outfits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    wardrobe_item_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("wardrobe_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    outfit: Mapped["Outfit"] = sa_relationship(
        "Outfit",
        back_populates="items",
    )
    
    wardrobe_item: Mapped["WardrobeItem"] = sa_relationship(
        "WardrobeItem",
        back_populates="outfit_items",
    )


class OutfitPlan(Base, UUIDMixin, TimestampMixin):
    """Outfit plan model for scheduling outfits for future dates.
    
    Validates: Requirements 21.1-21.5
    """
    
    __tablename__ = "outfit_plans"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    outfit_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("outfits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    planned_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    
    event_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    outfit: Mapped["Outfit"] = sa_relationship(
        "Outfit",
        back_populates="plans",
    )


class PackingList(Base, UUIDMixin, TimestampMixin):
    """Packing list model for trip packing management.
    
    Validates: Requirements 23.1-23.5
    """
    
    __tablename__ = "packing_lists"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    destination: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    trip_start: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    
    trip_end: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    
    is_template: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    items: Mapped[List["PackingListItem"]] = sa_relationship(
        "PackingListItem",
        back_populates="packing_list",
        cascade="all, delete-orphan",
    )


class PackingListItem(Base, UUIDMixin):
    """Packing list item model for tracking items in a packing list.
    
    Validates: Requirements 23.2, 23.3
    """
    
    __tablename__ = "packing_list_items"
    
    packing_list_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("packing_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    wardrobe_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("wardrobe_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    custom_item_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    
    is_packed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    packing_list: Mapped["PackingList"] = sa_relationship(
        "PackingList",
        back_populates="items",
    )
    
    wardrobe_item: Mapped[Optional["WardrobeItem"]] = sa_relationship(
        "WardrobeItem",
        back_populates="packing_list_items",
    )
