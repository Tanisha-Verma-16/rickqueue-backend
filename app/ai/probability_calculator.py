"""
🎲 PROBABILITY CALCULATOR
Combines multiple data sources to predict: "Will a new passenger arrive in 60 seconds?"

This is a WEIGHTED ALGORITHM simulating ML (for MVP).
In production, this could be replaced with a trained scikit-learn model.
"""

import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ProbabilityCalculator:
    """
    Calculates the final probability of a new passenger arriving
    Based on multiple weighted factors
    """
    
    # Weight Distribution (total = 100%)
    WEIGHTS = {
        'historical': 0.40,      # 40% - Past patterns are strong indicators
        'proximity': 0.35,       # 35% - Real-time pending bookings (YOUR ENHANCEMENT)
        'wait_time': 0.15,       # 15% - Urgency factor
        'group_size': 0.10       # 10% - How close to full
    }
    
    def calculate_final_probability(
        self,
        historical_prob: float,
        pending_count: int,
        nearest_distance: int,
        wait_time: int,
        current_size: int,
        max_size: int = 4
    ) -> float:
        """
        Main calculation method
        
        Args:
            historical_prob: Probability from historical data (0-100)
            pending_count: Number of pending bookings
            nearest_distance: Distance to nearest pending user (meters)
            wait_time: Current wait time (seconds)
            current_size: Current group size
            max_size: Max group capacity
            
        Returns:
            Final probability score (0-100)
        """
        
        # Calculate individual components
        historical_score = self._normalize_historical(historical_prob)
        proximity_score = self._calculate_proximity_score(pending_count, nearest_distance)
        wait_time_score = self._calculate_wait_time_score(wait_time)
        group_size_score = self._calculate_group_size_score(current_size, max_size)
        
        # Weighted combination
        final_probability = (
            historical_score * self.WEIGHTS['historical'] +
            proximity_score * self.WEIGHTS['proximity'] +
            wait_time_score * self.WEIGHTS['wait_time'] +
            group_size_score * self.WEIGHTS['group_size']
        )
        
        # Clamp to 0-100 range
        final_probability = np.clip(final_probability, 0, 100)
        
        logger.debug(
            f"Probability Calculation:\n"
            f"  Historical: {historical_score:.1f} (weight: {self.WEIGHTS['historical']})\n"
            f"  Proximity: {proximity_score:.1f} (weight: {self.WEIGHTS['proximity']})\n"
            f"  Wait Time: {wait_time_score:.1f} (weight: {self.WEIGHTS['wait_time']})\n"
            f"  Group Size: {group_size_score:.1f} (weight: {self.WEIGHTS['group_size']})\n"
            f"  FINAL: {final_probability:.1f}%"
        )
        
        return round(final_probability, 2)
    
    def _normalize_historical(self, historical_prob: float) -> float:
        """
        Normalize historical probability to 0-100 scale
        """
        return np.clip(historical_prob, 0, 100)
    
    def _calculate_proximity_score(self, pending_count: int, nearest_distance: int) -> float:
        """
        Calculate score based on pending bookings
        
        Logic:
        - More pending bookings = higher probability
        - Closer pending users = higher probability
        
        Returns: 0-100 score
        """
        if pending_count == 0:
            return 0.0
        
        # Count factor: 0-50 points
        # 1 pending = 20, 2 = 40, 3+ = 50
        count_score = min(pending_count * 20, 50)
        
        # Distance factor: 0-50 points
        # < 200m = 50, 200-500m = 30, 500-1000m = 10, >1000m = 0
        if nearest_distance < 200:
            distance_score = 50
        elif nearest_distance < 500:
            distance_score = 30
        elif nearest_distance < 1000:
            distance_score = 10
        else:
            distance_score = 0
        
        total_score = count_score + distance_score
        
        logger.debug(
            f"Proximity Score: count={pending_count} ({count_score}pts), "
            f"distance={nearest_distance}m ({distance_score}pts) → {total_score}/100"
        )
        
        return total_score
    
    def _calculate_wait_time_score(self, wait_time_seconds: int) -> float:
        """
        Calculate score based on how long the group has been waiting
        
        Logic:
        - Longer wait = LOWER probability (people give up)
        - Exponential decay after 5 minutes
        
        Returns: 0-100 score
        """
        wait_minutes = wait_time_seconds / 60
        
        if wait_minutes < 1:
            # Very fresh group - assume high demand
            return 80.0
        elif wait_minutes < 3:
            # Normal wait - still good
            return 60.0
        elif wait_minutes < 5:
            # Getting long - moderate
            return 40.0
        elif wait_minutes < 10:
            # Too long - low probability
            return 20.0
        else:
            # Extremely long - almost zero
            return 5.0
    
    def _calculate_group_size_score(self, current_size: int, max_size: int) -> float:
        """
        Calculate score based on how close to full the group is
        
        Logic:
        - Closer to full = higher probability (social proof effect)
        - 3/4 people are more likely to attract the 4th
        
        Returns: 0-100 score
        """
        fill_ratio = current_size / max_size
        
        if fill_ratio >= 0.75:  # 3/4 or more
            return 90.0
        elif fill_ratio >= 0.5:  # 2/4
            return 60.0
        elif fill_ratio >= 0.25:  # 1/4
            return 30.0
        else:
            return 10.0
    
    def calculate_confidence_interval(
        self,
        probability: float,
        sample_size: int = 100
    ) -> tuple[float, float]:
        """
        Calculate 95% confidence interval for the probability
        Useful for showing uncertainty to drivers
        
        Returns: (lower_bound, upper_bound)
        """
        # Simple confidence interval calculation
        # In production, use proper statistical methods
        
        std_error = np.sqrt((probability * (100 - probability)) / sample_size)
        margin = 1.96 * std_error  # 95% confidence
        
        lower = max(0, probability - margin)
        upper = min(100, probability + margin)
        
        return (round(lower, 1), round(upper, 1))
    
    def get_recommendation(self, probability: float) -> dict:
        """
        Convert probability to actionable recommendation
        
        Returns: {
            'action': 'WAIT' | 'DISPATCH',
            'confidence': 'HIGH' | 'MEDIUM' | 'LOW',
            'message': str
        }
        """
        if probability >= 80:
            return {
                'action': 'WAIT',
                'confidence': 'HIGH',
                'message': f'{probability:.0f}% chance - Wait for next passenger'
            }
        elif probability >= 50:
            return {
                'action': 'WAIT',
                'confidence': 'MEDIUM',
                'message': f'{probability:.0f}% chance - Monitor for 1-2 minutes'
            }
        elif probability >= 20:
            return {
                'action': 'DISPATCH',
                'confidence': 'MEDIUM',
                'message': f'{probability:.0f}% chance - Consider dispatching soon'
            }
        else:
            return {
                'action': 'DISPATCH',
                'confidence': 'HIGH',
                'message': f'{probability:.0f}% chance - Dispatch now to avoid wait'
            }


class AdvancedProbabilityCalculator(ProbabilityCalculator):
    """
    Extended version with machine learning preparation
    Can be replaced with actual ML model later
    """
    
    def calculate_with_time_decay(
        self,
        historical_prob: float,
        pending_count: int,
        nearest_distance: int,
        wait_time: int,
        current_size: int,
        time_of_day_factor: float = 1.0,
        day_of_week_factor: float = 1.0
    ) -> float:
        """
        Advanced calculation with temporal factors
        
        Args:
            time_of_day_factor: Multiplier for time of day (rush hour = 1.5)
            day_of_week_factor: Multiplier for day (weekend = 0.8)
        """
        
        base_probability = self.calculate_final_probability(
            historical_prob,
            pending_count,
            nearest_distance,
            wait_time,
            current_size
        )
        
        # Apply temporal adjustments
        adjusted = base_probability * time_of_day_factor * day_of_week_factor
        
        return np.clip(adjusted, 0, 100)
    
    def prepare_features_for_ml(
        self,
        historical_prob: float,
        pending_count: int,
        nearest_distance: int,
        wait_time: int,
        current_size: int,
        hour: int,
        day_of_week: int
    ) -> np.ndarray:
        """
        Prepare feature vector for ML model training
        Returns: numpy array ready for scikit-learn
        
        Features:
        [0] historical_prob
        [1] pending_count
        [2] nearest_distance (normalized)
        [3] wait_time (normalized)
        [4] current_size
        [5] hour (0-23)
        [6] day_of_week (0-6)
        [7] is_rush_hour (boolean)
        [8] is_weekend (boolean)
        """
        
        # Normalize distance (0-2000m → 0-1)
        norm_distance = min(nearest_distance / 2000, 1.0)
        
        # Normalize wait time (0-600s → 0-1)
        norm_wait = min(wait_time / 600, 1.0)
        
        # Rush hour detection (7-9 AM, 5-7 PM)
        is_rush_hour = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
        
        # Weekend detection
        is_weekend = 1 if day_of_week >= 5 else 0
        
        features = np.array([
            historical_prob / 100,  # Normalize to 0-1
            pending_count,
            norm_distance,
            norm_wait,
            current_size,
            hour / 24,  # Normalize to 0-1
            day_of_week / 7,  # Normalize to 0-1
            is_rush_hour,
            is_weekend
        ])
        
        return features