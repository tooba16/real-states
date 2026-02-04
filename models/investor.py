from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
from core.database import Base

class Investor(Base, BaseModel):
    __tablename__ = "investors"

    name = Column(String(255), nullable=False)
    company_name = Column(String(255))
    cnic = Column(String(15), unique=True)
    contact_person = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    status = Column(String(20), default="active", nullable=False)  # 'active', 'inactive'

    # Relationships
    builder_id = Column(PG_UUID(as_uuid=True), ForeignKey("builders.id"))

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    builder = relationship("Builder", back_populates="investors")
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    # Back references
    users = relationship("User", back_populates="investor", foreign_keys="User.investor_id", lazy="dynamic")
    inventory_items = relationship("Inventory", back_populates="investor", lazy="dynamic")
    assignments = relationship("InvestorInventoryAssignment", back_populates="investor", lazy="dynamic")