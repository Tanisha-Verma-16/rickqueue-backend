from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class DispatchStatus(enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DispatchLog(Base):
    __tablename__ = "dispatch_logs"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, index=True, nullable=False)
    driver_id = Column(Integer, index=True, nullable=False)
    status = Column(Enum(DispatchStatus), default=DispatchStatus.PENDING)
    dispatch_time = Column(DateTime, default=datetime.utcnow)
    completion_time = Column(DateTime, nullable=True)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    dropoff_latitude = Column(Float, nullable=True)
    dropoff_longitude = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DispatchLog(ride_id={self.ride_id}, driver_id={self.driver_id}, status={self.status})>"