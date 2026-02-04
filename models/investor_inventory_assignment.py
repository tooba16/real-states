from sqlalchemy import Column, String, DECIMAL, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
from core.database import Base

class InvestorInventoryAssignment(Base, BaseModel):
    __tablename__ = "investor_inventory_assignments"

    investor_id = Column(PG_UUID(as_uuid=True), ForeignKey("investors.id"), nullable=False)
    inventory_id = Column(PG_UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False)
    percentage_share = Column(DECIMAL(5, 2), nullable=False)  # e.g., 50.00 for 50%
    consent_required = Column(Boolean, default=True)
    status = Column(String(20), default="active", nullable=False)  # 'active', 'inactive'

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    investor = relationship("Investor", back_populates="assignments")
    inventory = relationship("Inventory", back_populates="investor_assignments")
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    __table_args__ = (
        # Unique constraint to prevent duplicate assignments
    )