"""
Notification Service
Handles real-time WebSocket notifications to users and drivers
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Manages real-time notifications via WebSocket
    """
    
    def __init__(self):
        # Will be set by main.py when Socket.IO initializes
        self.sio = None
    
    def set_socketio(self, sio):
        """Set Socket.IO instance"""
        self.sio = sio
    
    async def notify_group_update(
        self,
        group_id: int,
        current_size: int,
        max_size: int
    ):
        """
        Notify all members when group composition changes
        """
        
        if not self.sio:
            logger.warning("Socket.IO not initialized")
            return
        
        message = self._generate_group_message(current_size, max_size)
        
        notification = {
            'type': 'group_update',
            'group_id': group_id,
            'current_size': current_size,
            'max_size': max_size,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            await self.sio.emit(
                'group_update',
                notification,
                room=f"group_{group_id}"
            )
            
            logger.info(f"Sent group update to group {group_id}: {message}")
            
        except Exception as e:
            logger.error(f"Failed to send group update: {e}")
    
    async def notify_group_ready(
        self,
        group_id: int,
        qr_code: str,
        passenger_count: int
    ):
        """
        Notify when group is ready (dispatched by AI)
        """
        
        if not self.sio:
            logger.warning("Socket.IO not initialized")
            return
        
        notification = {
            'type': 'group_ready',
            'group_id': group_id,
            'qr_code': qr_code,
            'passenger_count': passenger_count,
            'message': f"🎉 Your group is ready! ({passenger_count} passengers)",
            'instruction': "A driver will be assigned soon. Have your QR code ready!",
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            await self.sio.emit(
                'group_ready',
                notification,
                room=f"group_{group_id}"
            )
            
            logger.info(f"Sent group ready notification to group {group_id}")
            
        except Exception as e:
            logger.error(f"Failed to send group ready notification: {e}")
    
    async def notify_group_waiting(
        self,
        group_id: int,
        message: str
    ):
        """
        AI decided to WAIT - notify users why
        """
        
        if not self.sio:
            logger.warning("Socket.IO not initialized")
            return
        
        notification = {
            'type': 'ai_decision',
            'group_id': group_id,
            'decision': 'WAIT',
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            await self.sio.emit(
                'ai_decision',
                notification,
                room=f"group_{group_id}"
            )
            
            logger.info(f"Sent AI wait decision to group {group_id}")
            
        except Exception as e:
            logger.error(f"Failed to send AI decision: {e}")
    
    async def notify_driver_assigned(
        self,
        group_id: int,
        driver_name: str,
        vehicle_number: str,
        estimated_arrival_mins: int
    ):
        """
        Notify passengers when driver is assigned
        """
        
        if not self.sio:
            logger.warning("Socket.IO not initialized")
            return
        
        notification = {
            'type': 'driver_assigned',
            'group_id': group_id,
            'driver_name': driver_name,
            'vehicle_number': vehicle_number,
            'estimated_arrival_mins': estimated_arrival_mins,
            'message': f"🚗 {driver_name} is on the way! (Vehicle: {vehicle_number})",
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            await self.sio.emit(
                'driver_assigned',
                notification,
                room=f"group_{group_id}"
            )
            
            logger.info(f"Sent driver assignment to group {group_id}")
            
        except Exception as e:
            logger.error(f"Failed to send driver assignment: {e}")
    
    async def notify_user_left(
        self,
        group_id: int,
        left_user_name: str,
        new_size: int,
        max_size: int
    ):
        """
        Notify when someone leaves the group
        """
        
        if not self.sio:
            logger.warning("Socket.IO not initialized")
            return
        
        notification = {
            'type': 'user_left',
            'group_id': group_id,
            'message': f"{left_user_name} left the group. Now {new_size}/{max_size}",
            'current_size': new_size,
            'max_size': max_size,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            await self.sio.emit(
                'user_left',
                notification,
                room=f"group_{group_id}"
            )
            
            logger.info(f"Sent user left notification to group {group_id}")
            
        except Exception as e:
            logger.error(f"Failed to send user left notification: {e}")
    
    def _generate_group_message(self, current_size: int, max_size: int) -> str:
        """
        Generate contextual message based on group size
        """
        
        if current_size == max_size:
            return f"🎉 Group full! ({current_size}/{max_size}) - Dispatching soon!"
        elif current_size == max_size - 1:
            return f"⏳ Almost there! ({current_size}/{max_size}) - Waiting for 1 more"
        elif current_size == 2:
            return f"👥 Group forming... ({current_size}/{max_size}) - 2 more needed"
        else:
            return f"✨ New passenger joined! ({current_size}/{max_size})"
    
    # Synchronous wrappers for use in non-async contexts
    
    def notify_group_update_sync(
        self,
        group_id: int,
        current_size: int,
        max_size: int
    ):
        """Sync wrapper for notify_group_update"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, schedule the task
                asyncio.create_task(
                    self.notify_group_update(group_id, current_size, max_size)
                )
            else:
                # Run in new loop
                asyncio.run(
                    self.notify_group_update(group_id, current_size, max_size)
                )
        except Exception as e:
            logger.error(f"Error in sync notification: {e}")
    
    def notify_group_ready_sync(
        self,
        group_id: int,
        qr_code: str,
        passenger_count: int
    ):
        """Sync wrapper for notify_group_ready"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.notify_group_ready(group_id, qr_code, passenger_count)
                )
            else:
                asyncio.run(
                    self.notify_group_ready(group_id, qr_code, passenger_count)
                )
        except Exception as e:
            logger.error(f"Error in sync notification: {e}")
    
    def notify_group_waiting_sync(self, group_id: int, message: str):
        """Sync wrapper for notify_group_waiting"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.notify_group_waiting(group_id, message)
                )
            else:
                asyncio.run(
                    self.notify_group_waiting(group_id, message)
                )
        except Exception as e:
            logger.error(f"Error in sync notification: {e}")


# Global instance
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get notification service instance"""
    return notification_service