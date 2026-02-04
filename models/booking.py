from sqlalchemy import Column, String, Text, DateTime, Date, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime, date
from models.base import BaseModel
from core.database import Base
from enum import Enum

class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class BookingType(str, Enum):
    HOLD = "hold"
    BOOKING = "booking"
    SALE = "sale"

class Booking(Base, BaseModel):
    __tablename__ = "bookings"

    inventory_id = Column(PG_UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    booking_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    booking_amount = Column(DECIMAL(15, 2), nullable=False)
    booking_status = Column(String(20), default=BookingStatus.CONFIRMED, nullable=False)  # 'confirmed', 'cancelled', 'completed'
    booking_type = Column(String(20), default=BookingType.SALE, nullable=False)  # 'hold', 'booking', 'sale'
    booking_reference = Column(String(100), unique=True)
    approved_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    cancelled_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    cancellation_reason = Column(Text)
    cancellation_date = Column(DateTime(timezone=True))
    remarks = Column(Text)

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    inventory = relationship("Inventory", back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")
    project = relationship("Project", back_populates="bookings")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    # Back references
    payments = relationship("Payment", back_populates="booking", lazy="dynamic")
    installments = relationship("Installment", back_populates="booking", lazy="dynamic")
    transfers = relationship("Transfer", back_populates="booking", lazy="dynamic")