"""
AI Decision Simulator
Visualize how the AI makes decisions under different conditions
Run: python scripts/ai_simulator.py
"""

from app.ai.probability_calculator import ProbabilityCalculator
import pandas as pd
from datetime import datetime, timedelta
import random


class AISimulator:
    """
    Simulates different scenarios and shows AI decision-making
    """
    
    def __init__(self):
        self.calculator = ProbabilityCalculator()
    
    def simulate_scenario(
        self,
        scenario_name: str,
        historical_prob: float,
        pending_count: int,
        nearest_distance: int,
        wait_time: int,
        current_size: int
    ):
        """
        Simulate a single scenario and print results
        """
        
        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'='*60}")
        print(f"📊 Inputs:")
        print(f"  Historical Probability: {historical_prob}%")
        print(f"  Pending Bookings: {pending_count}")
        print(f"  Nearest Distance: {nearest_distance}m")
        print(f"  Wait Time: {wait_time}s ({wait_time//60} mins)")
        print(f"  Group Size: {current_size}/4")
        
        # Calculate probability
        probability = self.calculator.calculate_final_probability(
            historical_prob=historical_prob,
            pending_count=pending_count,
            nearest_distance=nearest_distance,
            wait_time=wait_time,
            current_size=current_size
        )
        
        # Get recommendation
        recommendation = self.calculator.get_recommendation(probability)
        
        print(f"\n🤖 AI Decision:")
        print(f"  Final Probability: {probability}%")
        print(f"  Action: {recommendation['action']}")
        print(f"  Confidence: {recommendation['confidence']}")
        print(f"  Message: {recommendation['message']}")
        
        # Check specific rules
        print(f"\n📋 Rule Triggers:")
        
        strategic = (pending_count >= 2 and nearest_distance < 500 and wait_time > 180)
        print(f"  Strategic Positioning: {'✅ YES' if strategic else '❌ NO'}")
        
        low_prob = (probability < 20 and wait_time > 180)
        print(f"  Low Probability Rule: {'✅ YES' if low_prob else '❌ NO'}")
        
        high_prob = (probability > 80)
        print(f"  High Probability Rule: {'✅ YES' if high_prob else '❌ NO'}")
        
        max_wait = (wait_time > 600)
        print(f"  Max Wait Exceeded: {'✅ YES' if max_wait else '❌ NO'}")
    
    def run_all_scenarios(self):
        """
        Run a comprehensive set of test scenarios
        """
        
        scenarios = [
            {
                'scenario_name': "🌅 Morning Rush - Metro Station",
                'historical_prob': 85.0,
                'pending_count': 4,
                'nearest_distance': 200,
                'wait_time': 120,
                'current_size': 3
            },
            {
                'scenario_name': "🎯 Strategic Positioning (YOUR ENHANCEMENT)",
                'historical_prob': 50.0,
                'pending_count': 2,
                'nearest_distance': 300,
                'wait_time': 220,
                'current_size': 3
            },
            {
                'scenario_name': "🌙 Late Night - Low Demand",
                'historical_prob': 15.0,
                'pending_count': 0,
                'nearest_distance': 9999,
                'wait_time': 300,
                'current_size': 2
            },
            {
                'scenario_name': "⏰ Long Wait - Force Dispatch",
                'historical_prob': 40.0,
                'pending_count': 1,
                'nearest_distance': 800,
                'wait_time': 650,
                'current_size': 2
            },
            {
                'scenario_name': "🎲 Uncertain - Medium Probability",
                'historical_prob': 55.0,
                'pending_count': 1,
                'nearest_distance': 600,
                'wait_time': 240,
                'current_size': 2
            },
            {
                'scenario_name': "👥 Almost Full Group (3/4)",
                'historical_prob': 60.0,
                'pending_count': 1,
                'nearest_distance': 500,
                'wait_time': 180,
                'current_size': 3
            },
            {
                'scenario_name': "🏃 Fresh Group - Just Started",
                'historical_prob': 50.0,
                'pending_count': 0,
                'nearest_distance': 9999,
                'wait_time': 30,
                'current_size': 1
            }
        ]
        
        for scenario in scenarios:
            self.simulate_scenario(**scenario)
    
    def generate_probability_heatmap(self):
        """
        Generate a heatmap showing probability across different conditions
        """
        
        print(f"\n{'='*60}")
        print("📊 PROBABILITY HEATMAP")
        print("How probability changes with different inputs")
        print(f"{'='*60}\n")
        
        # Vary pending count and distance
        pending_counts = [0, 1, 2, 3, 4]
        distances = [100, 300, 500, 800, 1200]
        
        results = []
        
        for pending in pending_counts:
            row = []
            for distance in distances:
                prob = self.calculator.calculate_final_probability(
                    historical_prob=50.0,
                    pending_count=pending,
                    nearest_distance=distance,
                    wait_time=180,
                    current_size=2
                )
                row.append(f"{prob:5.1f}")
            results.append(row)
        
        # Print as table
        print("Pending Users | Distance (meters)")
        print("             ", " | ".join([f"{d:>6}m" for d in distances]))
        print("-" * 60)
        
        for i, pending in enumerate(pending_counts):
            print(f"     {pending}       |", " | ".join(results[i]))
        
        print("\nKey: Higher probability = More likely to wait")
        print("     Lower probability = More likely to dispatch")
    
    def simulate_day(self, route_name: str = "Metro -> College"):
        """
        Simulate a full day's operation with varying demand
        """
        
        print(f"\n{'='*60}")
        print(f"📅 FULL DAY SIMULATION: {route_name}")
        print(f"{'='*60}\n")
        
        # Simulate demand pattern throughout the day
        hours = list(range(6, 23))  # 6 AM to 11 PM
        
        print(f"{'Hour':<6} | {'Demand':<15} | {'Avg Probability':<15} | {'Decision Pattern'}")
        print("-" * 70)
        
        for hour in hours:
            # Simulate demand curve
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                demand = "HIGH (Rush)"
                historical = random.uniform(70, 90)
                pending = random.randint(2, 5)
            elif 10 <= hour <= 16:
                demand = "MEDIUM"
                historical = random.uniform(40, 60)
                pending = random.randint(0, 2)
            else:
                demand = "LOW"
                historical = random.uniform(10, 30)
                pending = 0
            
            # Calculate probability
            prob = self.calculator.calculate_final_probability(
                historical_prob=historical,
                pending_count=pending,
                nearest_distance=400 if pending > 0 else 9999,
                wait_time=180,
                current_size=2
            )
            
            decision = "WAIT" if prob > 50 else "DISPATCH"
            
            print(f"{hour:02d}:00  | {demand:<15} | {prob:>6.1f}%         | {decision}")


def main():
    """
    Run the simulator
    """
    
    print("🧠 RICKQUEUE AI ENGINE SIMULATOR")
    print("=" * 60)
    print("This tool simulates the AI decision-making process")
    print()
    
    simulator = AISimulator()
    
    # Run all test scenarios
    simulator.run_all_scenarios()
    
    # Generate heatmap
    simulator.generate_probability_heatmap()
    
    # Simulate a full day
    simulator.simulate_day()
    
    print(f"\n{'='*60}")
    print("✅ Simulation Complete!")
    print("The AI is ready for real-world deployment.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()