from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import date
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.payment import Payment, PaymentMethod, PaymentStatus
from models.booking import Booking, BookingStatus
from models.customer import Customer
from models.user import User, UserRole
from models.project import Project
from schemas.payment import PaymentCreate, PaymentUpdate, PaymentPublic
from schemas.responses import PaymentResponse, APIResponse
from utils.id_generator import generate_unique_payment_id

router = APIRouter()

@router.get("/", response_model=PaymentResponse)
async def get_payments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    booking_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get list of payments with optional filtering
    """
    query = select(Payment)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all payments
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only see payments for bookings in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view payments"
        )

    # Apply additional filters
    if booking_id:
        query = query.filter(Payment.booking_id == booking_id)

    if customer_id:
        query = query.filter(Payment.customer_id == customer_id)

    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)

    if payment_status:
        query = query.filter(Payment.payment_status == payment_status)

    if start_date:
        query = query.filter(Payment.payment_date >= start_date)

    if end_date:
        query = query.filter(Payment.payment_date <= end_date)

    if search:
        query = query.filter(
            or_(
                Payment.reference_number.contains(search),
                Payment.remarks.contains(search)
            )
        )

    # Count total for pagination
    count_query = select(Payment).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    payments = result.scalars().all()

    return PaymentResponse(
        success=True,
        message="Payments retrieved successfully",
        data={
            "payments": [payment.to_dict() for payment in payments],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific payment by ID
    """
    query = select(Payment).filter(Payment.id == payment_id)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see any payment
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only see payments for bookings in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view payments"
        )

    result = await db.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    return PaymentResponse(
        success=True,
        message="Payment retrieved successfully",
        data=payment.to_dict()
    )

@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("sales_agent"))
):
    """
    Create a new payment
    """
    # Verify booking exists and belongs to current user's builder
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == payment_data.booking_id)
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
            detail="Cannot create payment for booking in different builder organization"
        )

    # Verify customer exists
    customer_result = await db.execute(
        select(Customer).filter(Customer.id == payment_data.customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer not found"
        )

    # Verify customer matches booking
    if booking.customer_id != payment_data.customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer does not match booking"
        )

    # Verify booking is not cancelled
    if booking.booking_status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create payment for cancelled booking"
        )

    # Generate unique external ID
    external_id = await generate_unique_payment_id(db)

    # Create payment
    payment = Payment(
        booking_id=payment_data.booking_id,
        customer_id=payment_data.customer_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        payment_date=payment_data.payment_date,
        reference_number=payment_data.reference_number,
        cheque_number=payment_data.cheque_number if hasattr(payment_data, 'cheque_number') else None,
        bank_name=payment_data.bank_name if hasattr(payment_data, 'bank_name') else None,
        remarks=payment_data.remarks,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return PaymentResponse(
        success=True,
        message="Payment created successfully",
        data=payment.to_dict()
    )

@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: uuid.UUID,
    payment_update: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing payment
    """
    result = await db.execute(
        select(Payment).filter(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == payment.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this payment not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this payment"
        )

    # Update fields if provided
    update_data = payment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)

    payment.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(payment)

    return PaymentResponse(
        success=True,
        message="Payment updated successfully",
        data=payment.to_dict()
    )

@router.delete("/{payment_id}", response_model=APIResponse)
async def delete_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete a payment (soft delete by changing status)
    """
    result = await db.execute(
        select(Payment).filter(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Verify booking and check permissions
    booking_result = await db.execute(
        select(Booking).filter(Booking.id == payment.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking for this payment not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and booking.project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this payment"
        )

    # Only allow deletion if payment status is pending
    if payment.payment_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete payment that is not pending"
        )

    # Soft delete by setting status to rejected
    payment.payment_status = "rejected"
    payment.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Payment deleted successfully"
    )