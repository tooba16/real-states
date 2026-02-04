from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.customer import Customer
from models.user import User, UserRole
from models.booking import Booking
from models.project import Project
from schemas.customer import CustomerCreate, CustomerUpdate, CustomerPublic
from schemas.responses import APIResponse
from utils.id_generator import generate_unique_customer_id

router = APIRouter()

@router.get("/", response_model=APIResponse)
async def get_customers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Get list of customers with optional filtering
    """
    query = select(Customer)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all customers
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only see customers associated with bookings in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view customers"
        )

    # Apply additional filters
    if search:
        query = query.filter(
            or_(
                Customer.first_name.contains(search),
                Customer.last_name.contains(search),
                Customer.father_name.contains(search),
                Customer.cnic.contains(search),
                Customer.contact_number.contains(search)
            )
        )

    if city:
        query = query.filter(Customer.city == city)

    if status:
        query = query.filter(Customer.status == status)

    # Count total for pagination
    count_query = select(Customer).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    # Remove duplicates
    seen_ids = set()
    unique_customers = []
    for customer in customers:
        if customer.id not in seen_ids:
            unique_customers.append(customer)
            seen_ids.add(customer.id)

    return APIResponse(
        success=True,
        message="Customers retrieved successfully",
        data={
            "customers": [customer.to_dict() for customer in unique_customers],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{customer_id}", response_model=APIResponse)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific customer by ID
    """
    query = select(Customer).filter(Customer.id == customer_id)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see any customer
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SALES_AGENT]:
        # Staff can only see customers associated with bookings in their builder's projects
        query = query.join(Booking).join(Project).filter(Project.builder_id == current_user.builder_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view customers"
        )

    result = await db.execute(query)
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return APIResponse(
        success=True,
        message="Customer retrieved successfully",
        data=customer.to_dict()
    )

@router.post("/", response_model=APIResponse)
async def create_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("sales_agent"))
):
    """
    Create a new customer
    """
    # Check if CNIC already exists
    if customer_data.cnic:
        cnic_result = await db.execute(
            select(Customer).filter(Customer.cnic == customer_data.cnic)
        )
        existing_customer = cnic_result.scalar_one_or_none()

        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNIC already registered"
            )

    # Generate unique external ID
    external_id = await generate_unique_customer_id(db)

    # Create customer
    customer = Customer(
        first_name=customer_data.first_name,
        last_name=customer_data.last_name,
        father_name=customer_data.father_name,
        cnic=customer_data.cnic,
        contact_number=customer_data.contact_number,
        alternate_contact=customer_data.alternate_contact,
        email=customer_data.email,
        address=customer_data.address,
        city=customer_data.city,
        country=customer_data.country,
        occupation=customer_data.occupation,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return APIResponse(
        success=True,
        message="Customer created successfully",
        data=customer.to_dict()
    )

@router.put("/{customer_id}", response_model=APIResponse)
async def update_customer(
    customer_id: uuid.UUID,
    customer_update: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("sales_agent"))
):
    """
    Update an existing customer
    """
    result = await db.execute(
        select(Customer).filter(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Check if CNIC already exists for another customer
    if customer_update.cnic and customer_update.cnic != customer.cnic:
        cnic_result = await db.execute(
            select(Customer).filter(
                and_(
                    Customer.cnic == customer_update.cnic,
                    Customer.id != customer_id
                )
            )
        )
        existing_customer = cnic_result.scalar_one_or_none()

        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNIC already registered"
            )

    # Update fields if provided
    update_data = customer_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    customer.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(customer)

    return APIResponse(
        success=True,
        message="Customer updated successfully",
        data=customer.to_dict()
    )

@router.delete("/{customer_id}", response_model=APIResponse)
async def delete_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete a customer (soft delete by changing status)
    """
    result = await db.execute(
        select(Customer).filter(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Check if customer has any active bookings
    booking_result = await db.execute(
        select(Booking).filter(
            and_(
                Booking.customer_id == customer_id,
                Booking.booking_status != "cancelled"
            )
        )
    )
    bookings = booking_result.scalars().all()

    if bookings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete customer with active bookings"
        )

    # Soft delete by setting status to inactive
    customer.status = "inactive"
    customer.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Customer deactivated successfully"
    )