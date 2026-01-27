from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RideGroup(Base):
    __tablename__ = "ride_groups"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(String, unique=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pickup_location = Column(String, nullable=False)
    dropoff_location = Column(String, nullable=False)
    pickup_latitude = Column(Float)
    pickup_longitude = Column(Float)
    dropoff_latitude = Column(Float)
    dropoff_longitude = Column(Float)
    estimated_fare = Column(Float)
    status = Column(String, default="active")  # active, completed, cancelled
    max_passengers = Column(Integer, default=4)
    current_passengers = Column(Integer, default=1)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_time = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<RideGroup(ride_id={self.ride_id}, status={self.status})>"