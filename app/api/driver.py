"""
Driver API - Focus on Optimization Intelligence
Shows drivers: "Should I wait or move?" based on real-time data
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime, timedelta

from app.database.session import get_db
from app.services.auth_service import get_current_driver
from app.models.driver import Driver, Route
from app.models.ride_group import RideGroup, GroupStatus
from app.models.booking_request import BookingRequest
from app.schemas.driver_schema import (
    DriverDashboardResponse,
    RouteOpportunity,
    OptimizationSuggestion
)

router = APIRouter(prefix="/driver", tags=["Driver"])


@router.get("/dashboard", response_model=DriverDashboardResponse)
async def get_driver_dashboard(
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """
    🎯 DRIVER OPTIMIZATION DASHBOARD
    Shows real-time opportunities for time & profit optimization
    """
    
    # Get driver's current location
    if not current_driver.current_lat or not current_driver.current_lng:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enable location services"
        )
    
    # Find nearby forming groups (within 2km)
    nearby_groups = _find_nearby_opportunities(
        db=db,
        driver_lat=current_driver.current_lat,
        driver_lng=current_driver.current_lng,
        radius_km=2.0
    )
    
    # Analyze route optimization opportunities
    route_analysis = _analyze_route_opportunities(db, current_driver)
    
    # Get pending bookings map (for strategic positioning)
    pending_bookings_heatmap = _get_pending_bookings_heatmap(db)
    
    # AI Suggestion: "What should I do NOW?"
    ai_suggestion = _generate_optimization_suggestion(
        nearby_groups=nearby_groups,
        route_analysis=route_analysis,
        driver=current_driver
    )
    
    return DriverDashboardResponse(
        driver_status={
            "is_online": current_driver.is_online,
            "is_available": current_driver.is_available,
            "total_trips_today": current_driver.total_trips_completed,
            "avg_rating": current_driver.avg_rating
        },
        nearby_opportunities=nearby_groups,
        route_optimization=route_analysis,
        pending_bookings_heatmap=pending_bookings_heatmap,
        ai_suggestion=ai_suggestion
    )


@router.get("/opportunities/routes", response_model=List[RouteOpportunity])
async def get_route_opportunities(
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """
    📊 ROUTE COMPARISON VIEW
    Example: "Route A: 3 short-route passengers (6 mins, ₹90) 
             vs Route B: 2 full-route passengers (12 mins, ₹120)"
    """
    
    active_routes = db.query(Route).filter(Route.is_active == True).all()
    
    opportunities = []
    
    for route in active_routes:
        # Count pending bookings per route
        pending_bookings = db.query(BookingRequest).filter(
            BookingRequest.route_id == route.id,
            BookingRequest.request_status == "SEARCHING"
        ).all()
        
        # Separate short vs full route passengers (based on user's destination)
        short_route_count = sum(1 for b in pending_bookings if _is_short_route_booking(b, route))
        full_route_count = len(pending_bookings) - short_route_count
        
        # Calculate profit potential
        profit_analysis = route.calculate_profit_potential(
            short_passengers=short_route_count,
            full_passengers=full_route_count
        )
        
        # Find forming groups on this route
        forming_groups_count = db.query(RideGroup).filter(
            RideGroup.route_id == route.id,
            RideGroup.group_status == GroupStatus.FORMING
        ).count()
        
        opportunities.append(
            RouteOpportunity(
                route_id=route.id,
                route_name=f"{route.origin_name} → {route.destination_name}",
                pending_bookings_total=len(pending_bookings),
                short_route_passengers=short_route_count,
                full_route_passengers=full_route_count,
                forming_groups_count=forming_groups_count,
                profit_analysis=profit_analysis,
                recommendation=_generate_route_recommendation(profit_analysis)
            )
        )
    
    # Sort by potential revenue
    opportunities.sort(
        key=lambda x: x.profit_analysis['full_route']['revenue'],
        reverse=True
    )
    
    return opportunities


@router.post("/accept-group/{group_id}")
async def accept_group_assignment(
    group_id: int,
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """
    Driver accepts a ready group
    """
    
    # Find the group
    group = db.query(RideGroup).filter(
        RideGroup.id == group_id,
        RideGroup.group_status == GroupStatus.READY
    ).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or already assigned"
        )
    
    # Check if driver is available
    if not current_driver.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are currently on another trip"
        )
    
    # Assign driver to group
    group.assigned_driver_id = current_driver.id
    group.group_status = GroupStatus.DISPATCHED
    current_driver.is_available = False
    
    # Create ride record
    from app.models.driver import Ride
    ride = Ride(
        group_id=group.id,
        driver_id=current_driver.id,
        route_id=group.route_id,
        passenger_count=group.current_size,
        ride_status="ASSIGNED"
    )
    
    db.add(ride)
    db.commit()
    db.refresh(ride)
    
    # Notify passengers (WebSocket)
    from app.websocket.manager import notify_group_driver_assigned
    await notify_group_driver_assigned(
        group_id=group.id,
        driver_name=current_driver.full_name,
        vehicle_number=current_driver.vehicle_number,
        driver_location={
            "lat": current_driver.current_lat,
            "lng": current_driver.current_lng
        }
    )
    
    return {
        "success": True,
        "ride_id": ride.id,
        "group_qr_code": group.qr_code,
        "passenger_count": group.current_size,
        "route": {
            "origin": group.route.origin_name,
            "destination": group.route.destination_name,
            "estimated_duration": group.route.estimated_duration_mins
        }
    }


# ===== HELPER FUNCTIONS =====

def _find_nearby_opportunities(
    db: Session,
    driver_lat: float,
    driver_lng: float,
    radius_km: float
) -> List[Dict]:
    """Find groups ready for dispatch within radius"""
    from app.utils.geo import calculate_distance
    
    ready_groups = db.query(RideGroup).filter(
        RideGroup.group_status == GroupStatus.READY,
        RideGroup.assigned_driver_id == None
    ).all()
    
    nearby = []
    
    for group in ready_groups:
        distance_km = calculate_distance(
            driver_lat, driver_lng,
            group.route.origin_lat, group.route.origin_lng
        ) / 1000  # Convert meters to km
        
        if distance_km <= radius_km:
            nearby.append({
                "group_id": group.id,
                "passenger_count": group.current_size,
                "route_name": f"{group.route.origin_name} → {group.route.destination_name}",
                "distance_km": round(distance_km, 2),
                "wait_time_mins": round(group.get_wait_time_seconds() / 60, 1),
                "qr_code": group.qr_code
            })
    
    # Sort by distance
    nearby.sort(key=lambda x: x['distance_km'])
    return nearby


def _analyze_route_opportunities(db: Session, driver: Driver) -> Dict:
    """Analyze which routes have better time/profit optimization"""
    
    # Get all active routes
    routes = db.query(Route).filter(Route.is_active == True).all()
    
    analysis = {}
    
    for route in routes:
        pending = db.query(BookingRequest).filter(
            BookingRequest.route_id == route.id,
            BookingRequest.request_status == "SEARCHING"
        ).count()
        
        analysis[route.route_code] = {
            "route_name": f"{route.origin_name} → {route.destination_name}",
            "pending_passengers": pending,
            "avg_wait_time_mins": round(route.avg_wait_time_seconds / 60, 1),
            "demand_level": "HIGH" if pending >= 4 else "MEDIUM" if pending >= 2 else "LOW"
        }
    
    return analysis


def _get_pending_bookings_heatmap(db: Session) -> List[Dict]:
    """Get locations of pending bookings for map visualization"""
    
    recent_threshold = datetime.utcnow() - timedelta(minutes=5)
    
    pending = db.query(BookingRequest).filter(
        BookingRequest.request_status == "SEARCHING",
        BookingRequest.requested_at >= recent_threshold
    ).all()
    
    return [
        {
            "lat": float(b.request_lat),
            "lng": float(b.request_lng),
            "route_id": b.route_id,
            "wait_time_mins": round((datetime.utcnow() - b.requested_at).total_seconds() / 60, 1)
        }
        for b in pending
    ]


def _generate_optimization_suggestion(
    nearby_groups: List[Dict],
    route_analysis: Dict,
    driver: Driver
) -> OptimizationSuggestion:
    """AI generates actionable suggestion for driver"""
    
    if not nearby_groups:
        # No immediate opportunities
        best_route = max(
            route_analysis.items(),
            key=lambda x: x[1]['pending_passengers']
        )
        
        return OptimizationSuggestion(
            action="MOVE_TO_HOTSPOT",
            priority="MEDIUM",
            message=f"Move to {best_route[1]['route_name']} - {best_route[1]['pending_passengers']} passengers waiting",
            estimated_earning_potential=0.0,
            reasoning="Proactive positioning for upcoming demand"
        )
    
    # There are nearby groups ready
    closest_group = nearby_groups[0]
    
    return OptimizationSuggestion(
        action="ACCEPT_GROUP",
        priority="HIGH",
        message=f"Accept Group {closest_group['group_id']} - {closest_group['passenger_count']} passengers, {closest_group['distance_km']}km away",
        estimated_earning_potential=50.0 * closest_group['passenger_count'],  # Example
        reasoning=f"Closest opportunity with {closest_group['passenger_count']} confirmed passengers"
    )


def _is_short_route_booking(booking: BookingRequest, route: Route) -> bool:
    """
    Determine if booking is for short route (halfway) or full route
    This would be based on user's selected destination in real app
    For now, placeholder logic
    """
    # TODO: Add destination tracking to BookingRequest model
    return False  # Placeholder


def _generate_route_recommendation(profit_analysis: Dict) -> str:
    """Generate human-readable recommendation"""
    
    short = profit_analysis['short_route']
    full = profit_analysis['full_route']
    
    if short['trips_per_hour'] > full['trips_per_hour'] and short['passengers'] >= 3:
        return f"✅ TAKE SHORT ROUTES - {short['trips_per_hour']:.1f} trips/hour possible"
    elif full['passengers'] >= 3:
        return f"✅ TAKE FULL ROUTE - Higher revenue (₹{full['revenue']})"
    else:
        return "⏳ Wait for more bookings"