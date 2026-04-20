"""API endpoints for wardrobe module.

Validates: Requirements 19.1-19.6, 20.1-20.6, 21.1-21.5, 22.1-22.5, 23.1-23.5
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.services.wardrobe import WardrobeService, OutfitService, OutfitPlanService, PackingListService
from app.schemas.wardrobe import (
    WardrobeItemCreate, WardrobeItemUpdate, WardrobeItemResponse,
    WearLogCreate, WearLogResponse,
    OutfitCreate, OutfitUpdate, OutfitResponse,
    OutfitPlanCreate, OutfitPlanUpdate, OutfitPlanResponse,
    PackingListCreate, PackingListUpdate, PackingListResponse, PackingListItemCreate, PackingListItemResponse,
    WardrobeStatsResponse, OutfitSuggestionRequest, OutfitSuggestionResponse,
    PaginatedWardrobeItemResponse, PaginatedOutfitResponse, PaginatedPackingListResponse,
)

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


# ============================================================================
# Wardrobe Item Endpoints
# ============================================================================

@router.post("/items", response_model=WardrobeItemResponse, status_code=status.HTTP_201_CREATED)
async def create_wardrobe_item(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    item_type: str = Form(...),
    image: UploadFile = File(...),
    name: Optional[str] = Form(None),
    primary_color: Optional[str] = Form(None),
    pattern: Optional[str] = Form(None),
    brand: Optional[str] = Form(None),
    price: Optional[Decimal] = Form(None),
    purchase_date: Optional[date] = Form(None),
    occasions: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    """Create a new wardrobe item with image upload."""
    image_url = f"https://storage.example.com/wardrobe/{current_user.id}/{image.filename}"
    
    occasions_list = None
    if occasions:
        occasions_list = [o.strip() for o in occasions.split(",") if o.strip()]
    
    data = WardrobeItemCreate(
        item_type=item_type,
        name=name,
        primary_color=primary_color,
        pattern=pattern,
        brand=brand,
        price=price,
        purchase_date=purchase_date,
        occasions=occasions_list,
        notes=notes,
    )
    
    service = WardrobeService(session)
    item = await service.add_item(current_user.id, image_url, data)
    return WardrobeItemResponse.model_validate(item)


@router.get("/items", response_model=PaginatedWardrobeItemResponse)
async def list_wardrobe_items(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    item_type: Optional[str] = Query(None),
    primary_color: Optional[str] = Query(None),
    pattern: Optional[str] = Query(None),
    occasion: Optional[str] = Query(None),
    in_laundry: Optional[bool] = Query(None),
    min_price: Optional[Decimal] = Query(None),
    max_price: Optional[Decimal] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List wardrobe items with filters."""
    service = WardrobeService(session)
    items, total = await service.get_items(
        user_id=current_user.id,
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
    
    return PaginatedWardrobeItemResponse.create(
        items=[WardrobeItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/items/{item_id}", response_model=WardrobeItemResponse)
async def get_wardrobe_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get a wardrobe item by ID."""
    service = WardrobeService(session)
    item = await service.get_item(item_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return WardrobeItemResponse.model_validate(item)


@router.patch("/items/{item_id}", response_model=WardrobeItemResponse)
async def update_wardrobe_item(
    item_id: uuid.UUID,
    data: WardrobeItemUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Update a wardrobe item."""
    service = WardrobeService(session)
    item = await service.update_item(item_id, current_user.id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return WardrobeItemResponse.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wardrobe_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Delete a wardrobe item."""
    service = WardrobeService(session)
    deleted = await service.delete_item(item_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")


@router.post("/items/{item_id}/laundry", response_model=WardrobeItemResponse)
async def set_laundry_status(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    in_laundry: bool = Query(...),
):
    """Set the laundry status of an item."""
    service = WardrobeService(session)
    item = await service.set_laundry_status(item_id, current_user.id, in_laundry)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return WardrobeItemResponse.model_validate(item)


@router.post("/items/{item_id}/worn", response_model=WearLogResponse)
async def mark_item_worn(
    item_id: uuid.UUID,
    data: WearLogCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Mark an item as worn."""
    service = WardrobeService(session)
    log = await service.mark_worn(item_id, current_user.id, data)
    if not log:
        raise HTTPException(status_code=404, detail="Item not found")
    return WearLogResponse.model_validate(log)


@router.get("/items/{item_id}/wear-logs", response_model=List[WearLogResponse])
async def get_wear_logs(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get wear logs for an item."""
    service = WardrobeService(session)
    logs = await service.get_wear_logs(item_id, current_user.id, start_date, end_date)
    return [WearLogResponse.model_validate(log) for log in logs]


@router.get("/statistics", response_model=WardrobeStatsResponse)
async def get_wardrobe_statistics(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get wardrobe statistics."""
    service = WardrobeService(session)
    return await service.get_statistics(current_user.id)


# ============================================================================
# Outfit Endpoints
# ============================================================================

@router.post("/outfits", response_model=OutfitResponse, status_code=status.HTTP_201_CREATED)
async def create_outfit(
    data: OutfitCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Create a new outfit."""
    service = OutfitService(session)
    outfit = await service.create_outfit(current_user.id, data)
    return OutfitResponse.model_validate(outfit)


@router.get("/outfits", response_model=PaginatedOutfitResponse)
async def list_outfits(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    occasion: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List outfits with filters."""
    service = OutfitService(session)
    outfits, total = await service.get_outfits(current_user.id, occasion, page, page_size)
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedOutfitResponse(
        items=[OutfitResponse.model_validate(o) for o in outfits],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/outfits/suggestions", response_model=List[OutfitSuggestionResponse])
async def get_outfit_suggestions(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    occasion: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
):
    """Get outfit suggestions based on context."""
    weather = None
    service = OutfitService(session)
    return await service.get_suggestions(current_user.id, occasion, weather)


@router.get("/outfits/{outfit_id}", response_model=OutfitResponse)
async def get_outfit(
    outfit_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get an outfit by ID."""
    service = OutfitService(session)
    outfit = await service.get_outfit(outfit_id, current_user.id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitResponse.model_validate(outfit)


@router.patch("/outfits/{outfit_id}", response_model=OutfitResponse)
async def update_outfit(
    outfit_id: uuid.UUID,
    data: OutfitUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Update an outfit."""
    service = OutfitService(session)
    outfit = await service.update_outfit(outfit_id, current_user.id, data)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitResponse.model_validate(outfit)


@router.delete("/outfits/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(
    outfit_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Delete an outfit."""
    service = OutfitService(session)
    deleted = await service.delete_outfit(outfit_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Outfit not found")


# ============================================================================
# Outfit Plan Endpoints
# ============================================================================

@router.post("/plans", response_model=OutfitPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_outfit_plan(
    data: OutfitPlanCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Create an outfit plan."""
    service = OutfitPlanService(session)
    plan = await service.create_plan(current_user.id, data)
    return OutfitPlanResponse.model_validate(plan)


@router.get("/plans")
async def list_outfit_plans(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    is_completed: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List outfit plans with filters."""
    service = OutfitPlanService(session)
    plans, total = await service.get_plans(
        current_user.id, start_date, end_date, is_completed, page, page_size
    )
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": [OutfitPlanResponse.model_validate(p) for p in plans],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/plans/{plan_id}", response_model=OutfitPlanResponse)
async def get_outfit_plan(
    plan_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get an outfit plan by ID."""
    service = OutfitPlanService(session)
    plan = await service.get_plan(plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    conflicts = await service.check_laundry_conflicts(plan_id, current_user.id)
    response = OutfitPlanResponse.model_validate(plan)
    response.laundry_conflicts = conflicts
    return response


@router.patch("/plans/{plan_id}", response_model=OutfitPlanResponse)
async def update_outfit_plan(
    plan_id: uuid.UUID,
    data: OutfitPlanUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Update an outfit plan."""
    service = OutfitPlanService(session)
    plan = await service.update_plan(plan_id, current_user.id, data)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return OutfitPlanResponse.model_validate(plan)


@router.post("/plans/{plan_id}/complete", response_model=OutfitPlanResponse)
async def complete_outfit_plan(
    plan_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Mark an outfit plan as completed."""
    service = OutfitPlanService(session)
    plan = await service.complete_plan(plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return OutfitPlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit_plan(
    plan_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Delete an outfit plan."""
    service = OutfitPlanService(session)
    deleted = await service.delete_plan(plan_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan not found")


# ============================================================================
# Packing List Endpoints
# ============================================================================

@router.post("/packing-lists", response_model=PackingListResponse, status_code=status.HTTP_201_CREATED)
async def create_packing_list(
    data: PackingListCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Create a new packing list."""
    service = PackingListService(session)
    packing_list = await service.create_list(current_user.id, data)
    return PackingListResponse.model_validate(packing_list)


@router.get("/packing-lists", response_model=PaginatedPackingListResponse)
async def list_packing_lists(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    is_template: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List packing lists with filters."""
    service = PackingListService(session)
    lists, total = await service.get_lists(current_user.id, is_template, page, page_size)
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedPackingListResponse(
        items=[PackingListResponse.model_validate(l) for l in lists],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/packing-lists/templates", response_model=List[PackingListResponse])
async def get_packing_list_templates(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get all packing list templates."""
    service = PackingListService(session)
    templates = await service.get_templates(current_user.id)
    return [PackingListResponse.model_validate(t) for t in templates]


@router.post("/packing-lists/from-template/{template_id}", response_model=PackingListResponse)
async def create_from_template(
    template_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    name: str = Query(...),
    destination: Optional[str] = Query(None),
    trip_start: Optional[date] = Query(None),
    trip_end: Optional[date] = Query(None),
):
    """Create a packing list from a template."""
    service = PackingListService(session)
    packing_list = await service.create_from_template(
        template_id, current_user.id, name, destination, trip_start, trip_end
    )
    if not packing_list:
        raise HTTPException(status_code=404, detail="Template not found")
    return PackingListResponse.model_validate(packing_list)


@router.get("/packing-lists/{list_id}", response_model=PackingListResponse)
async def get_packing_list(
    list_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get a packing list by ID."""
    service = PackingListService(session)
    packing_list = await service.get_list(list_id, current_user.id)
    if not packing_list:
        raise HTTPException(status_code=404, detail="Packing list not found")
    return PackingListResponse.model_validate(packing_list)


@router.patch("/packing-lists/{list_id}", response_model=PackingListResponse)
async def update_packing_list(
    list_id: uuid.UUID,
    data: PackingListUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Update a packing list."""
    service = PackingListService(session)
    packing_list = await service.update_list(list_id, current_user.id, data)
    if not packing_list:
        raise HTTPException(status_code=404, detail="Packing list not found")
    return PackingListResponse.model_validate(packing_list)


@router.delete("/packing-lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_packing_list(
    list_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Delete a packing list."""
    service = PackingListService(session)
    deleted = await service.delete_list(list_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Packing list not found")


@router.post("/packing-lists/{list_id}/items", response_model=PackingListItemResponse)
async def add_packing_list_item(
    list_id: uuid.UUID,
    data: PackingListItemCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Add an item to a packing list."""
    service = PackingListService(session)
    item = await service.add_item(list_id, current_user.id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Packing list not found")
    return PackingListItemResponse.model_validate(item)


@router.patch("/packing-lists/{list_id}/items/{item_id}/packed", response_model=PackingListItemResponse)
async def toggle_item_packed(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    is_packed: bool = Query(...),
):
    """Toggle the packed status of an item."""
    service = PackingListService(session)
    item = await service.toggle_packed(list_id, item_id, current_user.id, is_packed)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return PackingListItemResponse.model_validate(item)


@router.delete("/packing-lists/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_packing_list_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Remove an item from a packing list."""
    service = PackingListService(session)
    removed = await service.remove_item(list_id, item_id, current_user.id)
    if not removed:
        raise HTTPException(status_code=404, detail="Item not found")
