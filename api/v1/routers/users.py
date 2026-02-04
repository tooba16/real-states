from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role, get_current_master_admin, get_password_hash
from models.user import User, UserRole
from schemas.user import UserCreate, UserUpdate, UserPublic, UserInDB
from schemas.responses import UserResponse, APIResponse

router = APIRouter()

@router.get("/", response_model=UserResponse)
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    builder_id: Optional[uuid.UUID] = Query(None)
):
    """
    Get list of users with optional filtering
    """
    # Build query based on user permissions
    query = select(User)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all users
        if builder_id:
            query = query.filter(User.builder_id == builder_id)
    elif current_user.role == UserRole.SUPER_ADMIN:
        # Super admin can only see users in their builder organization
        query = query.filter(User.builder_id == current_user.builder_id)
    else:
        # Other roles can only see users in their builder and with same or lower role
        query = query.filter(
            and_(
                User.builder_id == current_user.builder_id,
                User.role.in_([UserRole.SALES_AGENT, UserRole.INVESTOR]) if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] else User.id == current_user.id
            )
        )

    # Apply additional filters
    if search:
        query = query.filter(
            or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )

    if role:
        query = query.filter(User.role == role)

    # Count total for pagination
    count_query = select(User).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserResponse(
        success=True,
        message="Users retrieved successfully",
        data={
            "users": [user.to_dict() for user in users],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific user by ID
    """
    # Check permissions
    query = select(User).filter(User.id == user_id)

    if current_user.role != UserRole.MASTER_ADMIN:
        query = query.filter(User.builder_id == current_user.builder_id)

        # For non-admins, check if they're trying to access themselves
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            if user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this user"
                )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        success=True,
        message="User retrieved successfully",
        data=user.to_dict()
    )

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Create a new user
    """
    # Check if username or email already exists
    result = await db.execute(
        select(User).filter(
            or_(User.username == user_data.username, User.email == user_data.email)
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Validate role assignment permissions
    if user_data.role not in [UserRole.SALES_AGENT, UserRole.INVESTOR]:
        # Only master admin can create admin roles
        if current_user.role != UserRole.MASTER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only master admin can create admin roles"
            )

    # Set builder ID based on current user or provided data
    builder_id = user_data.builder_id or current_user.builder_id

    # For non-master admins, ensure they're creating users for their own builder
    if current_user.role != UserRole.MASTER_ADMIN and builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create user for different builder organization"
        )

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        role=user_data.role,
        builder_id=builder_id,
        investor_id=user_data.investor_id,
        created_by_id=current_user.id
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        success=True,
        message="User created successfully",
        data=user.to_dict()
    )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing user
    """
    # Get the user to update
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions
    if current_user.role != UserRole.MASTER_ADMIN:
        if user.builder_id != current_user.builder_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this user"
            )

        # Prevent demotion of users with higher roles
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update this user"
            )

    # Update fields if provided
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        success=True,
        message="User updated successfully",
        data=user.to_dict()
    )

@router.delete("/{user_id}", response_model=APIResponse)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete a user (soft delete by changing status)
    """
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions
    if current_user.role != UserRole.MASTER_ADMIN:
        if user.builder_id != current_user.builder_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this user"
            )

    # Soft delete by setting status to inactive
    user.status = "inactive"
    user.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="User deactivated successfully"
    )