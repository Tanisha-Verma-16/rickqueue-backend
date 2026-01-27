"""
Schemas package
"""

from app.schemas.user_schema import UserBase, UserCreate, UserUpdate, UserResponse
from app.schemas.driver_schema import (
    DriverBase, DriverCreate, DriverUpdate, DriverResponse,
    DriverDashboardResponse, RouteOpportunity, OptimizationSuggestion
)
from app.schemas.queue_schema import (
    JoinQueueRequest, JoinQueueResponse, QueueStatusResponse, LeaveQueueResponse
)

__all__ = [
    'UserBase', 'UserCreate', 'UserUpdate', 'UserResponse',
    'DriverBase', 'DriverCreate', 'DriverUpdate', 'DriverResponse',
    'DriverDashboardResponse', 'RouteOpportunity', 'OptimizationSuggestion',
    'JoinQueueRequest', 'JoinQueueResponse', 'QueueStatusResponse', 'LeaveQueueResponse'
]
