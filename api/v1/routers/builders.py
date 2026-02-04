from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_master_admin
from models.builder import Builder
from models.user import User, UserRole
from schemas.builder import BuilderCreate, BuilderUpdate, BuilderPublic
from schemas.responses import BuilderResponse, APIResponse
from utils.id_generator import generate_unique_builder_id

router = APIRouter()

@router.get("/", response_model=BuilderResponse)
async def get_builders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Get list of builders with optional filtering
    """
    query = select(Builder)

    # Master admin can see all builders, others can only see their own
    if current_user.role != UserRole.MASTER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only master admin can access builders"
        )

    # Apply filters
    if search:
        query = query.filter(
            or_(
                Builder.name.contains(search),
                Builder.registration_number.contains(search)
            )
        )

    if status:
        query = query.filter(Builder.status == status)

    # Count total for pagination
    count_query = select(Builder).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    builders = result.scalars().all()

    return BuilderResponse(
        success=True,
        message="Builders retrieved successfully",
        data={
            "builders": [builder.to_dict() for builder in builders],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{builder_id}", response_model=BuilderResponse)
async def get_builder(
    builder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific builder by ID
    """
    # Only master admin can access any builder
    if current_user.role != UserRole.MASTER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only master admin can access builders"
        )

    result = await db.execute(
        select(Builder).filter(Builder.id == builder_id)
    )
    builder = result.scalar_one_or_none()

    if not builder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder not found"
        )

    return BuilderResponse(
        success=True,
        message="Builder retrieved successfully",
        data=builder.to_dict()
    )

@router.post("/", response_model=BuilderResponse)
async def create_builder(
    builder_data: BuilderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_master_admin)
):
    """
    Create a new builder
    """
    # Check if registration number already exists
    if builder_data.registration_number:
        result = await db.execute(
            select(Builder).filter(Builder.registration_number == builder_data.registration_number)
        )
        existing_builder = result.scalar_one_or_none()

        if existing_builder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration number already exists"
            )

    # Generate unique external ID
    external_id = await generate_unique_builder_id(db)

    # Create builder
    builder = Builder(
        name=builder_data.name,
        registration_number=builder_data.registration_number,
        contact_person=builder_data.contact_person,
        contact_email=builder_data.contact_email,
        contact_phone=builder_data.contact_phone,
        address=builder_data.address,
        city=builder_data.city,
        country=builder_data.country,
        logo_url=builder_data.logo_url,
        max_projects=builder_data.max_projects,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(builder)
    await db.commit()
    await db.refresh(builder)

    return BuilderResponse(
        success=True,
        message="Builder created successfully",
        data=builder.to_dict()
    )

@router.put("/{builder_id}", response_model=BuilderResponse)
async def update_builder(
    builder_id: uuid.UUID,
    builder_update: BuilderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_master_admin)
):
    """
    Update an existing builder
    """
    result = await db.execute(
        select(Builder).filter(Builder.id == builder_id)
    )
    builder = result.scalar_one_or_none()

    if not builder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder not found"
        )

    # Check if registration number already exists for another builder
    if builder_update.registration_number:
        result = await db.execute(
            select(Builder).filter(
                and_(
                    Builder.registration_number == builder_update.registration_number,
                    Builder.id != builder_id
                )
            )
        )
        existing_builder = result.scalar_one_or_none()

        if existing_builder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration number already exists"
            )

    # Update fields if provided
    update_data = builder_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(builder, field, value)

    builder.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(builder)

    return BuilderResponse(
        success=True,
        message="Builder updated successfully",
        data=builder.to_dict()
    )

@router.delete("/{builder_id}", response_model=APIResponse)
async def delete_builder(
    builder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_master_admin)
):
    """
    Delete a builder (soft delete by changing status)
    """
    result = await db.execute(
        select(Builder).filter(Builder.id == builder_id)
    )
    builder = result.scalar_one_or_none()

    if not builder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Builder not found"
        )

    # Soft delete by setting status to inactive
    builder.status = "inactive"
    builder.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Builder deactivated successfully"
    )