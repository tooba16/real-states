from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.investor import Investor
from models.user import User, UserRole
from models.builder import Builder
from schemas.investor import InvestorCreate, InvestorUpdate, InvestorPublic
from schemas.responses import APIResponse
from utils.id_generator import generate_unique_investor_id

router = APIRouter()

@router.get("/", response_model=APIResponse)
async def get_investors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    search: Optional[str] = Query(None),
    builder_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Get list of investors with optional filtering
    """
    query = select(Investor)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all investors
        if builder_id:
            query = query.filter(Investor.builder_id == builder_id)
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        # Super admin and admin can only see investors in their builder
        query = query.filter(Investor.builder_id == current_user.builder_id)
    else:
        # Other roles cannot see investors except for their own investor account
        if current_user.role == UserRole.INVESTOR and current_user.investor_id:
            query = query.filter(Investor.id == current_user.investor_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view investors"
            )

    # Apply additional filters
    if search:
        query = query.filter(
            or_(
                Investor.name.contains(search),
                Investor.company_name.contains(search),
                Investor.cnic.contains(search)
            )
        )

    if status:
        query = query.filter(Investor.status == status)

    # Count total for pagination
    count_query = select(Investor).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    investors = result.scalars().all()

    return APIResponse(
        success=True,
        message="Investors retrieved successfully",
        data={
            "investors": [investor.to_dict() for investor in investors],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{investor_id}", response_model=APIResponse)
async def get_investor(
    investor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific investor by ID
    """
    query = select(Investor).filter(Investor.id == investor_id)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see any investor
        pass
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        # Super admin and admin can only see investors in their builder
        query = query.filter(Investor.builder_id == current_user.builder_id)
    elif current_user.role == UserRole.INVESTOR:
        # Investor can only see their own record
        if current_user.investor_id != investor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this investor"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view investors"
        )

    result = await db.execute(query)
    investor = result.scalar_one_or_none()

    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investor not found"
        )

    return APIResponse(
        success=True,
        message="Investor retrieved successfully",
        data=investor.to_dict()
    )

@router.post("/", response_model=APIResponse)
async def create_investor(
    investor_data: InvestorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Create a new investor
    """
    # Verify builder exists and belongs to current user's organization
    builder_result = await db.execute(
        select(Builder).filter(Builder.id == investor_data.builder_id)
    )
    builder = builder_result.scalar_one_or_none()

    if not builder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Builder not found"
        )

    if current_user.role != UserRole.MASTER_ADMIN and builder.id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create investor for different builder organization"
        )

    # Check if CNIC already exists
    if investor_data.cnic:
        cnic_result = await db.execute(
            select(Investor).filter(Investor.cnic == investor_data.cnic)
        )
        existing_investor = cnic_result.scalar_one_or_none()

        if existing_investor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNIC already registered"
            )

    # Generate unique external ID
    external_id = await generate_unique_investor_id(db)

    # Create investor
    investor = Investor(
        name=investor_data.name,
        company_name=investor_data.company_name,
        cnic=investor_data.cnic,
        contact_person=investor_data.contact_person,
        contact_email=investor_data.contact_email,
        contact_phone=investor_data.contact_phone,
        address=investor_data.address,
        city=investor_data.city,
        country=investor_data.country,
        builder_id=investor_data.builder_id,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(investor)
    await db.commit()
    await db.refresh(investor)

    return APIResponse(
        success=True,
        message="Investor created successfully",
        data=investor.to_dict()
    )

@router.put("/{investor_id}", response_model=APIResponse)
async def update_investor(
    investor_id: uuid.UUID,
    investor_update: InvestorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing investor
    """
    result = await db.execute(
        select(Investor).filter(Investor.id == investor_id)
    )
    investor = result.scalar_one_or_none()

    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investor not found"
        )

    # Check permissions
    if current_user.role != UserRole.MASTER_ADMIN and investor.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this investor"
        )

    # Check if CNIC already exists for another investor
    if investor_update.cnic:
        cnic_result = await db.execute(
            select(Investor).filter(
                and_(
                    Investor.cnic == investor_update.cnic,
                    Investor.id != investor_id
                )
            )
        )
        existing_investor = cnic_result.scalar_one_or_none()

        if existing_investor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNIC already registered"
            )

    # Update fields if provided
    update_data = investor_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(investor, field, value)

    investor.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(investor)

    return APIResponse(
        success=True,
        message="Investor updated successfully",
        data=investor.to_dict()
    )

@router.delete("/{investor_id}", response_model=APIResponse)
async def delete_investor(
    investor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete an investor (soft delete by changing status)
    """
    result = await db.execute(
        select(Investor).filter(Investor.id == investor_id)
    )
    investor = result.scalar_one_or_none()

    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investor not found"
        )

    # Check permissions
    if current_user.role != UserRole.MASTER_ADMIN and investor.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this investor"
        )

    # Soft delete by setting status to inactive
    investor.status = "inactive"
    investor.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Investor deactivated successfully"
    )