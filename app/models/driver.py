"""
Driver model with optimization tracking
Focus: Time & Profit optimization (NO payment processing)
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.database.base import Base


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String(128), unique=True, nullable=False, index=True)
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    
    # Vehicle Details
    vehicle_number = Column(String(20), unique=True, nullable=False)
    license_number = Column(String(30), unique=True, nullable=False)
    vehicle_capacity = Column(Integer, default=4)  # Can be 3 or 4
    
    verification_status = Column(
        Enum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False
    )
    
    # Real-time Status
    is_online = Column(Boolean, default=False, index=True)
    is_available = Column(Boolean, default=True)  # Not on active trip
    current_lat = Column(Float, nullable=True, index=True)
    current_lng = Column(Float, nullable=True, index=True)
    last_location_update = Column(DateTime(timezone=True), nullable=True)
    
    # Performance Metrics (for driver dashboard)
    total_trips_completed = Column(Integer, default=0)
    avg_rating = Column(Float, default=5.0)
    total_earnings_today = Column(Float, default=0.0)  # Just tracking, not payment
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    assigned_groups = relationship("RideGroup", back_populates="assigned_driver")
    completed_rides = relationship("Ride", back_populates="driver")
    
    def __repr__(self):
        return f"<Driver(id={self.id}, name={self.full_name}, online={self.is_online})>"


class Route(Base):
    """
    Predefined routes with pricing tiers
    Key insight: Drivers optimize between long-route vs multiple short-routes
    """
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(20), unique=True, nullable=False, index=True)
    
    # Route Details
    origin_name = Column(String(100), nullable=False)
    destination_name = Column(String(100), nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    dest_lat = Column(Float, nullable=False)
    dest_lng = Column(Float, nullable=False)
    
    # Route Characteristics
    distance_km = Column(Float, nullable=False)
    estimated_duration_mins = Column(Integer, nullable=False)
    
    # Pricing Tiers (for driver optimization calculation)
    # NO payment processing, just metrics for driver decision-making
    halfway_point_km = Column(Float, nullable=False)  # e.g., 2.5 km on a 5km route
    short_route_fare = Column(Float, nullable=False)  # Half price
    full_route_fare = Column(Float, nullable=False)   # Complete route
    
    # Optimization Metadata
    is_high_demand = Column(Boolean, default=False)  # Peak hours
    avg_wait_time_seconds = Column(Integer, default=0)  # Historical avg
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    ride_groups = relationship("RideGroup", back_populates="route")
    booking_requests = relationship("BookingRequest", back_populates="route")
    
    def calculate_profit_potential(self, short_passengers: int, full_passengers: int) -> dict:
        """
        Helper for driver dashboard to show optimization choices
        Example: "3 short-route (₹90) vs 2 full-route (₹120)"
        """
        short_revenue = short_passengers * self.short_route_fare
        full_revenue = full_passengers * self.full_route_fare
        
        # Time efficiency calculation
        short_route_time = self.estimated_duration_mins * 0.5  # Halfway
        full_route_time = self.estimated_duration_mins
        
        return {
            "short_route": {
                "passengers": short_passengers,
                "revenue": short_revenue,
                "time_mins": short_route_time,
                "trips_per_hour": 60 / short_route_time if short_route_time > 0 else 0
            },
            "full_route": {
                "passengers": full_passengers,
                "revenue": full_revenue,
                "time_mins": full_route_time,
                "trips_per_hour": 60 / full_route_time if full_route_time > 0 else 0
            }
        }


# User model is in app/models/user.py - don't duplicate here!


class Ride(Base):
    """
    Final trip record (NO payment tracking)
    Focus: Operational metrics and completion tracking
    """
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("ride_groups.id"), unique=True, nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    
    ride_status = Column(
        Enum("ASSIGNED", "DRIVER_ARRIVED", "IN_PROGRESS", "COMPLETED", "CANCELLED", 
             name="ride_status_enum"),
        default="ASSIGNED",
        nullable=False
    )
    
    # Timestamps
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    driver_arrived_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Trip Details (for passenger tracking)
    passenger_count = Column(Integer, nullable=False)
    short_route_passengers = Column(Integer, default=0)  # Getting off halfway
    full_route_passengers = Column(Integer, default=0)   # Going full distance
    
    # Performance Metrics
    actual_duration_mins = Column(Integer, nullable=True)
    driver_rating = Column(Float, nullable=True)  # 1-5 stars
    
    # Relationships
    ride_group = relationship("RideGroup")
    driver = relationship("Driver", back_populates="completed_rides")
    route = relationship("Route")
    
    def calculate_trip_metrics(self) -> dict:
        """Calculate efficiency metrics (NO payment calculation)"""
        if not self.completed_at or not self.started_at:
            return {}
        
        actual_time = (self.completed_at - self.started_at).total_seconds() / 60
        
        return {
            "actual_duration_mins": int(actual_time),
            "passenger_utilization": f"{self.passenger_count}/4",
            "on_time": actual_time <= self.route.estimated_duration_mins * 1.2  # 20% buffer
        }