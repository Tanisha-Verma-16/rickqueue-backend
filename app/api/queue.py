"""
Queue API Endpoints
User-facing APIs for queue management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.services.auth_service import get_current_user
from app.services.queue_service import QueueService
from app.models.user import User
from app.schemas.queue_schema import (
    JoinQueueRequest,
    JoinQueueResponse,
    QueueStatusResponse,
    LeaveQueueResponse
)

router = APIRouter(prefix="/queue", tags=["Queue"])


@router.post("/join", response_model=JoinQueueResponse)
async def join_queue(
    request: JoinQueueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎯 JOIN QUEUE
    
    User joins the queue for a specific route
    System automatically finds or creates a matching group
    
    Flow:
    1. Validate user and route
    2. Check for existing bookings
    3. Find matching group (or create new)
    4. Add user to group
    5. Notify other members
    6. Return group details + estimated wait time
    """
    
    try:
        queue_service = QueueService(db)
        
        result = queue_service.join_queue(
            user_id=current_user.id,
            route_id=request.route_id,
            user_lat=request.current_lat,
            user_lng=request.current_lng,
            women_only=request.women_only_preference
        )
        
        return JoinQueueResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to join queue: {str(e)}"
        )


@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 GET QUEUE STATUS
    
    Get user's current position in queue/group
    Includes:
    - Group details
    - Other passengers
    - Estimated wait time
    - Real-time updates
    """
    
    try:
        queue_service = QueueService(db)
        
        status = queue_service.get_queue_status(current_user.id)
        
        return QueueStatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.post("/leave", response_model=LeaveQueueResponse)
async def leave_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚪 LEAVE QUEUE
    
    User cancels their booking and leaves the group
    - Updates group size
    - Notifies other members
    - Reassigns seat numbers if needed
    """
    
    try:
        queue_service = QueueService(db)
        
        result = queue_service.leave_queue(current_user.id)
        
        return LeaveQueueResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to leave queue: {str(e)}"
        )


@router.get("/nearby-groups")
async def get_nearby_groups(
    route_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🗺️ GET NEARBY GROUPS
    
    Show user how many groups are forming on this route
    Helps with decision-making
    """
    
    try:
        queue_service = QueueService(db)
        
        groups = queue_service.get_all_forming_groups(route_id=route_id)
        
        return {
            'route_id': route_id,
            'forming_groups_count': len(groups),
            'groups': groups,
            'recommendation': _generate_recommendation(groups)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch groups: {str(e)}"
        )


@router.get("/analytics/summary")
async def get_queue_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📈 QUEUE ANALYTICS
    
    Real-time queue metrics (for admin/monitoring)
    """
    
    from app.models.ride_group import RideGroup, GroupStatus
    from sqlalchemy import func
    
    # Count groups by status
    status_counts = db.query(
        RideGroup.group_status,
        func.count(RideGroup.id)
    ).group_by(RideGroup.group_status).all()
    
    # Get forming groups details
    forming_groups = db.query(RideGroup).filter(
        RideGroup.group_status == GroupStatus.FORMING
    ).all()
    
    avg_wait_time = sum(g.get_wait_time_seconds() for g in forming_groups) / len(forming_groups) if forming_groups else 0
    avg_size = sum(g.current_size for g in forming_groups) / len(forming_groups) if forming_groups else 0
    
    return {
        'total_forming_groups': len(forming_groups),
        'average_wait_time_seconds': int(avg_wait_time),
        'average_group_size': round(avg_size, 1),
        'groups_by_status': dict(status_counts),
        'system_health': 'HEALTHY' if len(forming_groups) < 20 else 'BUSY'
    }


# ===== HELPER FUNCTIONS =====

def _generate_recommendation(groups: list) -> str:
    """
    Generate recommendation message for user
    """
    
    if not groups:
        return "No groups forming yet. You'll start a new group!"
    
    # Check for nearly full groups
    nearly_full = [g for g in groups if g['current_size'] >= 3]
    
    if nearly_full:
        return f"Great timing! {len(nearly_full)} group(s) almost full - you might be the last person!"
    
    half_full = [g for g in groups if g['current_size'] >= 2]
    
    if half_full:
        return f"{len(half_full)} group(s) forming now. Expected wait: 2-4 minutes"
    
    return f"{len(groups)} group(s) just started. You'll help fill them up faster!"


# ===== WEBSOCKET EVENTS (Called by notification service) =====

async def broadcast_group_update(group_id: int, message: dict):
    """
    WebSocket broadcast to all members of a group
    Called by NotificationService
    """
    from app.main import sio
    
    await sio.emit(
        'group_update',
        message,
        room=f"group_{group_id}"
    )