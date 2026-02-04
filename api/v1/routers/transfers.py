from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import date
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.transfer import Transfer, TransferStatus
from models.booking import Booking, BookingStatus
from models.inventory import Inventory, InventoryStatus
from models.customer import Customer
from models.user import User, UserRole
from models.project import Project
from schemas.transfer import TransferCreate, TransferUpdate, TransferPublic
from schemas.responses import APIResponse
from core.config import settings
from utils.id_generator import generate_unique_transfer_id

router = APIRouter()

@router.get("/", response_model=APIResponse)
async def get_transfers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    inventory_id: Optional[uuid.UUID] = Query(None),
    booking_id: Optional[uuid.UUID] = Query(None),
    from_customer_id: Optional[uuid.UUID] = Query(None),
    to_customer_id: Optional[uuid.UUID] = Query(None),
    status: Optional[TransferStatus] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get list of transfers with optional filtering
    """
    query = select(Transfer)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all transfers
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        # Super admin and admin can only see transfers in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view transfers"
        )

    # Apply additional filters
    if inventory_id:
        query = query.filter(Transfer.inventory_id == inventory_id)

    if booking_id:
        query = query.filter(Transfer.booking_id == booking_id)

    if from_customer_id:
        query = query.filter(Transfer.from_customer_id == from_customer_id)

    if to_customer_id:
        query = query.filter(Transfer.to_customer_id == to_customer_id)

    if status:
        query = query.filter(Transfer.status == status)

    if search:
        query = query.filter(
            or_(
                Transfer.remarks.contains(search)
            )
        )

    # Count total for pagination
    count_query = select(Transfer).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    transfers = result.scalars().all()

    return APIResponse(
        success=True,
        message="Transfers retrieved successfully",
        data={
            "transfers": [transfer.to_dict() for transfer in transfers],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{transfer_id}", response_model=APIResponse)
async def get_transfer(
    transfer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific transfer by ID
    """
    query = select(Transfer).filter(Transfer.id == transfer_id)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see any transfer
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        # Super admin and admin can only see transfers in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view transfers"
        )

    result = await db.execute(query)
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    return APIResponse(
        success=True,
        message="Transfer retrieved successfully",
        data=transfer.to_dict()
    )

@router.post("/", response_model=APIResponse)
async def create_transfer(
    transfer_data: TransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Create a new transfer request
    """
    # Verify inventory exists and belongs to current user's builder
    inventory_result = await db.execute(
        select(Inventory).filter(Inventory.id == transfer_data.inventory_id)
    )
    inventory = inventory_result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory item not found"
        )

    # Verify project exists and belongs to same builder as inventory
    project_result = await db.execute(
        select(Project).filter(Project.id == inventory.project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project or project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create transfer for inventory in different builder organization"
        )

    # Verify booking exists and belongs to same inventory
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == transfer_data.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking or booking.inventory_id != transfer_data.inventory_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking not found or does not match inventory"
        )

    # Verify from customer exists
    from_customer_result = await db.execute(
        select(Customer).filter(Customer.id == transfer_data.from_customer_id)
    )
    from_customer = from_customer_result.scalar_one_or_none()

    if not from_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="From customer not found"
        )

    # Verify to customer exists
    to_customer_result = await db.execute(
        select(Customer).filter(Customer.id == transfer_data.to_customer_id)
    )
    to_customer = to_customer_result.scalar_one_or_none()

    if not to_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="To customer not found"
        )

    # Check if booking status allows transfer
    if booking.booking_status not in ["booked", "sold"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transfer property with booking status: {booking.booking_status}"
        )

    # Check if inventory status allows transfer
    if inventory.status not in ["booked", "sold"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transfer inventory with status: {inventory.status}"
        )

    # Calculate transfer fee if not provided
    transfer_fee = transfer_data.transfer_fee
    if not transfer_fee:
        transfer_fee = inventory.price * (settings.TRANSFER_FEE_PERCENTAGE / 100)

    # Generate unique external ID
    external_id = await generate_unique_transfer_id(db)

    # Create transfer
    transfer = Transfer(
        inventory_id=transfer_data.inventory_id,
        booking_id=transfer_data.booking_id,
        from_customer_id=transfer_data.from_customer_id,
        to_customer_id=transfer_data.to_customer_id,
        transfer_date=date.today(),
        transfer_fee=transfer_fee,
        remarks=transfer_data.remarks,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)

    return APIResponse(
        success=True,
        message="Transfer request created successfully",
        data=transfer.to_dict()
    )

@router.put("/{transfer_id}", response_model=APIResponse)
async def update_transfer(
    transfer_id: uuid.UUID,
    transfer_update: TransferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing transfer
    """
    result = await db.execute(
        select(Transfer).filter(Transfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == transfer.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this transfer not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this transfer"
        )

    # Check if transfer can be updated (only pending transfers)
    if transfer.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update transfer that is not in pending status"
        )

    # Update fields if provided
    update_data = transfer_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transfer, field, value)

    transfer.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(transfer)

    return APIResponse(
        success=True,
        message="Transfer updated successfully",
        data=transfer.to_dict()
    )

@router.patch("/{transfer_id}/approve", response_model=APIResponse)
async def approve_transfer(
    transfer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Approve a transfer request
    """
    result = await db.execute(
        select(Transfer).filter(Transfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == transfer.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this transfer not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to approve this transfer"
        )

    # Check if transfer is in pending status
    if transfer.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer is not in pending status"
        )

    # Update transfer status
    transfer.status = "approved"
    transfer.approved_by_id = current_user.id
    transfer.updated_by_id = current_user.id

    # Update booking to reflect new customer
    booking.customer_id = transfer.to_customer_id
    booking.updated_by_id = current_user.id

    # Update inventory to reflect new customer (if applicable)
    inventory_result = await db.execute(
        select(Inventory).filter(Inventory.id == transfer.inventory_id)
    )
    inventory = inventory_result.scalar_one_or_none()

    if inventory:
        inventory.booked_by_id = current_user.id
        inventory.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Transfer approved successfully",
        data={
            "transfer_id": str(transfer.id),
            "booking_id": str(transfer.booking_id),
            "from_customer_id": str(transfer.from_customer_id),
            "to_customer_id": str(transfer.to_customer_id),
            "status": transfer.status
        }
    )

@router.patch("/{transfer_id}/complete", response_model=APIResponse)
async def complete_transfer(
    transfer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Complete a transfer
    """
    result = await db.execute(
        select(Transfer).filter(Transfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == transfer.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this transfer not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete this transfer"
        )

    # Check if transfer is approved
    if transfer.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer is not approved"
        )

    # Update transfer status
    transfer.status = "completed"
    transfer.transfer_date = date.today()
    transfer.updated_by_id = current_user.id

    # Update inventory status to reflect new ownership
    inventory_result = await db.execute(
        select(Inventory).filter(Inventory.id == transfer.inventory_id)
    )
    inventory = inventory_result.scalar_one_or_none()

    if inventory:
        # If inventory was booked, update to sold
        if inventory.status == "booked":
            inventory.status = "sold"
        inventory.booked_by_id = current_user.id
        inventory.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Transfer completed successfully",
        data={
            "transfer_id": str(transfer.id),
            "booking_id": str(transfer.booking_id),
            "from_customer_id": str(transfer.from_customer_id),
            "to_customer_id": str(transfer.to_customer_id),
            "status": transfer.status
        }
    )

@router.delete("/{transfer_id}", response_model=APIResponse)
async def delete_transfer(
    transfer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete a transfer (only if pending)
    """
    result = await db.execute(
        select(Transfer).filter(Transfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == transfer.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this transfer not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this transfer"
        )

    # Only allow deletion if transfer is pending
    if transfer.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete transfer that is not pending"
        )

    await db.delete(transfer)
    await db.commit()

    return APIResponse(
        success=True,
        message="Transfer deleted successfully"
    )