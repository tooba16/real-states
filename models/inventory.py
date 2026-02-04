from sqlalchemy import Column, String, Text, Integer, DateTime, Date, DECIMAL, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import BaseModel
from core.database import Base

from enum import Enum

class InventoryStatus(str, Enum):
    AVAILABLE = "available"
    ON_HOLD = "on_hold"
    BOOKED = "booked"
    SOLD = "sold"

class UnitType(str, Enum):
    PLOT = "plot"
    FILE = "file"
    FLAT = "flat"
    VILLA = "villa"
    COMMERCIAL = "commercial"

class CategoryType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    AGRICULTURAL = "agricultural"

class Inventory(Base, BaseModel):
    __tablename__ = "inventory"

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    phase_block_id = Column(PG_UUID(as_uuid=True), ForeignKey("phases_blocks.id"))
    unit_number = Column(String(50))
    unit_type = Column(String(50), nullable=False)  # 'plot', 'file', 'flat', 'villa', 'commercial'
    category = Column(String(50))  # 'residential', 'commercial', 'agricultural'
    size = Column(DECIMAL(10, 2))  # in square feet or marlas
    price = Column(DECIMAL(15, 2), nullable=False)
    status = Column(String(20), default="available", nullable=False)  # 'available', 'on_hold', 'booked', 'sold'
    hold_expiry_date = Column(DateTime(timezone=True))
    booked_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    investor_locked = Column(Boolean, default=False)
    investor_id = Column(PG_UUID(as_uuid=True), ForeignKey("investors.id"))
    remarks = Column(Text)

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    project = relationship("Project", back_populates="inventory_items")
    phase_block = relationship("PhaseBlock", back_populates="inventory_items")
    booked_by = relationship("User", foreign_keys=[booked_by_id])
    investor = relationship("Investor", back_populates="inventory_items")
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    # Back references
    bookings = relationship("Booking", back_populates="inventory", lazy="dynamic")
    investor_assignments = relationship("InvestorInventoryAssignment", back_populates="inventory", lazy="dynamic")
    transfers = relationship("Transfer", back_populates="inventory", lazy="dynamic")