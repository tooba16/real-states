from sqlalchemy import Column, DateTime, func, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from datetime import datetime, date
from core.database import Base

class BaseModel:
    """Base model that includes common fields for all models."""

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Internal UUID primary key
    external_id = Column(String(50), unique=True)  # Custom formatted ID for display
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, (datetime, date)):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result