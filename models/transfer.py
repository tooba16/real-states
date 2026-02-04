from sqlalchemy import Column, String, Text, DateTime, Date, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import date
from models.base import BaseModel
from core.database import Base
from enum import Enum

class TransferStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class Transfer(Base, BaseModel):
    __tablename__ = "transfers"

    inventory_id = Column(PG_UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False)
    booking_id = Column(PG_UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    from_customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    to_customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    transfer_date = Column(Date, nullable=False)
    transfer_fee = Column(DECIMAL(10, 2))
    status = Column(String(20), default=TransferStatus.PENDING, nullable=False)  # 'pending', 'approved', 'rejected', 'completed'
    approved_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    remarks = Column(Text)

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    inventory = relationship("Inventory", back_populates="transfers")
    booking = relationship("Booking", back_populates="transfers")
    from_customer = relationship("Customer", back_populates="transfers_from", foreign_keys=[from_customer_id])
    to_customer = relationship("Customer", back_populates="transfers_to", foreign_keys=[to_customer_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])