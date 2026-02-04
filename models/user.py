from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from models.base import BaseModel
from core.database import Base

class UserRole(str, Enum):
    MASTER_ADMIN = "master_admin"
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SALES_AGENT = "sales_agent"
    INVESTOR = "investor"

class User(Base, BaseModel):
    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    role = Column(SQLEnum(UserRole), nullable=False)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'inactive', 'suspended'

    # Relationships
    builder_id = Column(PG_UUID(as_uuid=True), ForeignKey("builders.id"))
    investor_id = Column(PG_UUID(as_uuid=True), ForeignKey("investors.id"))

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships - using string references to avoid circular import issues
    builder = relationship("Builder", back_populates="users", foreign_keys=[builder_id])
    investor = relationship("Investor", back_populates="users", foreign_keys=[investor_id])
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id], lazy="select")
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id], lazy="select")

    # Back references
    projects_created = relationship("Project", back_populates="created_by_user", foreign_keys="Project.created_by_id", lazy="select")
    projects_updated = relationship("Project", back_populates="updated_by_user", foreign_keys="Project.updated_by_id", lazy="select")

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        """Convert user instance to dictionary excluding sensitive fields."""
        data = super().to_dict()
        # Remove sensitive fields
        if 'password_hash' in data:
            del data['password_hash']
        return data