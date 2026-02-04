from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import BaseModel
from core.database import Base

class AuditLog(Base, BaseModel):
    __tablename__ = "audit_logs"

    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    entity_type = Column(String(50), nullable=False)  # e.g., 'inventory', 'booking', 'payment'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False)
    action = Column(String(50), nullable=False)  # 'create', 'update', 'delete', 'view'
    old_values = Column(JSONB)  # Store old values as JSON
    new_values = Column(JSONB)  # Store new values as JSON
    ip_address = Column(String(45))  # Support IPv6 addresses
    user_agent = Column(Text)

    # Relationships
    user = relationship("User")

    # Indexes will be created separately for performance