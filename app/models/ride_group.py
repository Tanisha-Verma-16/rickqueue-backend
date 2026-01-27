"""
Ride Group Models
Contains: RideGroup, GroupMember, BookingRequest, DispatchDecisionLog
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.database.base import Base


class GroupStatus(str, enum.Enum):
    FORMING = "FORMING"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DispatchDecisionType(str, enum.Enum):
    FULL_GROUP = "FULL_GROUP"
    EARLY_DISPATCH = "EARLY_DISPATCH"
    FORCED = "FORCED"


class RideGroup(Base):
    __tablename__ = "ride_groups"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    
    group_status = Column(Enum(GroupStatus), default=GroupStatus.FORMING, nullable=False, index=True)
    current_size = Column(Integer, default=0, nullable=False)
    max_size = Column(Integer, default=4, nullable=False)
    women_only = Column(Boolean, default=False)
    
    # AI Decision Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    first_user_joined_at = Column(DateTime(timezone=True), nullable=True)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    dispatch_decision_type = Column(Enum(DispatchDecisionType), nullable=True)
    dispatch_probability_score = Column(Float, nullable=True)
    
    # Assignment
    assigned_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    qr_code = Column(String(100), unique=True, nullable=True)
    
    # Relationships
    route = relationship("Route", back_populates="ride_groups")
    members = relationship("GroupMember", back_populates="ride_group", cascade="all, delete-orphan")
    assigned_driver = relationship("Driver", back_populates="assigned_groups")
    booking_requests = relationship("BookingRequest", back_populates="ride_group")
    
    def is_full(self) -> bool:
        """Check if group has reached max capacity"""
        return self.current_size >= self.max_size
    
    def can_accept_user(self, user) -> bool:
        """Check if user can join this group"""
        if self.is_full():
            return False
        if self.women_only and user.gender != "FEMALE":
            return False
        return True
    
    def get_wait_time_seconds(self) -> int:
        """Calculate how long the first user has been waiting"""
        if not self.first_user_joined_at:
            return 0
        delta = datetime.utcnow() - self.first_user_joined_at
        return int(delta.total_seconds())
    
    def __repr__(self):
        return f"<RideGroup(id={self.id}, status={self.group_status}, size={self.current_size}/{self.max_size})>"


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("ride_groups.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    user_lat = Column(Float, nullable=True)
    user_lng = Column(Float, nullable=True)
    seat_number = Column(Integer, nullable=True)
    
    # Relationships
    ride_group = relationship("RideGroup", back_populates="members")
    user = relationship("User", back_populates="group_memberships")
    
    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id}, seat={self.seat_number})>"


class BookingRequest(Base):
    __tablename__ = "booking_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    
    request_status = Column(
        Enum("SEARCHING", "GROUPED", "CANCELLED", name="request_status_enum"),
        default="SEARCHING",
        nullable=False,
        index=True
    )
    
    # Location when booking (CRITICAL for proximity analysis)
    request_lat = Column(Float, nullable=False)
    request_lng = Column(Float, nullable=False)
    
    # Timestamps (AI uses this for pattern detection)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    grouped_at = Column(DateTime(timezone=True), nullable=True)
    
    group_id = Column(Integer, ForeignKey("ride_groups.id"), nullable=True)
    women_only_preference = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="booking_requests")
    route = relationship("Route", back_populates="booking_requests")
    ride_group = relationship("RideGroup", back_populates="booking_requests")
    
    def __repr__(self):
        return f"<BookingRequest(id={self.id}, user_id={self.user_id}, status={self.request_status})>"


class DispatchDecisionLog(Base):
    """Audit trail for AI decisions"""
    __tablename__ = "dispatch_decisions_log"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("ride_groups.id"), nullable=False, index=True)
    decision_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # State at decision time
    group_size_at_decision = Column(Integer, nullable=False)
    wait_time_seconds = Column(Integer, nullable=False)
    
    # AI Inputs
    pending_bookings_count = Column(Integer, default=0)
    nearest_pending_distance_meters = Column(Integer, nullable=True)
    historical_probability = Column(Float, nullable=True)
    
    # AI Output
    final_probability_score = Column(Float, nullable=False)
    decision_made = Column(
        Enum("DISPATCH_NOW", "WAIT", "NO_ACTION", name="dispatch_action_enum"),
        nullable=False
    )
    reasoning = Column(Text, nullable=True)
    
    # Relationship
    ride_group = relationship("RideGroup")
    
    def __repr__(self):
        return f"<DispatchDecisionLog(group_id={self.group_id}, decision={self.decision_made})>"