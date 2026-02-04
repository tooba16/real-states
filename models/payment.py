from sqlalchemy import Column, String, Text, DateTime, Date, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import date
from models.base import BaseModel
from core.database import Base
from enum import Enum

class PaymentMethod(str, Enum):
    CASH = "cash"
    CHEQUE = "cheque"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"

class PaymentStatus(str, Enum):
    RECEIVED = "received"
    PENDING = "pending"
    REJECTED = "rejected"

class Payment(Base, BaseModel):
    __tablename__ = "payments"

    booking_id = Column(PG_UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)  # 'cash', 'cheque', 'bank_transfer', 'online'
    payment_date = Column(Date, nullable=False)
    reference_number = Column(String(100))
    cheque_number = Column(String(50))
    bank_name = Column(String(100))
    payment_status = Column(String(20), default="received", nullable=False)  # 'received', 'pending', 'rejected'
    remarks = Column(Text)

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    booking = relationship("Booking", back_populates="payments")
    customer = relationship("Customer", back_populates="payments_made")
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])