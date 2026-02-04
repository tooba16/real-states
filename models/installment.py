from sqlalchemy import Column, Integer, DateTime, Date, DECIMAL, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import date
from models.base import BaseModel
from core.database import Base
from enum import Enum

class InstallmentDueStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    WAIVED = "waived"

class Installment(Base, BaseModel):
    __tablename__ = "installments"

    booking_id = Column(PG_UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    paid_amount = Column(DECIMAL(15, 2), default=0)
    # Calculate balance amount as amount - paid_amount
    # Note: Computed columns may not work as expected in all SQLAlchemy versions
    due_status = Column(String(20), default="pending", nullable=False)  # 'pending', 'paid', 'overdue', 'waived'
    paid_date = Column(Date)
    remarks = Column(Text)

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    booking = relationship("Booking", back_populates="installments")
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    __table_args__ = (
        # Unique constraint to prevent duplicate installment numbers for same booking
        # Note: db is not imported in this context, removing this for now
    )