"""
SQLAlchemy Base Class
All models inherit from this
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here to ensure they're registered with Base
# This is important for Alembic migrations

from app.models.user import User
from app.models.driver import Driver, Route, Ride
from app.models.ride_group import RideGroup, GroupMember, BookingRequest, DispatchDecisionLog
from app.models.historical_data import HistoricalArrivalData

__all__ = [
    'Base',
    'User',
    'Driver',
    'Route',
    'Ride',
    'RideGroup',
    'GroupMember',
    'BookingRequest',
    'DispatchDecisionLog',
    'HistoricalArrivalData'
]