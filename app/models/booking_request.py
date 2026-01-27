from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class BookingStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Location(BaseModel):
    latitude: float
    longitude: float
    address: str


class BookingRequest(BaseModel):
    id: Optional[str] = Field(None, description="Unique booking identifier")
    user_id: str = Field(..., description="ID of the user requesting the ride")
    pickup_location: Location = Field(..., description="Pickup location details")
    dropoff_location: Location = Field(..., description="Dropoff location details")
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    status: BookingStatus = Field(default=BookingStatus.PENDING)
    estimated_fare: Optional[float] = None
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    driver_id: Optional[str] = None
    passenger_count: int = Field(default=1, ge=1, le=6)
    special_requests: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BookingRequestCreate(BaseModel):
    user_id: str
    pickup_location: Location
    dropoff_location: Location
    passenger_count: int = 1
    scheduled_for: Optional[datetime] = None
    special_requests: Optional[str] = None


class BookingRequestUpdate(BaseModel):
    status: Optional[BookingStatus] = None
    driver_id: Optional[str] = None
    estimated_fare: Optional[float] = None
    special_requests: Optional[str] = None