from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
from core.database import Base

class PhaseBlock(Base, BaseModel):
    __tablename__ = "phases_blocks"

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., "Phase 1", "Block A"
    description = Column(Text)
    total_units = Column(Integer)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'completed', 'cancelled'

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    project = relationship("Project", back_populates="phases_blocks")
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    # Back references
    inventory_items = relationship("Inventory", back_populates="phase_block", lazy="dynamic")