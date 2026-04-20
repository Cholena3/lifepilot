"""Repository for wardrobe module database operations.

Validates: Requirements 19.1-19.6, 20.1-20.6, 21.1-21.5, 22.1-22.5, 23.1-23.5
"""

import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.wardrobe import (
    WardrobeItem, WearLog, Outfit, OutfitItem, OutfitPlan, PackingList, PackingListItem
)


class WardrobeRepository:
    """Repository for wardrobe item operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_item(
        self,
        user_id: uuid.UUID,
        image_url: str,
        item_type: str,
        processed_image_url: Optional[str] = None,
        name: Optional[str] = None,
        primary_color: Optional[str] = None,
        pattern: Optional[str] = None,
        brand: Optional[str] = None,
        price: Optional[Decimal] = None,
        purchase_date: Optional[date] = None,
        occasions: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> WardrobeItem:
        """Create a new wardrobe item."""
        item = WardrobeItem(
            user_id=user_id,
            image_url=image_url,
            processed_image_url=processed_image_url,
            item_type=item_type,
            name=name,
            primary_color=primary_color,
            pattern=pattern,
            brand=brand,
            price=price,
            purchase_date=purchase_date,
            occasions=occasions or [],
            notes=notes,
        )
        self.session.add(item)
        await self.session.flush()
        return item
    
    async def get_item_by_id(self, item_id: uuid.UUID, user_id: uuid.UUID) -> Optional[WardrobeItem]:
        """Get a wardrobe item by ID."""
        result = await self.session.execute(
            select(WardrobeItem).where(
                and_(WardrobeItem.id == item_id, WardrobeItem.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_items(
        self,
        user_id: uuid.UUID,
        item_type: Optional[str] = None,
        primary_color: Optional[str] = None,
        pattern: Optional[str] = None,
        occasion: Optional[str] = None,
        in_laundry: Optional[bool] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[WardrobeItem], int]:
        """Get wardrobe items with filters and pagination."""
        query = select(WardrobeItem).where(WardrobeItem.user_id == user_id)
        
        if item_type:
            query = query.where(WardrobeItem.item_type == item_type)
        if primary_color:
            query = query.where(WardrobeItem.primary_color == primary_color)
        if pattern:
            query = query.where(WardrobeItem.pattern == pattern)
        if occasion:
            query = query.where(WardrobeItem.occasions.contains([occasion]))
        if in_laundry is not None:
            query = query.where(WardrobeItem.in_laundry == in_laundry)
        if min_price is not None:
            query = query.where(WardrobeItem.price >= min_price)
        if max_price is not None:
            query = query.where(WardrobeItem.price <= max_price)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0
        
        # Apply pagination
        query = query.order_by(desc(WardrobeItem.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
    
    async def update_item(self, item: WardrobeItem, **kwargs) -> WardrobeItem:
        """Update a wardrobe item."""
        for key, value in kwargs.items():
            if value is not None and hasattr(item, key):
                setattr(item, key, value)
        await self.session.flush()
        return item
    
    async def delete_item(self, item: WardrobeItem) -> None:
        """Delete a wardrobe item."""
        await self.session.delete(item)
        await self.session.flush()
    
    async def set_laundry_status(self, item: WardrobeItem, in_laundry: bool) -> WardrobeItem:
        """Set the laundry status of an item."""
        item.in_laundry = in_laundry
        await self.session.flush()
        return item
    
    async def get_available_items(
        self,
        user_id: uuid.UUID,
        item_type: Optional[str] = None,
        occasion: Optional[str] = None,
    ) -> List[WardrobeItem]:
        """Get available items (not in laundry) for outfit suggestions."""
        query = select(WardrobeItem).where(
            and_(
                WardrobeItem.user_id == user_id,
                WardrobeItem.in_laundry == False,
            )
        )
        
        if item_type:
            query = query.where(WardrobeItem.item_type == item_type)
        if occasion:
            query = query.where(WardrobeItem.occasions.contains([occasion]))
        
        # Order by last worn (prioritize items not worn recently)
        query = query.order_by(WardrobeItem.last_worn.asc().nullsfirst())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_items_in_laundry(self, user_id: uuid.UUID) -> List[WardrobeItem]:
        """Get all items currently in laundry."""
        result = await self.session.execute(
            select(WardrobeItem).where(
                and_(WardrobeItem.user_id == user_id, WardrobeItem.in_laundry == True)
            )
        )
        return list(result.scalars().all())


class WearLogRepository:
    """Repository for wear log operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_log(
        self,
        item_id: uuid.UUID,
        worn_date: date,
        occasion: Optional[str] = None,
    ) -> WearLog:
        """Create a new wear log entry."""
        log = WearLog(
            item_id=item_id,
            worn_date=worn_date,
            occasion=occasion,
        )
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def get_logs_for_item(
        self,
        item_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[WearLog]:
        """Get wear logs for an item."""
        query = select(WearLog).where(WearLog.item_id == item_id)
        
        if start_date:
            query = query.where(WearLog.worn_date >= start_date)
        if end_date:
            query = query.where(WearLog.worn_date <= end_date)
        
        query = query.order_by(desc(WearLog.worn_date))
        result = await self.session.execute(query)
        return list(result.scalars().all())


class OutfitRepository:
    """Repository for outfit operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_outfit(
        self,
        user_id: uuid.UUID,
        name: str,
        item_ids: List[uuid.UUID],
        occasion: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Outfit:
        """Create a new outfit."""
        outfit = Outfit(
            user_id=user_id,
            name=name,
            occasion=occasion,
            notes=notes,
        )
        self.session.add(outfit)
        await self.session.flush()
        
        # Add outfit items
        for item_id in item_ids:
            outfit_item = OutfitItem(outfit_id=outfit.id, wardrobe_item_id=item_id)
            self.session.add(outfit_item)
        
        await self.session.flush()
        return outfit
    
    async def get_outfit_by_id(self, outfit_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Outfit]:
        """Get an outfit by ID with items."""
        result = await self.session.execute(
            select(Outfit)
            .options(selectinload(Outfit.items).selectinload(OutfitItem.wardrobe_item))
            .where(and_(Outfit.id == outfit_id, Outfit.user_id == user_id))
        )
        return result.scalar_one_or_none()
    
    async def get_outfits(
        self,
        user_id: uuid.UUID,
        occasion: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Outfit], int]:
        """Get outfits with filters and pagination."""
        query = select(Outfit).where(Outfit.user_id == user_id)
        
        if occasion:
            query = query.where(Outfit.occasion == occasion)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0
        
        # Apply pagination and load items
        query = query.options(selectinload(Outfit.items).selectinload(OutfitItem.wardrobe_item))
        query = query.order_by(desc(Outfit.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
    
    async def update_outfit(
        self,
        outfit: Outfit,
        name: Optional[str] = None,
        occasion: Optional[str] = None,
        item_ids: Optional[List[uuid.UUID]] = None,
        notes: Optional[str] = None,
    ) -> Outfit:
        """Update an outfit."""
        if name is not None:
            outfit.name = name
        if occasion is not None:
            outfit.occasion = occasion
        if notes is not None:
            outfit.notes = notes
        
        if item_ids is not None:
            # Remove existing items
            await self.session.execute(
                select(OutfitItem).where(OutfitItem.outfit_id == outfit.id)
            )
            for item in outfit.items:
                await self.session.delete(item)
            
            # Add new items
            for item_id in item_ids:
                outfit_item = OutfitItem(outfit_id=outfit.id, wardrobe_item_id=item_id)
                self.session.add(outfit_item)
        
        await self.session.flush()
        return outfit
    
    async def delete_outfit(self, outfit: Outfit) -> None:
        """Delete an outfit."""
        await self.session.delete(outfit)
        await self.session.flush()


class OutfitPlanRepository:
    """Repository for outfit plan operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_plan(
        self,
        user_id: uuid.UUID,
        outfit_id: uuid.UUID,
        planned_date: date,
        event_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> OutfitPlan:
        """Create a new outfit plan."""
        plan = OutfitPlan(
            user_id=user_id,
            outfit_id=outfit_id,
            planned_date=planned_date,
            event_name=event_name,
            notes=notes,
        )
        self.session.add(plan)
        await self.session.flush()
        return plan
    
    async def get_plan_by_id(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> Optional[OutfitPlan]:
        """Get an outfit plan by ID."""
        result = await self.session.execute(
            select(OutfitPlan)
            .options(selectinload(OutfitPlan.outfit).selectinload(Outfit.items).selectinload(OutfitItem.wardrobe_item))
            .where(and_(OutfitPlan.id == plan_id, OutfitPlan.user_id == user_id))
        )
        return result.scalar_one_or_none()
    
    async def get_plans(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_completed: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[OutfitPlan], int]:
        """Get outfit plans with filters and pagination."""
        query = select(OutfitPlan).where(OutfitPlan.user_id == user_id)
        
        if start_date:
            query = query.where(OutfitPlan.planned_date >= start_date)
        if end_date:
            query = query.where(OutfitPlan.planned_date <= end_date)
        if is_completed is not None:
            query = query.where(OutfitPlan.is_completed == is_completed)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0
        
        # Apply pagination and load outfit
        query = query.options(selectinload(OutfitPlan.outfit).selectinload(Outfit.items).selectinload(OutfitItem.wardrobe_item))
        query = query.order_by(OutfitPlan.planned_date)
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
    
    async def update_plan(self, plan: OutfitPlan, **kwargs) -> OutfitPlan:
        """Update an outfit plan."""
        for key, value in kwargs.items():
            if value is not None and hasattr(plan, key):
                setattr(plan, key, value)
        await self.session.flush()
        return plan
    
    async def delete_plan(self, plan: OutfitPlan) -> None:
        """Delete an outfit plan."""
        await self.session.delete(plan)
        await self.session.flush()
    
    async def get_upcoming_plans(self, user_id: uuid.UUID, days: int = 7) -> List[OutfitPlan]:
        """Get upcoming outfit plans for reminders."""
        today = date.today()
        end_date = today + timedelta(days=days)
        
        result = await self.session.execute(
            select(OutfitPlan)
            .options(selectinload(OutfitPlan.outfit).selectinload(Outfit.items).selectinload(OutfitItem.wardrobe_item))
            .where(
                and_(
                    OutfitPlan.user_id == user_id,
                    OutfitPlan.planned_date >= today,
                    OutfitPlan.planned_date <= end_date,
                    OutfitPlan.is_completed == False,
                )
            )
            .order_by(OutfitPlan.planned_date)
        )
        return list(result.scalars().all())


class PackingListRepository:
    """Repository for packing list operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_list(
        self,
        user_id: uuid.UUID,
        name: str,
        destination: Optional[str] = None,
        trip_start: Optional[date] = None,
        trip_end: Optional[date] = None,
        is_template: bool = False,
        notes: Optional[str] = None,
    ) -> PackingList:
        """Create a new packing list."""
        packing_list = PackingList(
            user_id=user_id,
            name=name,
            destination=destination,
            trip_start=trip_start,
            trip_end=trip_end,
            is_template=is_template,
            notes=notes,
        )
        self.session.add(packing_list)
        await self.session.flush()
        return packing_list
    
    async def get_list_by_id(self, list_id: uuid.UUID, user_id: uuid.UUID) -> Optional[PackingList]:
        """Get a packing list by ID with items."""
        result = await self.session.execute(
            select(PackingList)
            .options(selectinload(PackingList.items).selectinload(PackingListItem.wardrobe_item))
            .where(and_(PackingList.id == list_id, PackingList.user_id == user_id))
        )
        return result.scalar_one_or_none()
    
    async def get_lists(
        self,
        user_id: uuid.UUID,
        is_template: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[PackingList], int]:
        """Get packing lists with filters and pagination."""
        query = select(PackingList).where(PackingList.user_id == user_id)
        
        if is_template is not None:
            query = query.where(PackingList.is_template == is_template)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0
        
        # Apply pagination and load items
        query = query.options(selectinload(PackingList.items).selectinload(PackingListItem.wardrobe_item))
        query = query.order_by(desc(PackingList.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
    
    async def update_list(self, packing_list: PackingList, **kwargs) -> PackingList:
        """Update a packing list."""
        for key, value in kwargs.items():
            if value is not None and hasattr(packing_list, key):
                setattr(packing_list, key, value)
        await self.session.flush()
        return packing_list
    
    async def delete_list(self, packing_list: PackingList) -> None:
        """Delete a packing list."""
        await self.session.delete(packing_list)
        await self.session.flush()
    
    async def add_item(
        self,
        packing_list_id: uuid.UUID,
        wardrobe_item_id: Optional[uuid.UUID] = None,
        custom_item_name: Optional[str] = None,
        quantity: int = 1,
    ) -> PackingListItem:
        """Add an item to a packing list."""
        item = PackingListItem(
            packing_list_id=packing_list_id,
            wardrobe_item_id=wardrobe_item_id,
            custom_item_name=custom_item_name,
            quantity=quantity,
        )
        self.session.add(item)
        await self.session.flush()
        return item
    
    async def update_item_packed_status(self, item: PackingListItem, is_packed: bool) -> PackingListItem:
        """Update the packed status of an item."""
        item.is_packed = is_packed
        await self.session.flush()
        return item
    
    async def remove_item(self, item: PackingListItem) -> None:
        """Remove an item from a packing list."""
        await self.session.delete(item)
        await self.session.flush()
    
    async def get_item_by_id(self, item_id: uuid.UUID, list_id: uuid.UUID) -> Optional[PackingListItem]:
        """Get a packing list item by ID."""
        result = await self.session.execute(
            select(PackingListItem).where(
                and_(PackingListItem.id == item_id, PackingListItem.packing_list_id == list_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_templates(self, user_id: uuid.UUID) -> List[PackingList]:
        """Get all packing list templates."""
        result = await self.session.execute(
            select(PackingList)
            .options(selectinload(PackingList.items))
            .where(and_(PackingList.user_id == user_id, PackingList.is_template == True))
            .order_by(PackingList.name)
        )
        return list(result.scalars().all())
