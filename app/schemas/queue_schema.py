"""
Pydantic schemas for Queue API
Request/Response validation and documentation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class JoinQueueRequest(BaseModel):
    """
    Request to join queue
    """
    route_id: int = Field(..., description="Route ID to book")
    current_lat: float = Field(..., description="User's current latitude", ge=-90, le=90)
    current_lng: float = Field(..., description="User's current longitude", ge=-180, le=180)
    women_only_preference: bool = Field(default=False, description="Request women-only group")
    
    class Config:
        json_schema_extra = {
            "example": {
                "route_id": 1,
                "current_lat": 28.6139,
                "current_lng": 77.2090,
                "women_only_preference": False
            }
        }


class RouteInfo(BaseModel):
    """
    Route information in responses
    """
    origin: str
    destination: str
    distance_km: float


class JoinQueueResponse(BaseModel):
    """
    Response after joining queue
    """
    success: bool
    booking_id: int
    group_id: int
    group_status: str
    current_size: int
    max_size: int
    seat_number: int
    position_in_queue: int
    estimated_wait_mins: int
    women_only: bool
    route: RouteInfo
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "booking_id": 123,
                "group_id": 45,
                "group_status": "FORMING",
                "current_size": 2,
                "max_size": 4,
                "seat_number": 2,
                "position_in_queue": 2,
                "estimated_wait_mins": 3,
                "women_only": False,
                "route": {
                    "origin": "Metro Station Gate 1",
                    "destination": "City College",
                    "distance_km": 5.2
                }
            }
        }


class PassengerInfo(BaseModel):
    """
    Other passenger info
    """
    name: str
    gender: str
    seat: int


class QueueStatusResponse(BaseModel):
    """
    Current queue/group status
    """
    in_queue: bool
    booking_id: Optional[int] = None
    group_id: Optional[int] = None
    group_status: Optional[str] = None
    current_size: Optional[int] = None
    max_size: Optional[int] = None
    your_seat: Optional[int] = None
    wait_time_seconds: Optional[int] = None
    estimated_wait_mins: Optional[int] = None
    women_only: Optional[bool] = None
    is_ready: Optional[bool] = None
    qr_code: Optional[str] = None
    route: Optional[RouteInfo] = None
    other_passengers: Optional[List[PassengerInfo]] = None
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "in_queue": True,
                "booking_id": 123,
                "group_id": 45,
                "group_status": "FORMING",
                "current_size": 3,
                "max_size": 4,
                "your_seat": 2,
                "wait_time_seconds": 180,
                "estimated_wait_mins": 2,
                "women_only": False,
                "is_ready": False,
                "qr_code": None,
                "route": {
                    "origin": "Metro Station",
                    "destination": "College",
                    "distance_km": 5.2
                },
                "other_passengers": [
                    {"name": "John", "gender": "MALE", "seat": 1},
                    {"name": "Sarah", "gender": "FEMALE", "seat": 3}
                ]
            }
        }


class LeaveQueueResponse(BaseModel):
    """
    Response after leaving queue
    """
    success: bool
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "You have left the queue"
            }
        }


class GroupUpdateNotification(BaseModel):
    """
    WebSocket notification format
    """
    type: str = Field(..., description="Notification type")
    group_id: int
    current_size: int
    max_size: int
    message: str
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "group_update",
                "group_id": 45,
                "current_size": 3,
                "max_size": 4,
                "message": "One more passenger joined! 3/4",
                "timestamp": "2026-01-27T10:30:00Z"
            }
        }


class GroupReadyNotification(BaseModel):
    """
    WebSocket notification when group is ready
    """
    type: str = "group_ready"
    group_id: int
    qr_code: str
    passenger_count: int
    message: str
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "group_ready",
                "group_id": 45,
                "qr_code": "RQ-45-1738056000000",
                "passenger_count": 4,
                "message": "Your group is ready! Show QR code to driver",
                "timestamp": "2026-01-27T10:35:00Z"
            }
        }