"""Service layer for wardrobe module.

Validates: Requirements 19.1-19.6, 20.1-20.6, 21.1-21.5, 22.1-22.5, 23.1-23.5
"""

import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wardrobe import WardrobeItem, WearLog, Outfit, OutfitPlan, PackingList, PackingListItem
from app.repositories.wardrobe import (
    WardrobeRepository, WearLogRepository, OutfitRepository, 
    OutfitPlanRepository, PackingListRepository
)
from app.schemas.wardrobe import (
    WardrobeItemCreate, WardrobeItemUpdate, WardrobeItemResponse, WardrobeItemWithStatsResponse,
    WearLogCreate, WearLogResponse,
    OutfitCreate, OutfitUpdate, OutfitResponse,
    OutfitPlanCreate, OutfitPlanUpdate, OutfitPlanResponse,
    PackingListCreate, PackingListUpdate, PackingListResponse, PackingListItemCreate,
    WardrobeStatsResponse, OutfitSuggestionResponse, WeatherInfo,
    PaginatedWardrobeItemResponse, ClothingType
)


class WardrobeService:
    """Service for wardrobe item management.
    
    Validates: Requirements 19.1-19.6
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WardrobeRepository(session)
        self.wear_log_repo = WearLogRepository(session)
    
    async def add_item(
        self,
        user_id: uuid.UUID,
        image_url: str,
        data: WardrobeItemCreate,
        processed_image_url: Optional[str] = None,
    ) -> WardrobeItem:
        """Add a new wardrobe item.
        
        Validates: Requirements 19.1, 19.4
        """
        item = await self.repo.create_item(
            user_id=user_id,
            image_url=image_url,
            processed_image_url=processed_image_url,
            item_type=data.item_type,
            name=data.name,
            primary_color=data.primary_color,
            pattern=data.pattern,
            brand=data.brand,
            price=data.price,
            purchase_date=data.purchase_date,
            occasions=data.occasions,
            notes=data.notes,
        )
        await self.session.commit()
        return item
    
    async def get_item(self, item_id: uuid.UUID, user_id: uuid.UUID) -> Optional[WardrobeItem]:
        """Get a wardrobe item by ID."""
        return await self.repo.get_item_by_id(item_id, user_id)
    
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
        """Get wardrobe items with filters."""
        return await self.repo.get_items(
            user_id=user_id,
            item_type=item_type,
            primary_color=primary_color,
            pattern=pattern,
            occasion=occasion,
            in_laundry=in_laundry,
            min_price=min_price,
            max_price=max_price,
            page=page,
            page_size=page_size,
        )
    
    async def update_item(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        data: WardrobeItemUpdate,
    ) -> Optional[WardrobeItem]:
        """Update a wardrobe item."""
        item = await self.repo.get_item_by_id(item_id, user_id)
        if not item:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        item = await self.repo.update_item(item, **update_data)
        await self.session.commit()
        return item
    
    async def delete_item(self, item_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a wardrobe item."""
        item = await self.repo.get_item_by_id(item_id, user_id)
        if not item:
            return False
        
        await self.repo.delete_item(item)
        await self.session.commit()
        return True
    
    async def set_laundry_status(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        in_laundry: bool,
    ) -> Optional[WardrobeItem]:
        """Set the laundry status of an item.
        
        Validates: Requirements 19.5
        """
        item = await self.repo.get_item_by_id(item_id, user_id)
        if not item:
            return None
        
        item = await self.repo.set_laundry_status(item, in_laundry)
        await self.session.commit()
        return item
    
    async def mark_worn(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        data: WearLogCreate,
    ) -> Optional[WearLog]:
        """Mark an item as worn and create a wear log.
        
        Validates: Requirements 19.6
        """
        item = await self.repo.get_item_by_id(item_id, user_id)
        if not item:
            return None
        
        # Create wear log
        log = await self.wear_log_repo.create_log(
            item_id=item_id,
            worn_date=data.worn_date,
            occasion=data.occasion,
        )
        
        # Update item wear count and last worn
        item.wear_count += 1
        item.last_worn = datetime.now()
        
        await self.session.commit()
        return log
    
    async def get_wear_logs(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[WearLog]:
        """Get wear logs for an item."""
        item = await self.repo.get_item_by_id(item_id, user_id)
        if not item:
            return []
        
        return await self.wear_log_repo.get_logs_for_item(item_id, start_date, end_date)
    
    async def get_statistics(self, user_id: uuid.UUID) -> WardrobeStatsResponse:
        """Get wardrobe statistics.
        
        Validates: Requirements 22.1-22.5
        """
        items, total = await self.repo.get_items(user_id, page=1, page_size=1000)
        
        # Calculate statistics
        total_value = Decimal("0")
        items_by_type = {}
        items_by_color = {}
        items_in_laundry = 0
        total_cost_per_wear = Decimal("0")
        items_with_cost = 0
        
        six_months_ago = datetime.now() - timedelta(days=180)
        unworn_items = []
        
        for item in items:
            # Total value
            if item.price:
                total_value += item.price
            
            # By type
            items_by_type[item.item_type] = items_by_type.get(item.item_type, 0) + 1
            
            # By color
            if item.primary_color:
                items_by_color[item.primary_color] = items_by_color.get(item.primary_color, 0) + 1
            
            # Laundry count
            if item.in_laundry:
                items_in_laundry += 1
            
            # Cost per wear
            if item.price and item.wear_count > 0:
                total_cost_per_wear += item.price / item.wear_count
                items_with_cost += 1
            
            # Unworn items (6+ months)
            if not item.last_worn or item.last_worn < six_months_ago:
                unworn_items.append(item)
        
        # Sort by wear count for most/least worn
        sorted_items = sorted(items, key=lambda x: x.wear_count, reverse=True)
        most_worn = sorted_items[:5]
        least_worn = sorted_items[-5:] if len(sorted_items) >= 5 else sorted_items
        
        # Calculate average cost per wear
        avg_cost_per_wear = total_cost_per_wear / items_with_cost if items_with_cost > 0 else None
        
        # Convert to response schemas with stats
        def item_with_stats(item: WardrobeItem) -> WardrobeItemWithStatsResponse:
            cost_per_wear = None
            if item.price and item.wear_count > 0:
                cost_per_wear = item.price / item.wear_count
            
            days_since = None
            if item.last_worn:
                days_since = (datetime.now() - item.last_worn).days
            
            return WardrobeItemWithStatsResponse(
                id=item.id,
                user_id=item.user_id,
                image_url=item.image_url,
                processed_image_url=item.processed_image_url,
                item_type=item.item_type,
                name=item.name,
                primary_color=item.primary_color,
                pattern=item.pattern,
                brand=item.brand,
                price=item.price,
                purchase_date=item.purchase_date,
                in_laundry=item.in_laundry,
                wear_count=item.wear_count,
                last_worn=item.last_worn,
                occasions=item.occasions,
                notes=item.notes,
                created_at=item.created_at,
                updated_at=item.updated_at,
                cost_per_wear=cost_per_wear,
                days_since_last_worn=days_since,
            )
        
        return WardrobeStatsResponse(
            total_items=total,
            total_value=total_value,
            items_by_type=items_by_type,
            items_by_color=items_by_color,
            most_worn_items=[item_with_stats(i) for i in most_worn],
            least_worn_items=[item_with_stats(i) for i in least_worn],
            unworn_items=[WardrobeItemResponse.model_validate(i) for i in unworn_items[:10]],
            items_in_laundry=items_in_laundry,
            average_cost_per_wear=avg_cost_per_wear,
        )


class OutfitService:
    """Service for outfit management.
    
    Validates: Requirements 20.1-20.6
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OutfitRepository(session)
        self.wardrobe_repo = WardrobeRepository(session)
    
    async def create_outfit(
        self,
        user_id: uuid.UUID,
        data: OutfitCreate,
    ) -> Outfit:
        """Create a new outfit.
        
        Validates: Requirements 20.6
        """
        outfit = await self.repo.create_outfit(
            user_id=user_id,
            name=data.name,
            item_ids=data.item_ids,
            occasion=data.occasion,
            notes=data.notes,
        )
        await self.session.commit()
        
        # Reload with items
        return await self.repo.get_outfit_by_id(outfit.id, user_id)
    
    async def get_outfit(self, outfit_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Outfit]:
        """Get an outfit by ID."""
        return await self.repo.get_outfit_by_id(outfit_id, user_id)
    
    async def get_outfits(
        self,
        user_id: uuid.UUID,
        occasion: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Outfit], int]:
        """Get outfits with filters."""
        return await self.repo.get_outfits(user_id, occasion, page, page_size)
    
    async def update_outfit(
        self,
        outfit_id: uuid.UUID,
        user_id: uuid.UUID,
        data: OutfitUpdate,
    ) -> Optional[Outfit]:
        """Update an outfit."""
        outfit = await self.repo.get_outfit_by_id(outfit_id, user_id)
        if not outfit:
            return None
        
        outfit = await self.repo.update_outfit(
            outfit,
            name=data.name,
            occasion=data.occasion,
            item_ids=data.item_ids,
            notes=data.notes,
        )
        await self.session.commit()
        return await self.repo.get_outfit_by_id(outfit_id, user_id)
    
    async def delete_outfit(self, outfit_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete an outfit."""
        outfit = await self.repo.get_outfit_by_id(outfit_id, user_id)
        if not outfit:
            return False
        
        await self.repo.delete_outfit(outfit)
        await self.session.commit()
        return True
    
    async def get_suggestions(
        self,
        user_id: uuid.UUID,
        occasion: Optional[str] = None,
        weather: Optional[WeatherInfo] = None,
    ) -> List[OutfitSuggestionResponse]:
        """Get outfit suggestions based on context.
        
        Validates: Requirements 20.1-20.5
        """
        suggestions = []
        
        # Get available items (not in laundry)
        available_items = await self.wardrobe_repo.get_available_items(
            user_id=user_id,
            occasion=occasion,
        )
        
        if not available_items:
            return suggestions
        
        # Group items by type
        items_by_type = {}
        for item in available_items:
            if item.item_type not in items_by_type:
                items_by_type[item.item_type] = []
            items_by_type[item.item_type].append(item)
        
        # Generate outfit combinations (simplified algorithm)
        tops = items_by_type.get(ClothingType.TOP, [])
        bottoms = items_by_type.get(ClothingType.BOTTOM, [])
        dresses = items_by_type.get(ClothingType.DRESS, [])
        footwear = items_by_type.get(ClothingType.FOOTWEAR, [])
        
        # Suggest top + bottom combinations
        for top in tops[:3]:  # Limit to avoid too many combinations
            for bottom in bottoms[:3]:
                outfit_items = [top, bottom]
                if footwear:
                    outfit_items.append(footwear[0])
                
                # Calculate score based on recency (items not worn recently score higher)
                score = self._calculate_outfit_score(outfit_items)
                
                suggestions.append(OutfitSuggestionResponse(
                    items=[WardrobeItemResponse.model_validate(i) for i in outfit_items],
                    weather=weather,
                    occasion=occasion,
                    score=score,
                ))
        
        # Suggest dresses
        for dress in dresses[:3]:
            outfit_items = [dress]
            if footwear:
                outfit_items.append(footwear[0])
            
            score = self._calculate_outfit_score(outfit_items)
            
            suggestions.append(OutfitSuggestionResponse(
                items=[WardrobeItemResponse.model_validate(i) for i in outfit_items],
                weather=weather,
                occasion=occasion,
                score=score,
            ))
        
        # Sort by score (higher is better)
        suggestions.sort(key=lambda x: x.score, reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _calculate_outfit_score(self, items: List[WardrobeItem]) -> float:
        """Calculate outfit score based on recency and other factors."""
        score = 100.0
        
        for item in items:
            # Penalize recently worn items
            if item.last_worn:
                days_since = (datetime.now() - item.last_worn).days
                if days_since < 7:
                    score -= (7 - days_since) * 5  # Penalize more for very recent
            else:
                score += 10  # Bonus for never worn items
        
        return max(0, score)


class OutfitPlanService:
    """Service for outfit planning.
    
    Validates: Requirements 21.1-21.5
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OutfitPlanRepository(session)
        self.outfit_repo = OutfitRepository(session)
        self.wardrobe_repo = WardrobeRepository(session)
    
    async def create_plan(
        self,
        user_id: uuid.UUID,
        data: OutfitPlanCreate,
    ) -> OutfitPlan:
        """Create an outfit plan.
        
        Validates: Requirements 21.1
        """
        plan = await self.repo.create_plan(
            user_id=user_id,
            outfit_id=data.outfit_id,
            planned_date=data.planned_date,
            event_name=data.event_name,
            notes=data.notes,
        )
        await self.session.commit()
        return await self.repo.get_plan_by_id(plan.id, user_id)
    
    async def get_plan(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> Optional[OutfitPlan]:
        """Get an outfit plan by ID."""
        return await self.repo.get_plan_by_id(plan_id, user_id)
    
    async def get_plans(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_completed: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[OutfitPlan], int]:
        """Get outfit plans with filters."""
        return await self.repo.get_plans(
            user_id, start_date, end_date, is_completed, page, page_size
        )
    
    async def update_plan(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
        data: OutfitPlanUpdate,
    ) -> Optional[OutfitPlan]:
        """Update an outfit plan."""
        plan = await self.repo.get_plan_by_id(plan_id, user_id)
        if not plan:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        plan = await self.repo.update_plan(plan, **update_data)
        await self.session.commit()
        return await self.repo.get_plan_by_id(plan_id, user_id)
    
    async def delete_plan(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete an outfit plan."""
        plan = await self.repo.get_plan_by_id(plan_id, user_id)
        if not plan:
            return False
        
        await self.repo.delete_plan(plan)
        await self.session.commit()
        return True
    
    async def complete_plan(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[OutfitPlan]:
        """Mark a plan as completed and record items as worn.
        
        Validates: Requirements 21.5
        """
        plan = await self.repo.get_plan_by_id(plan_id, user_id)
        if not plan:
            return None
        
        # Mark as completed
        plan.is_completed = True
        
        # Mark all items in the outfit as worn
        if plan.outfit and plan.outfit.items:
            wear_log_repo = WearLogRepository(self.session)
            for outfit_item in plan.outfit.items:
                item = outfit_item.wardrobe_item
                if item:
                    await wear_log_repo.create_log(
                        item_id=item.id,
                        worn_date=plan.planned_date,
                        occasion=plan.outfit.occasion,
                    )
                    item.wear_count += 1
                    item.last_worn = datetime.now()
        
        await self.session.commit()
        return plan
    
    async def check_laundry_conflicts(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[uuid.UUID]:
        """Check for laundry conflicts in a planned outfit.
        
        Validates: Requirements 21.4
        """
        plan = await self.repo.get_plan_by_id(plan_id, user_id)
        if not plan or not plan.outfit:
            return []
        
        conflicts = []
        for outfit_item in plan.outfit.items:
            if outfit_item.wardrobe_item and outfit_item.wardrobe_item.in_laundry:
                conflicts.append(outfit_item.wardrobe_item_id)
        
        return conflicts
    
    async def get_upcoming_plans(self, user_id: uuid.UUID, days: int = 7) -> List[OutfitPlan]:
        """Get upcoming outfit plans for reminders.
        
        Validates: Requirements 21.3
        """
        return await self.repo.get_upcoming_plans(user_id, days)


class PackingListService:
    """Service for packing list management.
    
    Validates: Requirements 23.1-23.5
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PackingListRepository(session)
    
    async def create_list(
        self,
        user_id: uuid.UUID,
        data: PackingListCreate,
    ) -> PackingList:
        """Create a new packing list.
        
        Validates: Requirements 23.1
        """
        packing_list = await self.repo.create_list(
            user_id=user_id,
            name=data.name,
            destination=data.destination,
            trip_start=data.trip_start,
            trip_end=data.trip_end,
            is_template=data.is_template,
            notes=data.notes,
        )
        
        # Add initial items if provided
        if data.items:
            for item_data in data.items:
                await self.repo.add_item(
                    packing_list_id=packing_list.id,
                    wardrobe_item_id=item_data.wardrobe_item_id,
                    custom_item_name=item_data.custom_item_name,
                    quantity=item_data.quantity,
                )
        
        await self.session.commit()
        return await self.repo.get_list_by_id(packing_list.id, user_id)
    
    async def get_list(self, list_id: uuid.UUID, user_id: uuid.UUID) -> Optional[PackingList]:
        """Get a packing list by ID."""
        return await self.repo.get_list_by_id(list_id, user_id)
    
    async def get_lists(
        self,
        user_id: uuid.UUID,
        is_template: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[PackingList], int]:
        """Get packing lists with filters."""
        return await self.repo.get_lists(user_id, is_template, page, page_size)
    
    async def update_list(
        self,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PackingListUpdate,
    ) -> Optional[PackingList]:
        """Update a packing list."""
        packing_list = await self.repo.get_list_by_id(list_id, user_id)
        if not packing_list:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        packing_list = await self.repo.update_list(packing_list, **update_data)
        await self.session.commit()
        return await self.repo.get_list_by_id(list_id, user_id)
    
    async def delete_list(self, list_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a packing list."""
        packing_list = await self.repo.get_list_by_id(list_id, user_id)
        if not packing_list:
            return False
        
        await self.repo.delete_list(packing_list)
        await self.session.commit()
        return True
    
    async def add_item(
        self,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PackingListItemCreate,
    ) -> Optional[PackingListItem]:
        """Add an item to a packing list.
        
        Validates: Requirements 23.2
        """
        packing_list = await self.repo.get_list_by_id(list_id, user_id)
        if not packing_list:
            return None
        
        item = await self.repo.add_item(
            packing_list_id=list_id,
            wardrobe_item_id=data.wardrobe_item_id,
            custom_item_name=data.custom_item_name,
            quantity=data.quantity,
        )
        await self.session.commit()
        return item
    
    async def toggle_packed(
        self,
        list_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        is_packed: bool,
    ) -> Optional[PackingListItem]:
        """Toggle the packed status of an item.
        
        Validates: Requirements 23.3
        """
        packing_list = await self.repo.get_list_by_id(list_id, user_id)
        if not packing_list:
            return None
        
        item = await self.repo.get_item_by_id(item_id, list_id)
        if not item:
            return None
        
        item = await self.repo.update_item_packed_status(item, is_packed)
        await self.session.commit()
        return item
    
    async def remove_item(
        self,
        list_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Remove an item from a packing list."""
        packing_list = await self.repo.get_list_by_id(list_id, user_id)
        if not packing_list:
            return False
        
        item = await self.repo.get_item_by_id(item_id, list_id)
        if not item:
            return False
        
        await self.repo.remove_item(item)
        await self.session.commit()
        return True
    
    async def get_templates(self, user_id: uuid.UUID) -> List[PackingList]:
        """Get all packing list templates.
        
        Validates: Requirements 23.4
        """
        return await self.repo.get_templates(user_id)
    
    async def create_from_template(
        self,
        template_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        destination: Optional[str] = None,
        trip_start: Optional[date] = None,
        trip_end: Optional[date] = None,
    ) -> Optional[PackingList]:
        """Create a new packing list from a template.
        
        Validates: Requirements 23.4
        """
        template = await self.repo.get_list_by_id(template_id, user_id)
        if not template or not template.is_template:
            return None
        
        # Create new list
        new_list = await self.repo.create_list(
            user_id=user_id,
            name=name,
            destination=destination,
            trip_start=trip_start,
            trip_end=trip_end,
            is_template=False,
            notes=template.notes,
        )
        
        # Copy items from template
        for item in template.items:
            await self.repo.add_item(
                packing_list_id=new_list.id,
                wardrobe_item_id=item.wardrobe_item_id,
                custom_item_name=item.custom_item_name,
                quantity=item.quantity,
            )
        
        await self.session.commit()
        return await self.repo.get_list_by_id(new_list.id, user_id)
