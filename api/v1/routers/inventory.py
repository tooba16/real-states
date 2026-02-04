from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.inventory import Inventory, InventoryStatus, UnitType, CategoryType
from models.user import User, UserRole
from models.project import Project
from models.phase_block import PhaseBlock
from models.investor import Investor
from schemas.inventory import InventoryCreate, InventoryUpdate, InventoryPublic
from schemas.responses import InventoryResponse, APIResponse
from core.config import settings
from utils.id_generator import generate_unique_inventory_id
from business_logic.inventory_rules import InventoryBusinessLogic

router = APIRouter()

@router.get("/", response_model=InventoryResponse)
async def get_inventory(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    project_id: Optional[uuid.UUID] = Query(None),
    phase_block_id: Optional[uuid.UUID] = Query(None),
    unit_type: Optional[UnitType] = Query(None),
    status: Optional[InventoryStatus] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get list of inventory items with optional filtering
    """
    query = select(Inventory)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all inventory
        pass
    elif current_user.role == UserRole.INVESTOR:
        # Investor can only see their assigned inventory
        query = query.filter(Inventory.investor_id == current_user.investor_id)
    else:
        # Other roles can see inventory in their builder's projects
        query = query.join(Project).filter(Project.builder_id == current_user.builder_id)

    # Apply additional filters
    if project_id:
        query = query.filter(Inventory.project_id == project_id)

    if phase_block_id:
        query = query.filter(Inventory.phase_block_id == phase_block_id)

    if unit_type:
        query = query.filter(Inventory.unit_type == unit_type)

    if status:
        query = query.filter(Inventory.status == status)

    if min_price:
        query = query.filter(Inventory.price >= min_price)

    if max_price:
        query = query.filter(Inventory.price <= max_price)

    if search:
        query = query.filter(
            or_(
                Inventory.unit_number.contains(search),
                Inventory.unit_type.contains(search.lower())
            )
        )

    # Count total for pagination
    count_query = select(Inventory).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    inventory_items = result.scalars().all()

    return InventoryResponse(
        success=True,
        message="Inventory retrieved successfully",
        data={
            "inventory": [item.to_dict() for item in inventory_items],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{inventory_id}", response_model=InventoryResponse)
async def get_inventory_item(
    inventory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific inventory item by ID
    """
    query = select(Inventory).filter(Inventory.id == inventory_id)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see any inventory
        pass
    elif current_user.role == UserRole.INVESTOR:
        # Investor can only see their assigned inventory
        query = query.filter(Inventory.investor_id == current_user.investor_id)
    else:
        # Others can only see inventory in their builder's projects
        query = query.join(Project).filter(Project.builder_id == current_user.builder_id)

    result = await db.execute(query)
    inventory_item = result.scalar_one_or_none()

    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )

    return InventoryResponse(
        success=True,
        message="Inventory item retrieved successfully",
        data=inventory_item.to_dict()
    )

@router.post("/", response_model=InventoryResponse)
async def create_inventory(
    inventory_data: InventoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Create a new inventory item
    """
    # Verify project exists and belongs to current user's builder
    project_result = await db.execute(
        select(Project).filter(Project.id == inventory_data.project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create inventory for project in different builder organization"
        )

    # Verify phase block exists if provided
    if inventory_data.phase_block_id:
        phase_block_result = await db.execute(
            select(PhaseBlock).filter(PhaseBlock.id == inventory_data.phase_block_id)
        )
        phase_block = phase_block_result.scalar_one_or_none()

        if not phase_block or phase_block.project_id != inventory_data.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phase block for this project"
            )

    # Verify investor exists if provided
    if inventory_data.investor_id:
        investor_result = await db.execute(
            select(Investor).filter(Investor.id == inventory_data.investor_id)
        )
        investor = investor_result.scalar_one_or_none()

        if not investor or investor.builder_id != project.builder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid investor for this builder"
            )

    # Generate unique external ID
    external_id = await generate_unique_inventory_id(db)

    # Create inventory item
    inventory = Inventory(
        unit_number=inventory_data.unit_number,
        unit_type=inventory_data.unit_type,
        category=inventory_data.category,
        size=inventory_data.size,
        price=inventory_data.price,
        project_id=inventory_data.project_id,
        phase_block_id=inventory_data.phase_block_id,
        investor_locked=inventory_data.investor_locked,
        investor_id=inventory_data.investor_id,
        remarks=inventory_data.remarks,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(inventory)
    await db.commit()
    await db.refresh(inventory)

    return InventoryResponse(
        success=True,
        message="Inventory item created successfully",
        data=inventory.to_dict()
    )

@router.put("/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(
    inventory_id: uuid.UUID,
    inventory_update: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing inventory item
    """
    result = await db.execute(
        select(Inventory).filter(Inventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )

    # Check permissions
    project_result = await db.execute(
        select(Project).filter(Project.id == inventory.project_id)
    )
    project = project_result.scalar_one_or_none()

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this inventory item"
        )

    # Prevent changing status if investor locked and not master admin
    if inventory.investor_locked and inventory_update.status and current_user.role != UserRole.MASTER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update status of investor locked inventory"
        )

    # Update fields if provided
    update_data = inventory_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory, field, value)

    inventory.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(inventory)

    return InventoryResponse(
        success=True,
        message="Inventory item updated successfully",
        data=inventory.to_dict()
    )

@router.patch("/{inventory_id}/lock", response_model=InventoryResponse)
async def lock_inventory(
    inventory_id: uuid.UUID,
    lock: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Lock or unlock inventory item for investor consent
    """
    result = await db.execute(
        select(Inventory).filter(Inventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )

    # Check permissions
    project_result = await db.execute(
        select(Project).filter(Project.id == inventory.project_id)
    )
    project = project_result.scalar_one_or_none()

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to lock/unlock this inventory item"
        )

    inventory.investor_locked = lock
    inventory.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(inventory)

    action = "locked" if lock else "unlocked"
    return InventoryResponse(
        success=True,
        message=f"Inventory item {action} successfully",
        data=inventory.to_dict()
    )

@router.patch("/{inventory_id}/hold", response_model=InventoryResponse)
async def place_hold(
    inventory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("sales_agent"))
):
    """
    Place a hold on an inventory item
    """
    result = await db.execute(
        select(Inventory).filter(Inventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )

    # Check permissions
    project_result = await db.execute(
        select(Project).filter(Project.id == inventory.project_id)
    )
    project = project_result.scalar_one_or_none()

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to place hold on this inventory item"
        )

    # Validate inventory availability using business logic
    await InventoryBusinessLogic.validate_inventory_availability(db, inventory_id)

    # Check if inventory is available
    if inventory.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inventory item is not available (current status: {inventory.status})"
        )

    # Check if investor consent is required
    if inventory.investor_locked:
        await InventoryBusinessLogic.validate_investor_consent(db, inventory_id)

    # Place hold
    inventory.status = "on_hold"
    inventory.hold_expiry_date = datetime.utcnow() + timedelta(hours=settings.DEFAULT_HOLD_EXPIRY_HOURS)
    inventory.booked_by_id = current_user.id
    inventory.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(inventory)

    return InventoryResponse(
        success=True,
        message="Hold placed successfully",
        data=inventory.to_dict()
    )

@router.delete("/{inventory_id}", response_model=APIResponse)
async def delete_inventory(
    inventory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete an inventory item (soft delete by changing status)
    """
    result = await db.execute(
        select(Inventory).filter(Inventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )

    # Check permissions
    project_result = await db.execute(
        select(Project).filter(Project.id == inventory.project_id)
    )
    project = project_result.scalar_one_or_none()

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this inventory item"
        )

    # Prevent deletion if inventory is booked or sold
    if inventory.status in ["booked", "sold"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete inventory item that is booked or sold"
        )

    # Soft delete by setting status to inactive
    inventory.status = "inactive"
    inventory.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Inventory item deactivated successfully"
    )