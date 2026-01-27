"""
Authentication API Endpoints
Firebase-based authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.auth_service import get_current_user, get_current_driver
from app.models.user import User
from app.models.driver import Driver
from app.schemas.user_schema import UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user info
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile
    """
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    if user_update.gender is not None:
        current_user.gender = user_update.gender
    
    if user_update.profile_image_url is not None:
        current_user.profile_image_url = user_update.profile_image_url
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/test")
async def auth_test():
    """
    Test endpoint to verify auth API is working
    """
    return {
        "message": "Auth API is working",
        "status": "ok"
    }