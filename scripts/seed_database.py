"""
Database Seeding Script
Populate database with sample data for testing
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database.session import get_db_context
from app.models.driver import Route
from app.models.historical_data import HistoricalArrivalData
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_routes():
    """
    Seed sample routes
    """
    logger.info("🌱 Seeding routes...")
    
    routes = [
        {
            "route_code": "METRO_COLLEGE_A",
            "origin_name": "Metro Station Gate 1",
            "destination_name": "City College Main Gate",
            "origin_lat": 28.6139,
            "origin_lng": 77.2090,
            "dest_lat": 28.6289,
            "dest_lng": 77.2265,
            "distance_km": 5.2,
            "estimated_duration_mins": 15,
            "halfway_point_km": 2.6,
            "short_route_fare": 30.0,
            "full_route_fare": 50.0,
            "is_active": True
        },
        {
            "route_code": "MARKET_HOSPITAL_B",
            "origin_name": "Central Market",
            "destination_name": "City Hospital",
            "origin_lat": 28.6200,
            "origin_lng": 77.2100,
            "dest_lat": 28.6350,
            "dest_lng": 77.2250,
            "distance_km": 4.0,
            "estimated_duration_mins": 12,
            "halfway_point_km": 2.0,
            "short_route_fare": 25.0,
            "full_route_fare": 40.0,
            "is_active": True
        },
        {
            "route_code": "STATION_MALL_C",
            "origin_name": "Railway Station",
            "destination_name": "City Mall",
            "origin_lat": 28.6300,
            "origin_lng": 77.2150,
            "dest_lat": 28.6450,
            "dest_lng": 77.2300,
            "distance_km": 6.0,
            "estimated_duration_mins": 18,
            "halfway_point_km": 3.0,
            "short_route_fare": 35.0,
            "full_route_fare": 60.0,
            "is_active": True
        }
    ]
    
    with get_db_context() as db:
        for route_data in routes:
            existing = db.query(Route).filter(
                Route.route_code == route_data['route_code']
            ).first()
            
            if not existing:
                route = Route(**route_data)
                db.add(route)
                logger.info(f"✓ Created route: {route_data['route_code']}")
            else:
                logger.info(f"  Route already exists: {route_data['route_code']}")
    
    logger.info("✅ Routes seeded successfully!")


def seed_historical_data():
    """
    Seed sample historical data for AI
    """
    logger.info("🌱 Seeding historical data...")
    
    with get_db_context() as db:
        routes = db.query(Route).all()
        
        if not routes:
            logger.warning("⚠ No routes found. Seed routes first!")
            return
        
        # Create sample historical data for each route
        for route in routes:
            # Rush hours (7-9 AM, 5-7 PM)
            rush_hours = [7, 8, 9, 17, 18, 19]
            # Normal hours
            normal_hours = [10, 11, 12, 13, 14, 15, 16]
            # Low hours
            low_hours = [6, 20, 21, 22]
            
            # Weekdays (Mon-Fri)
            for day in range(1, 6):
                # Rush hours
                for hour in rush_hours:
                    data = HistoricalArrivalData(
                        route_id=route.id,
                        day_of_week=day,
                        hour_of_day=hour,
                        time_slot=f"{hour:02d}:00-{hour:02d}:30",
                        total_bookings=45,
                        avg_bookings_per_30min=3.5,
                        avg_wait_time_seconds=120,
                        total_early_dispatches=2,
                        arrival_probability_score=85.0
                    )
                    db.add(data)
                
                # Normal hours
                for hour in normal_hours:
                    data = HistoricalArrivalData(
                        route_id=route.id,
                        day_of_week=day,
                        hour_of_day=hour,
                        time_slot=f"{hour:02d}:00-{hour:02d}:30",
                        total_bookings=25,
                        avg_bookings_per_30min=2.0,
                        avg_wait_time_seconds=180,
                        total_early_dispatches=5,
                        arrival_probability_score=55.0
                    )
                    db.add(data)
                
                # Low hours
                for hour in low_hours:
                    data = HistoricalArrivalData(
                        route_id=route.id,
                        day_of_week=day,
                        hour_of_day=hour,
                        time_slot=f"{hour:02d}:00-{hour:02d}:30",
                        total_bookings=10,
                        avg_bookings_per_30min=0.8,
                        avg_wait_time_seconds=300,
                        total_early_dispatches=8,
                        arrival_probability_score=25.0
                    )
                    db.add(data)
            
            # Weekends (Sat-Sun) - generally lower demand
            for day in range(6, 8):
                for hour in range(6, 23):
                    data = HistoricalArrivalData(
                        route_id=route.id,
                        day_of_week=day,
                        hour_of_day=hour,
                        time_slot=f"{hour:02d}:00-{hour:02d}:30",
                        total_bookings=15,
                        avg_bookings_per_30min=1.2,
                        avg_wait_time_seconds=240,
                        total_early_dispatches=6,
                        arrival_probability_score=40.0
                    )
                    db.add(data)
            
            logger.info(f"✓ Created historical data for route: {route.route_code}")
    
    logger.info("✅ Historical data seeded successfully!")


def seed_all():
    """
    Seed all data
    """
    logger.info("\n" + "="*60)
    logger.info("🌱 SEEDING DATABASE")
    logger.info("="*60 + "\n")
    
    seed_routes()
    print()
    seed_historical_data()
    
    logger.info("\n" + "="*60)
    logger.info("✅ DATABASE SEEDING COMPLETE!")
    logger.info("="*60 + "\n")
    logger.info("You can now:")
    logger.info("  1. Start the backend server")
    logger.info("  2. Test the APIs with sample routes")
    logger.info("  3. Watch the AI make decisions!")
    logger.info("")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed RickQueue database")
    parser.add_argument(
        '--type',
        choices=['all', 'routes', 'historical'],
        default='all',
        help='Type of data to seed'
    )
    
    args = parser.parse_args()
    
    if args.type == 'all':
        seed_all()
    elif args.type == 'routes':
        seed_routes()
    elif args.type == 'historical':
        seed_historical_data()