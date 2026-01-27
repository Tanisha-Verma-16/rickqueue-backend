"""
🧠 SMART DISPATCH ENGINE - The Core AI Logic
Runs every 30 seconds to analyze forming groups and make dispatch decisions
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.ride_group import RideGroup, GroupStatus, DispatchDecisionType
from app.models.booking_request import BookingRequest
from app.ai.probability_calculator import ProbabilityCalculator
from app.ai.proximity_analyzer import ProximityAnalyzer
from app.ai.historical_learner import HistoricalLearner
from app.services.notification_service import get_notification_service
from app.utils.qr_generator import generate_qr_code
from app.database.session import get_db

import logging

logger = logging.getLogger(__name__)


class SmartDispatchService:
    """
    The AI brain that decides:
    - WAIT: Hold for more passengers
    - DISPATCH_NOW: Send the rickshaw with current passengers
    """
    
    # Configuration
    CHECK_INTERVAL_SECONDS = 30
    PROBABILITY_THRESHOLD_LOW = 20  # Below this = dispatch
    PROBABILITY_THRESHOLD_HIGH = 80  # Above this = wait
    MIN_WAIT_TIME_SECONDS = 180  # 3 minutes
    MAX_WAIT_TIME_SECONDS = 600  # 10 minutes (force dispatch)
    
    def __init__(self, db: Session):
        self.db = db
        self.probability_calculator = ProbabilityCalculator()
        self.proximity_analyzer = ProximityAnalyzer(db)
        self.historical_learner = HistoricalLearner(db)
        self.notification_service = get_notification_service()
    
    def run_dispatch_analysis(self) -> Dict[str, int]:
        """
        Main AI loop - analyzes all forming groups
        Returns stats about the analysis
        """
        logger.info("🤖 AI Dispatch Analysis Started")
        
        # Find all groups currently forming
        forming_groups = self.db.query(RideGroup).filter(
            RideGroup.group_status == GroupStatus.FORMING
        ).all()
        
        stats = {
            "analyzed": len(forming_groups),
            "dispatched": 0,
            "waiting": 0,
            "skipped": 0
        }
        
        for group in forming_groups:
            try:
                decision = self._analyze_and_decide(group)
                stats[decision] += 1
            except Exception as e:
                logger.error(f"Error analyzing group {group.id}: {str(e)}")
                stats["skipped"] += 1
        
        logger.info(f"✅ Analysis complete: {stats}")
        return stats
    
    def _analyze_and_decide(self, group: RideGroup) -> str:
        """
        Core AI decision logic for a single group
        Returns: "dispatched", "waiting", or "skipped"
        """
        
        # RULE 0: If full, dispatch immediately
        if group.is_full():
            self._dispatch_group(group, DispatchDecisionType.FULL_GROUP, 100.0)
            return "dispatched"
        
        # Get wait time
        wait_time_seconds = group.get_wait_time_seconds()
        
        # Skip if too young (let it form)
        if wait_time_seconds < 60:
            logger.debug(f"Group {group.id} too young ({wait_time_seconds}s), skipping")
            return "skipped"
        
        logger.info(
            f"🔍 Analyzing Group {group.id} | "
            f"Size: {group.current_size}/{group.max_size} | "
            f"Wait: {wait_time_seconds}s"
        )
        
        # ===== STEP 1: Get Historical Probability =====
        historical_prob = self.historical_learner.get_arrival_probability(
            route_id=group.route_id,
            current_time=datetime.utcnow()
        )
        
        # ===== STEP 2: Analyze Pending Bookings (YOUR ENHANCEMENT) =====
        proximity_analysis = self.proximity_analyzer.analyze_pending_bookings(
            route_id=group.route_id,
            group=group
        )
        
        # ===== STEP 3: Calculate Final Probability =====
        final_probability = self.probability_calculator.calculate_final_probability(
            historical_prob=historical_prob,
            pending_count=proximity_analysis['pending_count'],
            nearest_distance=proximity_analysis['nearest_distance_meters'],
            wait_time=wait_time_seconds,
            current_size=group.current_size
        )
        
        # ===== STEP 4: Make Decision =====
        decision = self._make_decision(
            group=group,
            final_probability=final_probability,
            wait_time=wait_time_seconds,
            proximity_analysis=proximity_analysis
        )
        
        # ===== STEP 5: Log Decision =====
        self._log_decision(
            group=group,
            decision=decision,
            probability=final_probability,
            proximity_analysis=proximity_analysis
        )
        
        # ===== STEP 6: Execute Decision =====
        return self._execute_decision(group, decision, final_probability)
    
    def _make_decision(
        self,
        group: RideGroup,
        final_probability: float,
        wait_time: int,
        proximity_analysis: Dict
    ) -> Dict:
        """
        Decision logic with multiple rules
        Returns: {action: str, reasoning: str}
        """
        
        # RULE 1: Strategic Positioning (YOUR GENIUS ENHANCEMENT)
        if (proximity_analysis['pending_count'] >= 2 and
            proximity_analysis['nearest_distance_meters'] < 500 and
            wait_time > self.MIN_WAIT_TIME_SECONDS):
            
            return {
                "action": "DISPATCH_NOW",
                "reasoning": (
                    f"STRATEGIC: {proximity_analysis['pending_count']} users waiting within "
                    f"{proximity_analysis['nearest_distance_meters']}m - dispatch to secure them!"
                )
            }
        
        # RULE 2: Low Probability + Significant Wait
        if (final_probability < self.PROBABILITY_THRESHOLD_LOW and
            wait_time > self.MIN_WAIT_TIME_SECONDS):
            
            return {
                "action": "DISPATCH_NOW",
                "reasoning": (
                    f"Low arrival probability ({final_probability:.1f}%) + "
                    f"wait time {wait_time}s"
                )
            }
        
        # RULE 3: High Probability = Wait
        if final_probability > self.PROBABILITY_THRESHOLD_HIGH:
            return {
                "action": "WAIT",
                "reasoning": f"High arrival probability ({final_probability:.1f}%)"
            }
        
        # RULE 4: Maximum Wait Exceeded (Safety)
        if wait_time > self.MAX_WAIT_TIME_SECONDS:
            return {
                "action": "DISPATCH_NOW",
                "reasoning": f"Maximum wait time exceeded ({wait_time}s)"
            }
        
        # Default: WAIT (uncertain state)
        return {
            "action": "WAIT",
            "reasoning": f"Uncertain probability ({final_probability:.1f}%), continuing to wait"
        }
    
    def _execute_decision(
        self,
        group: RideGroup,
        decision: Dict,
        probability: float
    ) -> str:
        """Execute the AI's decision"""
        
        if decision["action"] == "DISPATCH_NOW":
            self._dispatch_group(group, DispatchDecisionType.EARLY_DISPATCH, probability)
            return "dispatched"
        else:
            # Notify users about waiting
            self.notification_service.notify_group_waiting(
                group_id=group.id,
                message=f"Hold tight! {decision['reasoning']}"
            )
            return "waiting"
    
    def _dispatch_group(
        self,
        group: RideGroup,
        decision_type: DispatchDecisionType,
        probability: float
    ):
        """
        Finalize and dispatch the group
        - Change status to READY (waiting for driver assignment)
        - Generate QR code
        - Calculate route optimization metrics
        - Notify members with ETA
        """
        logger.info(
            f"🚀 DISPATCHING Group {group.id} with {group.current_size} passengers "
            f"(Type: {decision_type.value})"
        )
        
        group.group_status = GroupStatus.READY
        group.dispatched_at = datetime.utcnow()
        group.dispatch_decision_type = decision_type
        group.dispatch_probability_score = probability
        group.qr_code = generate_qr_code(group.id)
        
        self.db.commit()
        
        # Update all booking requests to GROUPED
        self.db.query(BookingRequest).filter(
            BookingRequest.group_id == group.id
        ).update({
            "request_status": "GROUPED",
            "grouped_at": datetime.utcnow()
        })
        self.db.commit()
        
        # Notify members with group details (NO payment info)
        self.notification_service.notify_group_ready_sync(
            group_id=group.id,
            qr_code=group.qr_code,
            passenger_count=group.current_size
        )
    
    def _log_decision(
        self,
        group: RideGroup,
        decision: Dict,
        probability: float,
        proximity_analysis: Dict
    ):
        """Log AI decision for analytics"""
        from app.models.ride_group import DispatchDecisionLog
        
        log = DispatchDecisionLog(
            group_id=group.id,
            group_size_at_decision=group.current_size,
            wait_time_seconds=group.get_wait_time_seconds(),
            pending_bookings_count=proximity_analysis['pending_count'],
            nearest_pending_distance_meters=proximity_analysis['nearest_distance_meters'],
            historical_probability=proximity_analysis.get('historical_prob'),
            final_probability_score=probability,
            decision_made=decision['action'],
            reasoning=decision['reasoning']
        )
        
        self.db.add(log)
        self.db.commit()