from sqlalchemy import Column, String, Text, Integer, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import date
from models.base import BaseModel
from core.database import Base

class Project(Base, BaseModel):
    __tablename__ = "projects"

    builder_id = Column(PG_UUID(as_uuid=True), ForeignKey("builders.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(Text)
    city = Column(String(100))
    total_units = Column(Integer)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'completed', 'cancelled'
    start_date = Column(Date)
    expected_completion_date = Column(Date)

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    builder = relationship("Builder", back_populates="projects")
    created_by_user = relationship("User", remote_side="User.id", foreign_keys=[created_by_id], back_populates="projects_created")
    updated_by_user = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id], back_populates="projects_updated")

    # Back references
    phases_blocks = relationship("PhaseBlock", back_populates="project", lazy="dynamic")
    inventory_items = relationship("Inventory", back_populates="project", lazy="dynamic")
    bookings = relationship("Booking", back_populates="project", lazy="dynamic")