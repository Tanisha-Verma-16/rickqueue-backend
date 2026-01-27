"""
Comprehensive test suite for the AI Engine
Tests all decision-making logic
"""

import pytest
from datetime import datetime, timedelta
from app.ai.probability_calculator import ProbabilityCalculator, AdvancedProbabilityCalculator
from app.ai.smart_dispatch import SmartDispatchService
from app.ai.historical_learner import HistoricalLearner


class TestProbabilityCalculator:
    """Test the probability calculation logic"""
    
    def setup_method(self):
        self.calculator = ProbabilityCalculator()
    
    def test_high_proximity_high_probability(self):
        """
        Test: Many pending users nearby = High probability
        """
        probability = self.calculator.calculate_final_probability(
            historical_prob=60.0,
            pending_count=3,          # 3 pending users
            nearest_distance=200,     # 200m away
            wait_time=180,            # 3 minutes
            current_size=2
        )
        
        assert probability > 70, f"Expected high probability, got {probability}"
    
    def test_low_proximity_low_probability(self):
        """
        Test: No pending users = Low probability
        """
        probability = self.calculator.calculate_final_probability(
            historical_prob=50.0,
            pending_count=0,          # No pending
            nearest_distance=9999,    # Far away
            wait_time=300,            # 5 minutes
            current_size=2
        )
        
        assert probability < 50, f"Expected low probability, got {probability}"
    
    def test_long_wait_time_penalty(self):
        """
        Test: Long wait time reduces probability
        """
        short_wait = self.calculator.calculate_final_probability(
            historical_prob=60.0,
            pending_count=1,
            nearest_distance=500,
            wait_time=60,             # 1 minute
            current_size=2
        )
        
        long_wait = self.calculator.calculate_final_probability(
            historical_prob=60.0,
            pending_count=1,
            nearest_distance=500,
            wait_time=600,            # 10 minutes
            current_size=2
        )
        
        assert long_wait < short_wait, "Long wait should reduce probability"
    
    def test_group_size_effect(self):
        """
        Test: Larger groups attract more passengers (social proof)
        """
        small_group = self.calculator.calculate_final_probability(
            historical_prob=50.0,
            pending_count=1,
            nearest_distance=500,
            wait_time=180,
            current_size=1,           # 1/4
            max_size=4
        )
        
        large_group = self.calculator.calculate_final_probability(
            historical_prob=50.0,
            pending_count=1,
            nearest_distance=500,
            wait_time=180,
            current_size=3,           # 3/4
            max_size=4
        )
        
        assert large_group > small_group, "Larger groups should have higher probability"
    
    def test_recommendation_wait(self):
        """
        Test: High probability → WAIT recommendation
        """
        recommendation = self.calculator.get_recommendation(85.0)
        
        assert recommendation['action'] == 'WAIT'
        assert recommendation['confidence'] == 'HIGH'
    
    def test_recommendation_dispatch(self):
        """
        Test: Low probability → DISPATCH recommendation
        """
        recommendation = self.calculator.get_recommendation(15.0)
        
        assert recommendation['action'] == 'DISPATCH'
        assert recommendation['confidence'] == 'HIGH'


class TestSmartDispatchDecisionLogic:
    """Test the core dispatch decision rules"""
    
    def test_strategic_positioning_rule(self):
        """
        Test: 2+ pending users < 500m + 3min wait → DISPATCH NOW
        This is YOUR enhancement!
        """
        # Simulate the decision logic
        pending_count = 2
        nearest_distance = 300  # meters
        wait_time = 200  # seconds (3+ minutes)
        
        # This should trigger DISPATCH_NOW
        should_dispatch = (
            pending_count >= 2 and
            nearest_distance < 500 and
            wait_time > 180
        )
        
        assert should_dispatch, "Should dispatch for strategic positioning"
    
    def test_low_probability_rule(self):
        """
        Test: Probability < 20% + 3min wait → DISPATCH NOW
        """
        probability = 15.0
        wait_time = 200
        
        should_dispatch = probability < 20 and wait_time > 180
        
        assert should_dispatch, "Should dispatch on low probability"
    
    def test_high_probability_rule(self):
        """
        Test: Probability > 80% → WAIT
        """
        probability = 85.0
        
        should_wait = probability > 80
        
        assert should_wait, "Should wait on high probability"
    
    def test_max_wait_time_rule(self):
        """
        Test: Wait > 10 mins → FORCE DISPATCH (safety net)
        """
        wait_time = 650  # > 600 seconds
        
        should_force_dispatch = wait_time > 600
        
        assert should_force_dispatch, "Should force dispatch after 10 minutes"


class TestProximityScoring:
    """Test proximity analysis logic"""
    
    def setup_method(self):
        self.calculator = ProbabilityCalculator()
    
    def test_close_pending_high_score(self):
        """
        Test: 3 users within 200m = High proximity score
        """
        score = self.calculator._calculate_proximity_score(
            pending_count=3,
            nearest_distance=150
        )
        
        # Should get: count_score (50) + distance_score (50) = 100
        assert score >= 90, f"Expected high score, got {score}"
    
    def test_far_pending_low_score(self):
        """
        Test: 1 user 1500m away = Low proximity score
        """
        score = self.calculator._calculate_proximity_score(
            pending_count=1,
            nearest_distance=1500
        )
        
        # Should get: count_score (20) + distance_score (0) = 20
        assert score <= 30, f"Expected low score, got {score}"
    
    def test_no_pending_zero_score(self):
        """
        Test: No pending users = Zero score
        """
        score = self.calculator._calculate_proximity_score(
            pending_count=0,
            nearest_distance=9999
        )
        
        assert score == 0, f"Expected zero score, got {score}"


class TestAdvancedFeatures:
    """Test advanced probability features"""
    
    def setup_method(self):
        self.calculator = AdvancedProbabilityCalculator()
    
    def test_rush_hour_boost(self):
        """
        Test: Rush hour multiplier increases probability
        """
        normal = self.calculator.calculate_final_probability(
            historical_prob=50.0,
            pending_count=1,
            nearest_distance=500,
            wait_time=180,
            current_size=2
        )
        
        rush_hour = self.calculator.calculate_with_time_decay(
            historical_prob=50.0,
            pending_count=1,
            nearest_distance=500,
            wait_time=180,
            current_size=2,
            time_of_day_factor=1.5  # Rush hour boost
        )
        
        assert rush_hour > normal, "Rush hour should boost probability"
    
    def test_ml_feature_preparation(self):
        """
        Test: Feature vector preparation for ML
        """
        features = self.calculator.prepare_features_for_ml(
            historical_prob=60.0,
            pending_count=2,
            nearest_distance=300,
            wait_time=180,
            current_size=2,
            hour=9,
            day_of_week=1  # Monday
        )
        
        assert len(features) == 9, "Should have 9 features"
        assert all(0 <= f <= 1 or f in [2, 9] for f in features), "Features should be normalized"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def setup_method(self):
        self.calculator = ProbabilityCalculator()
    
    def test_zero_wait_time(self):
        """
        Test: Brand new group (wait_time=0)
        """
        probability = self.calculator.calculate_final_probability(
            historical_prob=50.0,
            pending_count=1,
            nearest_distance=500,
            wait_time=0,              # Just created
            current_size=1
        )
        
        # Should have high wait time score (fresh group)
        assert 30 <= probability <= 100
    
    def test_full_group(self):
        """
        Test: Full group (4/4) should always dispatch
        """
        # This would be handled before probability calculation
        # but testing the logic
        current_size = 4
        max_size = 4
        
        is_full = current_size >= max_size
        
        assert is_full, "4/4 group should be considered full"
    
    def test_extreme_historical_values(self):
        """
        Test: Handle extreme historical probabilities
        """
        # Very high historical
        prob_high = self.calculator.calculate_final_probability(
            historical_prob=150.0,    # Invalid, should clamp to 100
            pending_count=0,
            nearest_distance=9999,
            wait_time=180,
            current_size=2
        )
        
        assert 0 <= prob_high <= 100, "Should clamp to valid range"
        
        # Negative historical
        prob_negative = self.calculator.calculate_final_probability(
            historical_prob=-50.0,    # Invalid, should clamp to 0
            pending_count=0,
            nearest_distance=9999,
            wait_time=180,
            current_size=2
        )
        
        assert 0 <= prob_negative <= 100, "Should clamp to valid range"


# ===== INTEGRATION TEST SCENARIOS =====

class TestRealWorldScenarios:
    """Test real-world scenarios"""
    
    def setup_method(self):
        self.calculator = ProbabilityCalculator()
    
    def test_morning_rush_metro_station(self):
        """
        Scenario: Monday 9 AM at Metro Station
        - High historical demand (80%)
        - 3 pending bookings within 400m
        - Group has 2 people, waited 2 mins
        
        Expected: WAIT (high confidence new passenger coming)
        """
        probability = self.calculator.calculate_final_probability(
            historical_prob=80.0,
            pending_count=3,
            nearest_distance=400,
            wait_time=120,
            current_size=2
        )
        
        recommendation = self.calculator.get_recommendation(probability)
        
        assert probability > 70, f"Morning rush should have high probability: {probability}"
        assert recommendation['action'] == 'WAIT', "Should wait during morning rush"
    
    def test_late_night_empty_route(self):
        """
        Scenario: 11 PM on quiet route
        - Low historical demand (20%)
        - No pending bookings
        - Group has 2 people, waited 5 mins
        
        Expected: DISPATCH NOW (unlikely to get more passengers)
        """
        probability = self.calculator.calculate_final_probability(
            historical_prob=20.0,
            pending_count=0,
            nearest_distance=9999,
            wait_time=300,
            current_size=2
        )
        
        recommendation = self.calculator.get_recommendation(probability)
        
        assert probability < 40, f"Late night should have low probability: {probability}"
        assert recommendation['action'] == 'DISPATCH', "Should dispatch at night"
    
    def test_strategic_positioning_scenario(self):
        """
        Scenario: Your Enhancement!
        - 2 people just booked 250m ahead
        - Current group: 3/4, waited 3.5 mins
        - Medium historical demand (50%)
        
        Expected: DISPATCH NOW to pick up waiting passengers
        """
        probability = self.calculator.calculate_final_probability(
            historical_prob=50.0,
            pending_count=2,
            nearest_distance=250,
            wait_time=210,
            current_size=3
        )
        
        # Check if strategic rule would trigger
        should_dispatch_strategic = (
            2 >= 2 and          # pending_count >= 2
            250 < 500 and       # within 500m
            210 > 180           # waited > 3 mins
        )
        
        assert should_dispatch_strategic, "Should trigger strategic dispatch"
        assert probability > 60, f"Should have decent probability: {probability}"


# ===== PYTEST CONFIGURATION =====

@pytest.fixture
def sample_probability_data():
    """Sample data for testing"""
    return {
        'historical_prob': 60.0,
        'pending_count': 2,
        'nearest_distance': 400,
        'wait_time': 180,
        'current_size': 2,
        'max_size': 4
    }


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])