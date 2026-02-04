from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import date
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.installment import Installment, InstallmentDueStatus
from models.booking import Booking, BookingStatus
from models.user import User, UserRole
from models.project import Project
from schemas.installment import InstallmentCreate, InstallmentUpdate, InstallmentPublic
from schemas.responses import APIResponse
from utils.id_generator import generate_unique_installment_id

router = APIRouter()

@router.get("/", response_model=APIResponse)
async def get_installments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    booking_id: Optional[uuid.UUID] = Query(None),
    due_status: Optional[InstallmentDueStatus] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get list of installments with optional filtering
    """
    query = select(Installment)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all installments
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only see installments for bookings in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view installments"
        )

    # Apply additional filters
    if booking_id:
        query = query.filter(Installment.booking_id == booking_id)

    if due_status:
        query = query.filter(Installment.due_status == due_status)

    if start_date:
        query = query.filter(Installment.due_date >= start_date)

    if end_date:
        query = query.filter(Installment.due_date <= end_date)

    if search:
        query = query.filter(
            or_(
                func.cast(Installment.installment_number, db.String).contains(search),
                Installment.remarks.contains(search)
            )
        )

    # Count total for pagination
    count_query = select(Installment).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    installments = result.scalars().all()

    return APIResponse(
        success=True,
        message="Installments retrieved successfully",
        data={
            "installments": [installment.to_dict() for installment in installments],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{installment_id}", response_model=APIResponse)
async def get_installment(
    installment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific installment by ID
    """
    query = select(Installment).filter(Installment.id == installment_id)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see any installment
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only see installments for bookings in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view installments"
        )

    result = await db.execute(query)
    installment = result.scalar_one_or_none()

    if not installment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installment not found"
        )

    return APIResponse(
        success=True,
        message="Installment retrieved successfully",
        data=installment.to_dict()
    )

@router.post("/", response_model=APIResponse)
async def create_installment(
    installment_data: InstallmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Create a new installment
    """
    # Verify booking exists and belongs to current user's builder
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == installment_data.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking not found"
        )

    # Verify project exists and belongs to same builder as booking
    project_result = await db.execute(
        select(Project).filter(Project.id == booking.project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project or project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create installment for booking in different builder organization"
        )

    # Check if installment number already exists for this booking
    existing_installment_result = await db.execute(
        select(Installment).filter(
            and_(
                Installment.booking_id == installment_data.booking_id,
                Installment.installment_number == installment_data.installment_number
            )
        )
    )
    existing_installment = existing_installment_result.scalar_one_or_none()

    if existing_installment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Installment number already exists for this booking"
        )

    # Generate unique external ID
    external_id = await generate_unique_installment_id(db)

    # Create installment
    installment = Installment(
        booking_id=installment_data.booking_id,
        installment_number=installment_data.installment_number,
        due_date=installment_data.due_date,
        amount=installment_data.amount,
        remarks=installment_data.remarks,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(installment)
    await db.commit()
    await db.refresh(installment)

    return APIResponse(
        success=True,
        message="Installment created successfully",
        data=installment.to_dict()
    )

@router.put("/{installment_id}", response_model=APIResponse)
async def update_installment(
    installment_id: uuid.UUID,
    installment_update: InstallmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing installment
    """
    result = await db.execute(
        select(Installment).filter(Installment.id == installment_id)
    )
    installment = result.scalar_one_or_none()

    if not installment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installment not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == installment.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this installment not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this installment"
        )

    # Update fields if provided
    update_data = installment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(installment, field, value)

    installment.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(installment)

    return APIResponse(
        success=True,
        message="Installment updated successfully",
        data=installment.to_dict()
    )

@router.patch("/{installment_id}/pay", response_model=APIResponse)
async def pay_installment(
    installment_id: uuid.UUID,
    amount: float = Query(..., gt=0, description="Amount being paid"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("sales_agent"))
):
    """
    Mark an installment as paid
    """
    result = await db.execute(
        select(Installment).filter(Installment.id == installment_id)
    )
    installment = result.scalar_one_or_none()

    if not installment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installment not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == installment.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this installment not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this installment"
        )

    # Check if installment is already paid
    if installment.due_status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Installment is already paid"
        )

    # Check if amount is valid
    if amount > installment.balance_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount exceeds installment balance ({installment.balance_amount})"
        )

    # Update installment
    installment.paid_amount += amount
    if installment.paid_amount >= installment.amount:
        installment.due_status = "paid"
        installment.paid_date = date.today()
    else:
        installment.due_status = "partial"

    installment.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(installment)

    return APIResponse(
        success=True,
        message="Installment payment recorded successfully",
        data={
            "installment_id": str(installment.id),
            "paid_amount": float(installment.paid_amount),
            "balance_amount": float(installment.balance_amount),
            "status": installment.due_status
        }
    )

@router.delete("/{installment_id}", response_model=APIResponse)
async def delete_installment(
    installment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete an installment (only if not paid)
    """
    result = await db.execute(
        select(Installment).filter(Installment.id == installment_id)
    )
    installment = result.scalar_one_or_none()

    if not installment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installment not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == installment.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this installment not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this installment"
        )

    # Only allow deletion if installment is not paid
    if installment.due_status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete installment that is already paid"
        )

    await db.delete(installment)
    await db.commit()

    return APIResponse(
        success=True,
        message="Installment deleted successfully"
    )