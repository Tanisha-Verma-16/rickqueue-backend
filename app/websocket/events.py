"""
WebSocket Event Handlers
Additional events and utilities
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


class WebSocketEvents:
    """
    WebSocket event definitions and handlers
    """
    
    # Event types
    GROUP_UPDATE = 'group_update'
    GROUP_READY = 'group_ready'
    AI_DECISION = 'ai_decision'
    DRIVER_ASSIGNED = 'driver_assigned'
    USER_LEFT = 'user_left'
    DRIVER_LOCATION = 'driver_location'
    
    @staticmethod
    def format_group_update(group_id: int, current_size: int, 
                           max_size: int, message: str) -> Dict:
        """Format group update event"""
        return {
            'type': WebSocketEvents.GROUP_UPDATE,
            'group_id': group_id,
            'current_size': current_size,
            'max_size': max_size,
            'message': message
        }
    
    @staticmethod
    def format_group_ready(group_id: int, qr_code: str, 
                          passenger_count: int) -> Dict:
        """Format group ready event"""
        return {
            'type': WebSocketEvents.GROUP_READY,
            'group_id': group_id,
            'qr_code': qr_code,
            'passenger_count': passenger_count,
            'message': f'🎉 Your group is ready! ({passenger_count} passengers)'
        }
    
    @staticmethod
    def format_ai_decision(group_id: int, decision: str, 
                          message: str) -> Dict:
        """Format AI decision event"""
        return {
            'type': WebSocketEvents.AI_DECISION,
            'group_id': group_id,
            'decision': decision,
            'message': message
        }