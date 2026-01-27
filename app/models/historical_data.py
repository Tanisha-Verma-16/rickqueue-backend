"""
Historical Arrival Data Model
Stores learned patterns for AI predictions
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.base import Base


class HistoricalArrivalData(Base):
    """
    Aggregated historical data for arrival predictions
    Updated daily by the HistoricalDataBuilder
    """
    __tablename__ = "historical_arrival_data"
    
    __table_args__ = (
        UniqueConstraint('route_id', 'day_of_week', 'hour_of_day', 'time_slot', 
                        name='uq_route_time_slot'),
        Index('idx_route_time', 'route_id', 'day_of_week', 'hour_of_day'),
    )

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    
    # Time Bucketing
    day_of_week = Column(Integer, nullable=False)  # 1=Mon, 7=Sun
    hour_of_day = Column(Integer, nullable=False)  # 0-23
    time_slot = Column(String(20), nullable=False)  # "09:00-09:30"
    
    # Metrics (Calculated from historical bookings)
    total_bookings = Column(Integer, default=0)
    avg_bookings_per_30min = Column(Float, default=0.0)
    avg_wait_time_seconds = Column(Integer, default=0)
    total_early_dispatches = Column(Integer, default=0)
    
    # Calculated Probability (Pre-computed for fast lookup)
    arrival_probability_score = Column(Float, default=50.0)  # 0-100%
    
    # Metadata
    last_updated = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()))
    
    # Relationships
    route = relationship("Route")
    
    def __repr__(self):
        return (
            f"<HistoricalArrivalData(route={self.route_id}, "
            f"day={self.day_of_week}, hour={self.hour_of_day}, "
            f"probability={self.arrival_probability_score}%)>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'route_id': self.route_id,
            'day_of_week': self.day_of_week,
            'hour_of_day': self.hour_of_day,
            'time_slot': self.time_slot,
            'total_bookings': self.total_bookings,
            'avg_bookings_per_30min': round(self.avg_bookings_per_30min, 2),
            'avg_wait_time_seconds': self.avg_wait_time_seconds,
            'arrival_probability_score': round(self.arrival_probability_score, 2)
        }