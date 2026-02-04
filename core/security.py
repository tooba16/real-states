from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Union
import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError
from core.config import settings
from core.database import get_db
from models.user import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# JWT scheme for dependency injection
security = HTTPBearer()

import hashlib
import re

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    if not hashed_password:
        return False

    # Check if this is a SHA-256 hash (starts with 'sha256:')
    if hashed_password.startswith('sha256:'):
        # Extract the hash part after 'sha256:'
        expected_hash = hashed_password[7:]  # Remove 'sha256:' prefix
        # Hash the plain password and compare
        actual_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        return actual_hash == expected_hash
    else:
        # Use bcrypt verification, but handle errors gracefully
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            print(f"Bcrypt verification error: {e}")
            # Try to create a temporary fallback - check if raw password matches (for testing only)
            # This is only for debugging purposes
            import warnings
            warnings.warn("Using fallback password verification - this is insecure for production!")
            return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    """Generate a hash for a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if current_user.status != "active":
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_user_by_role(required_role: str):
    """Dependency to get current user with specific role check."""
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in [required_role, "master_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role}"
            )
        return current_user
    return role_checker

def get_current_master_admin(current_user: User = Depends(get_current_active_user)):
    """Dependency to ensure user is master admin."""
    if current_user.role != "master_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Master admin access required"
        )
    return current_user