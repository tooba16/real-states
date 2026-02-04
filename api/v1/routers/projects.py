from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid

from core.database import get_db
from core.security import get_current_user, get_current_active_user, get_current_user_by_role
from models.project import Project
from models.user import User, UserRole
from models.builder import Builder
from schemas.project import ProjectCreate, ProjectUpdate, ProjectPublic
from schemas.responses import ProjectResponse, APIResponse
from utils.id_generator import generate_unique_project_id

router = APIRouter()

@router.get("/", response_model=ProjectResponse)
async def get_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    search: Optional[str] = Query(None),
    builder_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Get list of projects with optional filtering
    """
    query = select(Project)

    # Apply filters based on user role
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can see all projects, can filter by builder
        if builder_id:
            query = query.filter(Project.builder_id == builder_id)
    elif current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        # Super admin and admin can only see projects in their builder
        query = query.filter(Project.builder_id == current_user.builder_id)
    else:
        # Other roles can only see projects in their builder
        query = query.filter(Project.builder_id == current_user.builder_id)

    # Apply additional filters
    if search:
        query = query.filter(
            or_(
                Project.name.contains(search),
                Project.location.contains(search)
            )
        )

    if status:
        query = query.filter(Project.status == status)

    # Count total for pagination
    count_query = select(Project).filter(query.whereclause)
    total_result = await db.execute(count_query)
    total = total_result.rowcount

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectResponse(
        success=True,
        message="Projects retrieved successfully",
        data={
            "projects": [project.to_dict() for project in projects],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific project by ID
    """
    query = select(Project).filter(Project.id == project_id)

    if current_user.role != UserRole.MASTER_ADMIN:
        query = query.filter(Project.builder_id == current_user.builder_id)

    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return ProjectResponse(
        success=True,
        message="Project retrieved successfully",
        data=project.to_dict()
    )

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Create a new project
    """
    # Verify builder exists and belongs to current user's organization
    builder_result = await db.execute(
        select(Builder).filter(Builder.id == project_data.builder_id)
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
            detail="Cannot create project for different builder organization"
        )

    # Check if builder has reached project limit
    project_count_result = await db.execute(
        select(Project).filter(Project.builder_id == builder.id).filter(Project.status != "cancelled")
    )
    project_count = len(project_count_result.scalars().all())

    if project_count >= builder.max_projects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum project limit ({builder.max_projects}) reached for this builder"
        )

    # Generate unique external ID
    external_id = await generate_unique_project_id(db)

    # Create project
    project = Project(
        name=project_data.name,
        description=project_data.description,
        location=project_data.location,
        city=project_data.city,
        total_units=project_data.total_units,
        start_date=project_data.start_date,
        expected_completion_date=project_data.expected_completion_date,
        builder_id=project_data.builder_id,
        external_id=external_id,
        created_by_id=current_user.id
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        success=True,
        message="Project created successfully",
        data=project.to_dict()
    )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Update an existing project
    """
    result = await db.execute(
        select(Project).filter(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permissions
    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this project"
        )

    # Update fields if provided
    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    project.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        success=True,
        message="Project updated successfully",
        data=project.to_dict()
    )

@router.delete("/{project_id}", response_model=APIResponse)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_by_role("admin"))
):
    """
    Delete a project (soft delete by changing status)
    """
    result = await db.execute(
        select(Project).filter(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permissions
    if current_user.role != UserRole.MASTER_ADMIN and project.builder_id != current_user.builder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project"
        )

    # Soft delete by setting status to cancelled
    project.status = "cancelled"
    project.updated_by_id = current_user.id

    await db.commit()

    return APIResponse(
        success=True,
        message="Project cancelled successfully"
    )