"""
WebSocket Manager
Handles Socket.IO connections and rooms
"""

import socketio
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Socket.IO Server instance (will be initialized in main.py)
sio = None


def init_socketio(app):
    """
    Initialize Socket.IO server
    Called from main.py
    """
    global sio
    
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins='*',
        logger=True,
        engineio_logger=True
    )
    
    # Attach event handlers
    register_events()
    
    return sio


def register_events():
    """
    Register Socket.IO event handlers
    """
    
    @sio.event
    async def connect(sid, environ):
        """Client connected"""
        logger.info(f"Client connected: {sid}")
        await sio.emit('connection_success', {'sid': sid}, to=sid)
    
    @sio.event
    async def disconnect(sid):
        """Client disconnected"""
        logger.info(f"Client disconnected: {sid}")
    
    @sio.event
    async def join_group_room(sid, data):
        """
        User/Driver joins a group room for updates
        """
        group_id = data.get('group_id')
        if group_id:
            room_name = f"group_{group_id}"
            await sio.enter_room(sid, room_name)
            logger.info(f"Client {sid} joined room: {room_name}")
            await sio.emit('room_joined', {'group_id': group_id}, to=sid)
    
    @sio.event
    async def leave_group_room(sid, data):
        """
        User leaves a group room
        """
        group_id = data.get('group_id')
        if group_id:
            room_name = f"group_{group_id}"
            await sio.leave_room(sid, room_name)
            logger.info(f"Client {sid} left room: {room_name}")
    
    @sio.event
    async def driver_location_update(sid, data):
        """
        Driver sends live location updates
        """
        driver_id = data.get('driver_id')
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not all([driver_id, lat, lng]):
            return
        
        # Broadcast to assigned group
        group_id = data.get('group_id')
        if group_id:
            await sio.emit(
                'driver_location',
                {'lat': lat, 'lng': lng, 'driver_id': driver_id},
                room=f"group_{group_id}"
            )


async def notify_group_driver_assigned(group_id: int, driver_name: str, 
                                       vehicle_number: str, driver_location: Dict):
    """
    Notify group members when driver is assigned
    """
    if sio:
        await sio.emit(
            'driver_assigned',
            {
                'type': 'driver_assigned',
                'group_id': group_id,
                'driver_name': driver_name,
                'vehicle_number': vehicle_number,
                'driver_location': driver_location
            },
            room=f"group_{group_id}"
        )


def get_sio():
    """Get Socket.IO instance"""
    return sio