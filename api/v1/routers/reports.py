from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from typing import Optional, Dict, Any
from datetime import date, datetime
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.user import User, UserRole
from models.project import Project
from models.inventory import Inventory
from models.booking import Booking, BookingStatus
from models.payment import Payment, PaymentStatus
from models.customer import Customer
from models.builder import Builder
from schemas.responses import ReportResponse

router = APIRouter()

@router.get("/sales-summary", response_model=ReportResponse)
async def get_sales_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    builder_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get sales summary report
    """
    # Determine builder access based on user role
    effective_builder_id = None
    if current_user.role == UserRole.MASTER_ADMIN:
        if builder_id:
            effective_builder_id = builder_id
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        effective_builder_id = current_user.builder_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view reports"
        )

    # Build query for bookings
    bookings_query = select(Booking).join(Project)

    if effective_builder_id:
        bookings_query = bookings_query.filter(Project.builder_id == effective_builder_id)

    if project_id:
        bookings_query = bookings_query.filter(Booking.project_id == project_id)

    if start_date:
        bookings_query = bookings_query.filter(Booking.booking_date >= start_date)

    if end_date:
        bookings_query = bookings_query.filter(Booking.booking_date <= end_date)

    bookings_query = bookings_query.filter(Booking.booking_status != "cancelled")

    # Execute query
    bookings_result = await db.execute(bookings_query)
    bookings = bookings_result.scalars().all()

    # Calculate summary
    total_bookings = len(bookings)
    total_booking_amount = sum(float(booking.booking_amount) for booking in bookings)

    # Build query for payments
    payments_query = select(Payment).join(Booking).join(Project)

    if effective_builder_id:
        payments_query = payments_query.filter(Project.builder_id == effective_builder_id)

    if project_id:
        payments_query = payments_query.filter(Booking.project_id == project_id)

    if start_date:
        payments_query = payments_query.filter(Payment.payment_date >= start_date)

    if end_date:
        payments_query = payments_query.filter(Payment.payment_date <= end_date)

    payments_query = payments_query.filter(Payment.payment_status == "received")

    # Execute payments query
    payments_result = await db.execute(payments_query)
    payments = payments_result.scalars().all()

    total_payments = sum(float(payment.amount) for payment in payments)
    total_pending = total_booking_amount - total_payments

    summary_data = {
        "summary": {
            "total_sales": total_booking_amount,
            "total_bookings": total_bookings,
            "total_payments": total_payments,
            "pending_amount": total_pending
        },
        "breakdown": {
            "by_status": {},
            "by_project": {},
            "by_month": {}
        }
    }

    # Breakdown by booking status
    status_counts = {}
    for booking in bookings:
        status = booking.booking_status
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts[status] = 1
    summary_data["breakdown"]["by_status"] = status_counts

    # Breakdown by project
    project_totals = {}
    for booking in bookings:
        project_id_str = str(booking.project_id)
        if project_id_str in project_totals:
            project_totals[project_id_str] += float(booking.booking_amount)
        else:
            project_totals[project_id_str] = float(booking.booking_amount)
    summary_data["breakdown"]["by_project"] = project_totals

    return ReportResponse(
        success=True,
        message="Sales summary report retrieved successfully",
        data=summary_data
    )

@router.get("/inventory-status", response_model=ReportResponse)
async def get_inventory_status_report(
    project_id: Optional[uuid.UUID] = Query(None),
    builder_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get inventory status report
    """
    # Determine builder access based on user role
    effective_builder_id = None
    if current_user.role == UserRole.MASTER_ADMIN:
        if builder_id:
            effective_builder_id = builder_id
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        effective_builder_id = current_user.builder_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view reports"
        )

    # Build query for inventory
    inventory_query = select(Inventory).join(Project)

    if effective_builder_id:
        inventory_query = inventory_query.filter(Project.builder_id == effective_builder_id)

    if project_id:
        inventory_query = inventory_query.filter(Inventory.project_id == project_id)

    # Execute query
    inventory_result = await db.execute(inventory_query)
    inventory_items = inventory_result.scalars().all()

    # Calculate status breakdown
    status_counts = {}
    unit_type_counts = {}
    total_value = 0

    for item in inventory_items:
        # Count by status
        status = item.status
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts[status] = 1

        # Count by unit type
        unit_type = item.unit_type
        if unit_type in unit_type_counts:
            unit_type_counts[unit_type] += 1
        else:
            unit_type_counts[unit_type] = 1

        # Add to total value if available
        if item.status == "available":
            total_value += float(item.price)

    report_data = {
        "summary": {
            "total_inventory": len(inventory_items),
            "total_value_of_available": total_value
        },
        "breakdown": {
            "by_status": status_counts,
            "by_unit_type": unit_type_counts
        }
    }

    return ReportResponse(
        success=True,
        message="Inventory status report retrieved successfully",
        data=report_data
    )

@router.get("/customer-ledger", response_model=ReportResponse)
async def get_customer_ledger_report(
    customer_id: uuid.UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get customer ledger report
    """
    # Verify customer belongs to user's builder
    customer_result = await db.execute(
        select(Customer).filter(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Verify access based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can access any customer
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only access customers in their builder's projects
        booking_result = await db.execute(
            select(Booking).filter(Booking.customer_id == customer_id).limit(1)
        )
        booking = booking_result.scalar_one_or_none()

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer not associated with your builder organization"
            )

        project_result = await db.execute(
            select(Project).filter(Project.id == booking.project_id)
        )
        project = project_result.scalar_one_or_none()

        if not project or project.builder_id != current_user.builder_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer not associated with your builder organization"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view reports"
        )

    # Get bookings for customer
    bookings_query = select(Booking).filter(Booking.customer_id == customer_id)

    if start_date:
        bookings_query = bookings_query.filter(Booking.booking_date >= start_date)

    if end_date:
        bookings_query = bookings_query.filter(Booking.booking_date <= end_date)

    bookings_result = await db.execute(bookings_query)
    bookings = bookings_result.scalars().all()

    # Get payments for customer
    payments_query = select(Payment).filter(Payment.customer_id == customer_id)

    if start_date:
        payments_query = payments_query.filter(Payment.payment_date >= start_date)

    if end_date:
        payments_query = payments_query.filter(Payment.payment_date <= end_date)

    payments_query = payments_query.filter(Payment.payment_status == "received")

    payments_result = await db.execute(payments_query)
    payments = payments_result.scalars().all()

    # Calculate ledger summary
    total_bookings = sum(float(booking.booking_amount) for booking in bookings)
    total_payments = sum(float(payment.amount) for payment in payments)
    outstanding_balance = total_bookings - total_payments

    report_data = {
        "customer": customer.to_dict(),
        "ledger": {
            "total_bookings": total_bookings,
            "total_payments": total_payments,
            "outstanding_balance": outstanding_balance
        },
        "transactions": {
            "bookings": [booking.to_dict() for booking in bookings],
            "payments": [payment.to_dict() for payment in payments]
        }
    }

    return ReportResponse(
        success=True,
        message="Customer ledger report retrieved successfully",
        data=report_data
    )

@router.get("/payment-collection", response_model=ReportResponse)
async def get_payment_collection_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    builder_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get payment collection report
    """
    # Determine builder access based on user role
    effective_builder_id = None
    if current_user.role == UserRole.MASTER_ADMIN:
        if builder_id:
            effective_builder_id = builder_id
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        effective_builder_id = current_user.builder_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view reports"
        )

    # Build query for payments
    payments_query = select(Payment).join(Booking).join(Project)

    if effective_builder_id:
        payments_query = payments_query.filter(Project.builder_id == effective_builder_id)

    if project_id:
        payments_query = payments_query.filter(Booking.project_id == project_id)

    if start_date:
        payments_query = payments_query.filter(Payment.payment_date >= start_date)

    if end_date:
        payments_query = payments_query.filter(Payment.payment_date <= end_date)

    payments_query = payments_query.filter(Payment.payment_status == "received")

    # Execute query
    payments_result = await db.execute(payments_query)
    payments = payments_result.scalars().all()

    # Calculate report data
    total_collections = sum(float(payment.amount) for payment in payments)
    payment_methods = {}

    for payment in payments:
        method = payment.payment_method
        if method in payment_methods:
            payment_methods[method] += float(payment.amount)
        else:
            payment_methods[method] = float(payment.amount)

    # Calculate daily collections
    daily_collections = {}
    for payment in payments:
        payment_date_str = payment.payment_date.isoformat()
        if payment_date_str in daily_collections:
            daily_collections[payment_date_str] += float(payment.amount)
        else:
            daily_collections[payment_date_str] = float(payment.amount)

    report_data = {
        "summary": {
            "total_collections": total_collections,
            "total_transactions": len(payments)
        },
        "breakdown": {
            "by_payment_method": payment_methods,
            "by_date": daily_collections
        }
    }

    return ReportResponse(
        success=True,
        message="Payment collection report retrieved successfully",
        data=report_data
    )