from sqlalchemy import Column, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import date
from models.base import BaseModel
from core.database import Base

class Customer(Base, BaseModel):
    __tablename__ = "customers"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    father_name = Column(String(100))
    cnic = Column(String(15), unique=True)
    contact_number = Column(String(20), nullable=False)
    alternate_contact = Column(String(20))
    email = Column(String(255))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    occupation = Column(String(100))
    status = Column(String(20), default="active", nullable=False)  # 'active', 'inactive'

    # Creator/updater tracking
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    created_by = relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    updated_by = relationship("User", remote_side="User.id", foreign_keys=[updated_by_id])

    # Back references
    bookings = relationship("Booking", back_populates="customer", lazy="dynamic")
    payments_made = relationship("Payment", back_populates="customer", lazy="dynamic")
    transfers_from = relationship("Transfer", back_populates="from_customer", foreign_keys="Transfer.from_customer_id", lazy="dynamic")
    transfers_to = relationship("Transfer", back_populates="to_customer", foreign_keys="Transfer.to_customer_id", lazy="dynamic")