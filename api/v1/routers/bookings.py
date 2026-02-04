from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.booking import Booking, BookingStatus, BookingType
from models.inventory import Inventory, InventoryStatus
from models.customer import Customer
from models.user import User, UserRole
from models.project import Project
from schemas.booking import BookingCreate, BookingUpdate, BookingPublic
from schemas.responses import BookingResponse, APIResponse
from utils.id_generator import generate_unique_booking_id

router = APIRouter()

@router.get("/", response_model=BookingResponse)
async def get_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    project_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    status: Optional[BookingStatus] = Query(None),
    booking_type: Optional[BookingType] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get list of bookings with optional filtering
    """
    query = select(Booking)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all bookings
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        # Super admin and admin can only see bookings in their builder's projects
        query = query.join(Project).filter(Project.builder_id == current_user.builder_id)
    elif current_user.role == UserRole.SALES_AGENT:
        # Sales agent can only see bookings they created or in their builder's projects
        query = query.join(Project).filter(
            and_(
                Project.builder_id == current_user.builder_id
            )
        )
    elif current_user.role == UserRole.INVESTOR:
        # Investor can only see bookings related to their assigned inventory
        query = query.join(Inventory).filter(Inventory.investor_id == current_user.investor_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view bookings"
        )

    # Apply additional filters
    if project_id:
        query = query.filter(Booking.project_id == project_id)

    if customer_id:
        query = query.filter(Booking.customer_id == customer_id)

    if status:
        query = query.filter(Booking.booking_status == status)

    if booking_type:
        query = query.filter(Booking.booking_type == booking_type)

    if search:
        query = query.filter(
            or_(
                Booking.booking_reference.contains(search),
                Booking.remarks.contains(search)
            )
        )

    # Count total for pagination
    count_query = select(Booking).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    bookings = result.scalars().all()

    return BookingResponse(
        success=True,
        message="Bookings retrieved successfully",
        data={
            "bookings": [booking.to_dict() for booking in bookings],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific booking by ID
    """
    query = select(Booking).filter(Booking.id == booking_id)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see any booking
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only see bookings in their builder's projects
        query = query.join(Project).filter(Project.builder_id == current_user.builder_id)
    elif current_user.role == UserRole.INVESTOR:
        # Investor can only see bookings related to their assigned inventory
        query = query.join(Inventory).filter(Inventory.investor_id == current_user.investor_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view bookings"
        )

    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    return BookingResponse(
        success=True,
        message="Booking retrieved successfully",
        data=booking.to_dict()
    )

@router.post("/", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("sales_agent"))
):
    """
    Create a new booking
    """
    # Verify inventory exists and belongs to current user's builder
    inventory_result = await db.execute(
        select(Inventory).filter(Inventory.id == booking_data.inventory_id)
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
            detail="Cannot create booking for inventory in different builder organization"
        )

    # Verify customer exists
    customer_result = await db.execute(
        select(Customer).filter(Customer.id == booking_data.customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer not found"
        )

    # Check if inventory is available for booking
    if inventory.status not in ["available", "on_hold"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inventory item is not available for booking (current status: {inventory.status})"
        )

    # If inventory is on hold, check if current user is authorized to convert to booking
    if inventory.status == "on_hold":
        if inventory.booked_by_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the holder or admin can convert a hold to booking"
            )

    # Generate unique external ID
    external_id = await generate_unique_booking_id(db)

    # Create booking
    booking = Booking(
        inventory_id=booking_data.inventory_id,
        customer_id=booking_data.customer_id,
        booking_amount=booking_data.booking_amount,
        booking_type=booking_data.booking_type,
        remarks=booking_data.remarks,
        project_id=inventory.project_id,
        external_id=external_id,
        approved_by_id=current_user.id,
        booking_reference=f"BKG-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
        created_by_id=current_user.id
    )

    # Update inventory status
    inventory.status = "booked"
    inventory.booked_by_id = current_user.id
    inventory.updated_by_id = current_user.id

    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return BookingResponse(
        success=True,
        message="Booking created successfully",
        data=booking.to_dict()
    )

@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: uuid.UUID,
    booking_update: BookingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing booking
    """
    result = await db.execute(
        select(Booking).filter(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Verify project and check permissions
    project_result = await db.execute(
        select(Project).filter(Project.id == booking.project_id)
    )
    project = project_result.scalar_one_or_none()

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this booking"
        )

    # Update fields if provided
    update_data = booking_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(booking, field, value)

    booking.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(booking)

    return BookingResponse(
        success=True,
        message="Booking updated successfully",
        data=booking.to_dict()
    )

@router.patch("/{booking_id}/cancel", response_model=APIResponse)
async def cancel_booking(
    booking_id: uuid.UUID,
    reason: str = Query(..., description="Cancellation reason"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Cancel a booking
    """
    result = await db.execute(
        select(Booking).filter(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Verify project and check permissions
    project_result = await db.execute(
        select(Project).filter(Project.id == booking.project_id)
    )
    project = project_result.scalar_one_or_none()

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this booking"
        )

    # Check if booking can be cancelled
    if booking.booking_status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled"
        )

    # Update booking status
    booking.booking_status = "cancelled"
    booking.cancellation_reason = reason
    booking.cancellation_date = datetime.utcnow()
    booking.cancelled_by_id = current_user.id
    booking.updated_by_id = current_user.id

    # Update inventory status back to available
    inventory_result = await db.execute(
        select(Inventory).filter(Inventory.id == booking.inventory_id)
    )
    inventory = inventory_result.scalar_one_or_none()

    if inventory:
        inventory.status = "available"
        inventory.hold_expiry_date = None
        inventory.booked_by_id = None
        inventory.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Booking cancelled successfully",
        data={
            "booking_id": str(booking.id),
            "inventory_id": str(booking.inventory_id)
        }
    )

@router.delete("/{booking_id}", response_model=APIResponse)
async def delete_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete a booking (only if it's in draft/hold status)
    """
    result = await db.execute(
        select(Booking).filter(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Verify project and check permissions
    project_result = await db.execute(
        select(Project).filter(Project.id == booking.project_id)
    )
    project = project_result.scalar_one_or_none()

    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this booking"
        )

    # Only allow deletion if booking is in hold status
    if booking.booking_status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete booking that is not in hold status"
        )

    # Update inventory status back to available
    inventory_result = await db.execute(
        select(Inventory).filter(Inventory.id == booking.inventory_id)
    )
    inventory = inventory_result.scalar_one_or_none()

    if inventory:
        inventory.status = "available"
        inventory.hold_expiry_date = None
        inventory.booked_by_id = None
        inventory.updated_by_id = current_user.id

    # Delete the booking
    await db.delete(booking)
    await db.commit()

    return APIResponse(
        success=True,
        message="Booking deleted successfully"
    )