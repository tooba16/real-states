from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import BaseModel
from core.database import Base

class Builder(Base, BaseModel):
    __tablename__ = "builders"

    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True)
    contact_person = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    logo_url = Column(String(500))
    max_projects = Column(Integer, default=10)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'suspended', 'inactive'

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    # Back references
    users = relationship("User", back_populates="builder", foreign_keys="User.builder_id", lazy="dynamic")
    projects = relationship("Project", back_populates="builder", lazy="dynamic")
    investors = relationship("Investor", back_populates="builder", lazy="dynamic")