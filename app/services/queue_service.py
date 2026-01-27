"""
Queue Service - Core Business Logic
Handles group formation, matching, and queue management
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, Dict, List
from datetime import datetime
import logging

from app.models.ride_group import RideGroup, GroupStatus, GroupMember
from app.models.booking_request import BookingRequest
from app.models.user import User
from app.models.driver import Route
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class QueueService:
    """
    Manages the queue and group formation logic
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService()
    
    def join_queue(
        self,
        user_id: int,
        route_id: int,
        user_lat: float,
        user_lng: float,
        women_only: bool = False
    ) -> Dict:
        """
        Main entry point: User joins the queue
        
        Returns: {
            'success': bool,
            'booking_id': int,
            'group_id': int | None,
            'group_status': str,
            'position_in_queue': int,
            'estimated_wait_mins': int
        }
        """
        
        logger.info(f"User {user_id} joining queue for route {route_id}")
        
        # Validation
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        route = self.db.query(Route).filter(Route.id == route_id).first()
        if not route or not route.is_active:
            raise ValueError("Route not found or inactive")
        
        # Check if user already in queue
        existing_booking = self.db.query(BookingRequest).filter(
            and_(
                BookingRequest.user_id == user_id,
                BookingRequest.request_status == "SEARCHING"
            )
        ).first()
        
        if existing_booking:
            raise ValueError("You're already in a queue. Please cancel first.")
        
        # Create booking request
        booking = BookingRequest(
            user_id=user_id,
            route_id=route_id,
            request_lat=user_lat,
            request_lng=user_lng,
            women_only_preference=women_only,
            request_status="SEARCHING"
        )
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        
        logger.info(f"Booking {booking.id} created for user {user_id}")
        
        # Try to find or create a matching group
        group = self._find_or_create_group(
            user=user,
            route=route,
            booking=booking,
            women_only=women_only
        )
        
        # Add user to group
        result = self._add_user_to_group(
            user=user,
            group=group,
            booking=booking,
            user_lat=user_lat,
            user_lng=user_lng
        )
        
        # Notify other group members
        self._notify_group_update(group)
        
        return result
    
    def _find_or_create_group(
        self,
        user: User,
        route: Route,
        booking: BookingRequest,
        women_only: bool
    ) -> RideGroup:
        """
        Smart group matching algorithm
        Finds an existing group or creates a new one
        """
        
        # Find suitable existing groups
        query = self.db.query(RideGroup).filter(
            and_(
                RideGroup.route_id == route.id,
                RideGroup.group_status == GroupStatus.FORMING,
                RideGroup.current_size < RideGroup.max_size
            )
        )
        
        # Gender filter
        if women_only or user.gender == "FEMALE":
            # Women can only join women-only groups
            query = query.filter(RideGroup.women_only == True)
        else:
            # Men can only join mixed groups
            query = query.filter(RideGroup.women_only == False)
        
        existing_groups = query.all()
        
        # Find best match (prioritize groups closer to full)
        if existing_groups:
            # Sort by size (descending) - fill up existing groups first
            existing_groups.sort(key=lambda g: g.current_size, reverse=True)
            
            for group in existing_groups:
                if group.can_accept_user(user):
                    logger.info(f"Found existing group {group.id} for user {user.id}")
                    return group
        
        # No suitable group found, create new one
        new_group = RideGroup(
            route_id=route.id,
            women_only=women_only or user.gender == "FEMALE",
            group_status=GroupStatus.FORMING,
            current_size=0,
            max_size=4
        )
        
        self.db.add(new_group)
        self.db.commit()
        self.db.refresh(new_group)
        
        logger.info(f"Created new group {new_group.id} for route {route.id}")
        
        return new_group
    
    def _add_user_to_group(
        self,
        user: User,
        group: RideGroup,
        booking: BookingRequest,
        user_lat: float,
        user_lng: float
    ) -> Dict:
        """
        Add user to group and update all records
        """
        
        # Assign seat number
        seat_number = group.current_size + 1
        
        # Create group member record
        member = GroupMember(
            group_id=group.id,
            user_id=user.id,
            user_lat=user_lat,
            user_lng=user_lng,
            seat_number=seat_number
        )
        self.db.add(member)
        
        # Update group
        group.current_size += 1
        if group.first_user_joined_at is None:
            group.first_user_joined_at = datetime.utcnow()
        
        # Update booking request
        booking.group_id = group.id
        booking.request_status = "GROUPED"
        booking.grouped_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(
            f"User {user.id} added to group {group.id} "
            f"(seat {seat_number}, size now {group.current_size}/{group.max_size})"
        )
        
        # Calculate estimated wait time
        estimated_wait = self._estimate_wait_time(group)
        
        return {
            'success': True,
            'booking_id': booking.id,
            'group_id': group.id,
            'group_status': group.group_status.value,
            'current_size': group.current_size,
            'max_size': group.max_size,
            'seat_number': seat_number,
            'position_in_queue': seat_number,
            'estimated_wait_mins': estimated_wait,
            'women_only': group.women_only,
            'route': {
                'origin': group.route.origin_name,
                'destination': group.route.destination_name,
                'distance_km': group.route.distance_km
            }
        }
    
    def leave_queue(self, user_id: int) -> Dict:
        """
        User leaves the queue/group
        """
        
        logger.info(f"User {user_id} leaving queue")
        
        # Find active booking
        booking = self.db.query(BookingRequest).filter(
            and_(
                BookingRequest.user_id == user_id,
                or_(
                    BookingRequest.request_status == "SEARCHING",
                    BookingRequest.request_status == "GROUPED"
                )
            )
        ).first()
        
        if not booking:
            raise ValueError("No active booking found")
        
        # If user was in a group, remove them
        if booking.group_id:
            group = self.db.query(RideGroup).filter(
                RideGroup.id == booking.group_id
            ).first()
            
            if group and group.group_status == GroupStatus.FORMING:
                # Remove member
                member = self.db.query(GroupMember).filter(
                    and_(
                        GroupMember.group_id == group.id,
                        GroupMember.user_id == user_id
                    )
                ).first()
                
                if member:
                    self.db.delete(member)
                    group.current_size -= 1
                    
                    # If group is now empty, delete it
                    if group.current_size == 0:
                        logger.info(f"Group {group.id} is empty, deleting")
                        self.db.delete(group)
                    else:
                        # Reassign seat numbers
                        self._reassign_seat_numbers(group)
                        # Notify remaining members
                        self._notify_group_update(group)
        
        # Cancel booking
        booking.request_status = "CANCELLED"
        self.db.commit()
        
        return {
            'success': True,
            'message': 'You have left the queue'
        }
    
    def get_queue_status(self, user_id: int) -> Dict:
        """
        Get user's current queue/group status
        """
        
        # Find active booking
        booking = self.db.query(BookingRequest).filter(
            and_(
                BookingRequest.user_id == user_id,
                BookingRequest.request_status.in_(["SEARCHING", "GROUPED"])
            )
        ).first()
        
        if not booking:
            return {
                'in_queue': False,
                'message': 'You are not in any queue'
            }
        
        # Get group details
        if booking.group_id:
            group = self.db.query(RideGroup).filter(
                RideGroup.id == booking.group_id
            ).first()
            
            if group:
                # Get member info
                member = self.db.query(GroupMember).filter(
                    and_(
                        GroupMember.group_id == group.id,
                        GroupMember.user_id == user_id
                    )
                ).first()
                
                # Get other members
                other_members = self.db.query(GroupMember).filter(
                    and_(
                        GroupMember.group_id == group.id,
                        GroupMember.user_id != user_id
                    )
                ).all()
                
                return {
                    'in_queue': True,
                    'booking_id': booking.id,
                    'group_id': group.id,
                    'group_status': group.group_status.value,
                    'current_size': group.current_size,
                    'max_size': group.max_size,
                    'your_seat': member.seat_number if member else None,
                    'wait_time_seconds': group.get_wait_time_seconds(),
                    'estimated_wait_mins': self._estimate_wait_time(group),
                    'women_only': group.women_only,
                    'is_ready': group.group_status == GroupStatus.READY,
                    'qr_code': group.qr_code if group.group_status == GroupStatus.READY else None,
                    'route': {
                        'origin': group.route.origin_name,
                        'destination': group.route.destination_name
                    },
                    'other_passengers': [
                        {
                            'name': m.user.full_name,
                            'gender': m.user.gender,
                            'seat': m.seat_number
                        }
                        for m in other_members
                    ]
                }
        
        return {
            'in_queue': True,
            'booking_id': booking.id,
            'status': 'SEARCHING',
            'message': 'Finding a group for you...'
        }
    
    def get_all_forming_groups(self, route_id: Optional[int] = None) -> List[Dict]:
        """
        Get all forming groups (admin/analytics endpoint)
        """
        
        query = self.db.query(RideGroup).filter(
            RideGroup.group_status == GroupStatus.FORMING
        )
        
        if route_id:
            query = query.filter(RideGroup.route_id == route_id)
        
        groups = query.all()
        
        return [
            {
                'group_id': g.id,
                'route': f"{g.route.origin_name} → {g.route.destination_name}",
                'current_size': g.current_size,
                'max_size': g.max_size,
                'wait_time_seconds': g.get_wait_time_seconds(),
                'women_only': g.women_only,
                'created_at': g.created_at.isoformat()
            }
            for g in groups
        ]
    
    def _reassign_seat_numbers(self, group: RideGroup):
        """
        Reassign seat numbers after a user leaves
        """
        members = self.db.query(GroupMember).filter(
            GroupMember.group_id == group.id
        ).order_by(GroupMember.joined_at).all()
        
        for idx, member in enumerate(members, start=1):
            member.seat_number = idx
        
        self.db.commit()
    
    def _estimate_wait_time(self, group: RideGroup) -> int:
        """
        Estimate wait time in minutes based on AI predictions
        """
        from app.ai.historical_learner import HistoricalLearner
        from app.ai.proximity_analyzer import ProximityAnalyzer
        
        # If group is full, minimal wait
        if group.is_full():
            return 1
        
        # Get AI prediction
        learner = HistoricalLearner(self.db)
        prediction = learner.predict_next_arrival_time(
            route_id=group.route_id,
            current_time=datetime.utcnow()
        )
        
        if prediction:
            # Convert to minutes
            return max(1, prediction['estimated_arrival_seconds'] // 60)
        
        # Fallback: base on current size
        if group.current_size == 3:
            return 2  # Likely to fill soon
        elif group.current_size == 2:
            return 3
        else:
            return 5
    
    def _notify_group_update(self, group: RideGroup):
        """
        Send WebSocket notification to all group members
        """
        self.notification_service.notify_group_update(
            group_id=group.id,
            current_size=group.current_size,
            max_size=group.max_size
        )