"""
User Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    phone_number: str
    full_name: str
    gender: str


class UserCreate(UserBase):
    firebase_uid: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserResponse(UserBase):
    id: int
    firebase_uid: str
    profile_image_url: Optional[str] = None
    is_active: bool
    total_rides: int
    created_at: datetime
    
    class Config:
        from_attributes = True