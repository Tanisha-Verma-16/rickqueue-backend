from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RouteStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_location = Column(String)
    end_location = Column(String)
    distance = Column(Float)  # in kilometers
    estimated_duration = Column(Integer)  # in minutes
    status = Column(SQLEnum(RouteStatus), default=RouteStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RouteBase(BaseModel):
    name: str
    start_location: str
    end_location: str
    distance: float
    estimated_duration: int
    status: RouteStatus = RouteStatus.ACTIVE


class RouteCreate(RouteBase):
    pass


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[RouteStatus] = None
    is_active: Optional[bool] = None


class RouteResponse(RouteBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True