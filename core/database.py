from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import logging

# Create async engine
def create_engine():
    # Import settings dynamically to ensure latest values
    from core.config import settings

    # For Neon database, we need to ensure SSL is properly configured
    connect_args = {}
    if "neon.tech" in settings.DATABASE_URL or "postgresql" in settings.DATABASE_URL:
        # Add SSL requirement for PostgreSQL/Neon
        connect_args["server_settings"] = {"sslmode": "require"}
    elif "sqlite" in settings.DATABASE_URL:
        # SQLite doesn't need special connection args
        # Also ensure we don't set server_settings which is PostgreSQL-specific
        connect_args["check_same_thread"] = False  # Allow multiple threads for SQLite
    else:
        # For other databases, check if it's PostgreSQL-related
        if "postgres" in settings.DATABASE_URL or "postgresql" in settings.DATABASE_URL:
            connect_args["server_settings"] = {"sslmode": "require"}

    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=NullPool if settings.DEBUG else None,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args
    )

# Create async session maker
def get_session_local():
    engine = create_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

# Base class for declarative models
class Base(DeclarativeBase):
    pass

# Global variables to hold engine and session maker
engine = None
AsyncSessionLocal = None

def init_database():
    global engine, AsyncSessionLocal
    # Import settings to ensure latest values are used
    from core.config import settings
    engine = create_engine()
    AsyncSessionLocal = get_session_local()

# Dependency to get DB session
async def get_db():
    if AsyncSessionLocal is None:
        init_database()
    async with AsyncSessionLocal() as session:
        yield session