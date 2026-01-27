from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRole(str, Enum):
    PASSENGER = "passenger"
    DRIVER = "driver"
    ADMIN = "admin"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    role: UserRole = UserRole.PASSENGER

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[UserStatus] = None

class User(UserBase):
    id: int
    status: UserStatus = UserStatus.ACTIVE
    rating: float = Field(default=5.0, ge=1.0, le=5.0)
    total_rides: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: str