from pydantic_settings import BaseSettings
from typing import List
import os
from datetime import timedelta

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Kings Builder Real Estate Management System"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_CGYk4fs2Xmel@ep-hidden-rice-ah2vyh8x-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require")
    DB_ECHO: bool = False

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Password hashing
    HASH_ROUNDS: int = 12

    # CORS settings - Allow specific origins for development
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # Standard Next.js dev server
        "http://localhost:3005",  # Alternative Next.js dev server
        "http://127.0.0.1:3000",  # Alternative localhost format
        "http://127.0.0.1:3005",  # Alternative localhost format
        "*"  # Fallback for development
    ]

    # Email settings (optional)
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # Master Admin credentials
    MASTER_ADMIN_USERNAME: str = os.getenv("MASTER_ADMIN_USERNAME", "scitforte")
    MASTER_ADMIN_EMAIL: str = os.getenv("MASTER_ADMIN_EMAIL", "admin@scitforte.com")
    MASTER_ADMIN_PASSWORD: str = os.getenv("MASTER_ADMIN_PASSWORD", "Pass2026")

    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]

    # Business rules
    DEFAULT_HOLD_EXPIRY_HOURS: int = 168  # 7 days in hours
    MAX_HOLD_EXTENSION_HOURS: int = 336   # 14 additional days in hours
    TRANSFER_FEE_PERCENTAGE: float = 2.0  # 2% transfer fee

settings = Settings()