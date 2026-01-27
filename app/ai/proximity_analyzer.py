"""
Proximity Analyzer - Your Enhancement
Analyzes pending bookings for strategic dispatch
"""

from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.ride_group import BookingRequest, RideGroup
from app.utils.geo import calculate_distance

import logging

logger = logging.getLogger(__name__)


class ProximityAnalyzer:
    """
    Analyzes nearby pending bookings for strategic positioning
    """
    
    RECENT_BOOKING_WINDOW_SECONDS = 120  # 2 minutes
    MAX_PROXIMITY_METERS = 1000  # 1 km
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_pending_bookings(
        self,
        route_id: int,
        group: RideGroup
    ) -> Dict:
        """
        Analyze pending bookings for strategic dispatch
        
        Returns: {
            'pending_count': int,
            'nearest_distance_meters': int,
            'strategic_advantage': bool,
            'reasoning': str
        }
        """
        
        # Find recent SEARCHING bookings
        recent_threshold = datetime.utcnow() - timedelta(
            seconds=self.RECENT_BOOKING_WINDOW_SECONDS
        )
        
        try:
            pending_bookings = self.db.query(BookingRequest).filter(
                and_(
                    BookingRequest.route_id == route_id,
                    BookingRequest.request_status == "SEARCHING",
                    BookingRequest.requested_at >= recent_threshold
                )
            ).all()
        except Exception as e:
            logger.error(f"Error querying pending bookings: {e}")
            return {
                'pending_count': 0,
                'nearest_distance_meters': 9999,
                'strategic_advantage': False,
                'reasoning': 'Error checking bookings'
            }
        
        if not pending_bookings:
            return {
                'pending_count': 0,
                'nearest_distance_meters': 9999,
                'strategic_advantage': False,
                'reasoning': 'No pending bookings detected'
            }
        
        # Calculate nearest distance
        nearest_distance = self._calculate_nearest_distance(group, pending_bookings)
        
        # Determine strategic advantage
        strategic_advantage = (
            len(pending_bookings) >= 2 and
            nearest_distance < self.MAX_PROXIMITY_METERS
        )
        
        reasoning = self._build_reasoning(
            len(pending_bookings),
            nearest_distance,
            strategic_advantage
        )
        
        return {
            'pending_count': len(pending_bookings),
            'nearest_distance_meters': nearest_distance,
            'strategic_advantage': strategic_advantage,
            'reasoning': reasoning
        }
    
    def _calculate_nearest_distance(
        self,
        group: RideGroup,
        bookings: List[BookingRequest]
    ) -> int:
        """Calculate distance to nearest pending booking"""
        
        group_lat = float(group.route.origin_lat)
        group_lng = float(group.route.origin_lng)
        
        distances = []
        for booking in bookings:
            try:
                distance = calculate_distance(
                    group_lat, group_lng,
                    float(booking.request_lat), float(booking.request_lng)
                )
                distances.append(distance)
            except Exception as e:
                logger.error(f"Error calculating distance: {e}")
                continue
        
        return min(distances) if distances else 9999
    
    def _build_reasoning(
        self,
        count: int,
        distance: int,
        advantage: bool
    ) -> str:
        """Generate reasoning message"""
        
        if advantage:
            return (
                f"STRATEGIC: {count} users waiting within {distance}m - "
                f"dispatch NOW to secure them!"
            )
        elif count > 0:
            return (
                f"{count} pending booking(s) but {distance}m away - "
                f"not close enough"
            )
        else:
            return "No pending bookings detected"