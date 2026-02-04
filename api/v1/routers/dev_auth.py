from fastapi import APIRouter, HTTPException, status
from datetime import timedelta
from core.security import create_access_token, create_refresh_token
from schemas.responses import TokenResponse
import uuid
from typing import Dict, Any

router = APIRouter()

@router.post("/dev-login", response_model=TokenResponse)
async def dev_login():
    """
    Development login endpoint for testing purposes
    """
    # Create a development token with full admin access

    # Create access token
    access_token_expires = timedelta(minutes=60)  # 1 hour for development
    access_token = create_access_token(
        data={"sub": "dev_admin", "role": "MASTER_ADMIN"},
        expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token_expires = timedelta(days=7)  # 7 days for development
    refresh_token = create_refresh_token(
        data={"sub": "dev_admin", "role": "MASTER_ADMIN"},
        expires_delta=refresh_token_expires
    )

    return TokenResponse(
        success=True,
        message="Development login successful",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(uuid.uuid4()),
                "username": "dev_admin",
                "email": "dev@kingsbuilder.com",
                "first_name": "Developer",
                "last_name": "Admin",
                "role": "MASTER_ADMIN",
                "builder_id": None
            }
        }
    )