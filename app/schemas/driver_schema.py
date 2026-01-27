"""
Driver Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class DriverBase(BaseModel):
    phone_number: str
    full_name: str
    vehicle_number: str
    license_number: str


class DriverCreate(DriverBase):
    firebase_uid: str


class DriverUpdate(BaseModel):
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    is_online: Optional[bool] = None
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None


class DriverResponse(DriverBase):
    id: int
    firebase_uid: str
    verification_status: str
    is_online: bool
    is_available: bool
    total_trips_completed: int
    avg_rating: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class DriverDashboardResponse(BaseModel):
    driver_status: Dict
    nearby_opportunities: List[Dict]
    route_optimization: Dict
    pending_bookings_heatmap: List[Dict]
    ai_suggestion: "OptimizationSuggestion"


class RouteOpportunity(BaseModel):
    route_id: int
    route_name: str
    pending_bookings_total: int
    short_route_passengers: int
    full_route_passengers: int
    forming_groups_count: int
    profit_analysis: Dict
    recommendation: str


class OptimizationSuggestion(BaseModel):
    action: str
    priority: str
    message: str
    estimated_earning_potential: float
    reasoning: str