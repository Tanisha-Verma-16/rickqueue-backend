"""
📊 HISTORICAL LEARNER
Learns from past booking patterns to predict future demand
"Mondays at 9 AM always have high traffic"
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

from app.models.booking_request import BookingRequest
from app.models.ride_group import RideGroup, GroupStatus
from app.models.historical_data import HistoricalArrivalData

logger = logging.getLogger(__name__)


class HistoricalLearner:
    """
    Analyzes historical booking data to predict arrival patterns
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_arrival_probability(
        self,
        route_id: int,
        current_time: datetime
    ) -> float:
        """
        Get probability of passenger arrival in next 60 seconds
        Based on historical data for this route/time
        
        Returns: Probability score (0-100)
        """
        
        day_of_week = current_time.weekday() + 1  # 1=Monday, 7=Sunday
        hour_of_day = current_time.hour
        
        # Find matching historical data
        historical_data = self.db.query(HistoricalArrivalData).filter(
            and_(
                HistoricalArrivalData.route_id == route_id,
                HistoricalArrivalData.day_of_week == day_of_week,
                HistoricalArrivalData.hour_of_day == hour_of_day
            )
        ).first()
        
        if historical_data:
            probability = historical_data.arrival_probability_score
            logger.debug(
                f"Historical probability for route {route_id} "
                f"on {self._day_name(day_of_week)} at {hour_of_day}:00 = {probability}%"
            )
            return float(probability)
        
        # No historical data - return neutral probability
        logger.warning(
            f"No historical data for route {route_id}, "
            f"day {day_of_week}, hour {hour_of_day}"
        )
        return 50.0  # Default neutral
    
    def build_historical_data(
        self,
        route_id: int,
        lookback_days: int = 30
    ) -> Dict[str, int]:
        """
        Build/update historical arrival data from past bookings
        This should run daily (scheduled job)
        
        Returns: Statistics about data processed
        """
        
        logger.info(f"Building historical data for route {route_id} (last {lookback_days} days)")
        
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get all bookings in the lookback period
        bookings = self.db.query(BookingRequest).filter(
            and_(
                BookingRequest.route_id == route_id,
                BookingRequest.requested_at >= cutoff_date
            )
        ).all()
        
        logger.info(f"Processing {len(bookings)} bookings")
        
        # Group bookings by day-of-week and hour
        time_buckets = {}
        
        for booking in bookings:
            day = booking.requested_at.weekday() + 1
            hour = booking.requested_at.hour
            time_slot = f"{hour:02d}:00-{hour:02d}:30"
            
            key = (day, hour, time_slot)
            
            if key not in time_buckets:
                time_buckets[key] = []
            
            time_buckets[key].append(booking)
        
        # Calculate statistics for each time bucket
        records_created = 0
        records_updated = 0
        
        for (day, hour, time_slot), bucket_bookings in time_buckets.items():
            # Calculate metrics
            total_bookings = len(bucket_bookings)
            
            # Average bookings per 30-min window
            days_in_period = lookback_days / 7  # Approximate weeks
            avg_bookings_per_30min = total_bookings / days_in_period if days_in_period > 0 else 0
            
            # Calculate average wait time
            wait_times = []
            for booking in bucket_bookings:
                if booking.grouped_at:
                    wait_seconds = (booking.grouped_at - booking.requested_at).total_seconds()
                    wait_times.append(wait_seconds)
            
            avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
            
            # Calculate probability score
            probability_score = self._calculate_probability_score(
                avg_bookings_per_30min,
                avg_wait_time
            )
            
            # Update or create historical record
            existing = self.db.query(HistoricalArrivalData).filter(
                and_(
                    HistoricalArrivalData.route_id == route_id,
                    HistoricalArrivalData.day_of_week == day,
                    HistoricalArrivalData.hour_of_day == hour,
                    HistoricalArrivalData.time_slot == time_slot
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.total_bookings = total_bookings
                existing.avg_bookings_per_30min = avg_bookings_per_30min
                existing.avg_wait_time_seconds = int(avg_wait_time)
                existing.arrival_probability_score = probability_score
                records_updated += 1
            else:
                # Create new record
                new_record = HistoricalArrivalData(
                    route_id=route_id,
                    day_of_week=day,
                    hour_of_day=hour,
                    time_slot=time_slot,
                    total_bookings=total_bookings,
                    avg_bookings_per_30min=avg_bookings_per_30min,
                    avg_wait_time_seconds=int(avg_wait_time),
                    arrival_probability_score=probability_score
                )
                self.db.add(new_record)
                records_created += 1
        
        self.db.commit()
        
        stats = {
            "records_created": records_created,
            "records_updated": records_updated,
            "total_bookings_processed": len(bookings),
            "time_buckets": len(time_buckets)
        }
        
        logger.info(f"Historical data build complete: {stats}")
        return stats
    
    def _calculate_probability_score(
        self,
        avg_bookings_per_30min: float,
        avg_wait_time: float
    ) -> float:
        """
        Calculate probability score from metrics
        
        Logic:
        - Higher booking frequency = higher probability
        - Shorter wait times = higher probability (fast-moving demand)
        
        Returns: 0-100 score
        """
        
        # Booking frequency component (0-70 points)
        # 0-1 bookings = 20, 1-2 = 40, 2-3 = 60, 3+ = 70
        if avg_bookings_per_30min >= 3:
            frequency_score = 70
        elif avg_bookings_per_30min >= 2:
            frequency_score = 60
        elif avg_bookings_per_30min >= 1:
            frequency_score = 40
        else:
            frequency_score = 20
        
        # Wait time component (0-30 points)
        # Short wait = high score (indicates quick arrivals)
        wait_minutes = avg_wait_time / 60
        if wait_minutes < 2:
            wait_score = 30
        elif wait_minutes < 5:
            wait_score = 20
        elif wait_minutes < 10:
            wait_score = 10
        else:
            wait_score = 5
        
        total_score = frequency_score + wait_score
        
        return round(total_score, 2)
    
    def get_demand_heatmap(
        self,
        route_id: int
    ) -> List[Dict]:
        """
        Get demand heatmap for visualization
        Shows which hours have highest demand
        
        Returns: List of {day, hour, score}
        """
        
        heatmap_data = self.db.query(HistoricalArrivalData).filter(
            HistoricalArrivalData.route_id == route_id
        ).all()
        
        result = []
        for record in heatmap_data:
            result.append({
                'day_of_week': self._day_name(record.day_of_week),
                'hour': record.hour_of_day,
                'time_slot': record.time_slot,
                'demand_score': record.arrival_probability_score,
                'avg_bookings': record.avg_bookings_per_30min,
                'avg_wait_mins': round(record.avg_wait_time_seconds / 60, 1)
            })
        
        # Sort by demand score
        result.sort(key=lambda x: x['demand_score'], reverse=True)
        
        return result
    
    def get_peak_hours(
        self,
        route_id: int,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Get top peak hours for a route
        """
        
        peak_hours = self.db.query(HistoricalArrivalData).filter(
            HistoricalArrivalData.route_id == route_id
        ).order_by(
            HistoricalArrivalData.arrival_probability_score.desc()
        ).limit(top_n).all()
        
        return [
            {
                'day': self._day_name(record.day_of_week),
                'hour': record.hour_of_day,
                'time_slot': record.time_slot,
                'probability': record.arrival_probability_score,
                'avg_bookings_per_30min': record.avg_bookings_per_30min
            }
            for record in peak_hours
        ]
    
    def predict_next_arrival_time(
        self,
        route_id: int,
        current_time: datetime
    ) -> Optional[Dict]:
        """
        Predict when the next passenger is likely to arrive
        
        Returns: {
            'estimated_arrival_seconds': int,
            'confidence': str,
            'reasoning': str
        }
        """
        
        probability = self.get_arrival_probability(route_id, current_time)
        
        day = current_time.weekday() + 1
        hour = current_time.hour
        
        historical_data = self.db.query(HistoricalArrivalData).filter(
            and_(
                HistoricalArrivalData.route_id == route_id,
                HistoricalArrivalData.day_of_week == day,
                HistoricalArrivalData.hour_of_day == hour
            )
        ).first()
        
        if not historical_data:
            return None
        
        # Estimate arrival time based on average booking rate
        if historical_data.avg_bookings_per_30min > 0:
            # Calculate average time between bookings
            avg_seconds_between = (30 * 60) / historical_data.avg_bookings_per_30min
            
            confidence = 'HIGH' if probability > 70 else 'MEDIUM' if probability > 40 else 'LOW'
            
            return {
                'estimated_arrival_seconds': int(avg_seconds_between),
                'confidence': confidence,
                'reasoning': f"Based on {historical_data.avg_bookings_per_30min:.1f} bookings/30min average"
            }
        
        return None
    
    @staticmethod
    def _day_name(day_num: int) -> str:
        """Convert day number to name"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[day_num - 1] if 1 <= day_num <= 7 else 'Unknown'


class HistoricalDataBuilder:
    """
    Scheduled job to rebuild historical data daily
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.learner = HistoricalLearner(db)
    
    def rebuild_all_routes(self, lookback_days: int = 30) -> Dict:
        """
        Rebuild historical data for all active routes
        Should be run daily as a scheduled job
        """
        
        from app.models.driver import Route
        
        active_routes = self.db.query(Route).filter(Route.is_active == True).all()
        
        logger.info(f"Rebuilding historical data for {len(active_routes)} routes")
        
        total_stats = {
            'routes_processed': 0,
            'total_records_created': 0,
            'total_records_updated': 0,
            'total_bookings_processed': 0
        }
        
        for route in active_routes:
            try:
                stats = self.learner.build_historical_data(route.id, lookback_days)
                
                total_stats['routes_processed'] += 1
                total_stats['total_records_created'] += stats['records_created']
                total_stats['total_records_updated'] += stats['records_updated']
                total_stats['total_bookings_processed'] += stats['total_bookings_processed']
                
            except Exception as e:
                logger.error(f"Error processing route {route.id}: {e}")
        
        logger.info(f"Historical data rebuild complete: {total_stats}")
        return total_stats