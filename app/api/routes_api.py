"""
Routes API Endpoints
Manage rickshaw routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db
from app.models.driver import Route

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get("/")
async def get_all_routes(db: Session = Depends(get_db)):
    """
    Get all active routes
    """
    routes = db.query(Route).filter(Route.is_active == True).all()
    
    return [
        {
            "id": r.id,
            "route_code": r.route_code,
            "origin_name": r.origin_name,
            "destination_name": r.destination_name,
            "distance_km": float(r.distance_km),
            "estimated_duration_mins": r.estimated_duration_mins,
            "short_route_fare": float(r.short_route_fare),
            "full_route_fare": float(r.full_route_fare),
            "origin": {
                "lat": float(r.origin_lat),
                "lng": float(r.origin_lng)
            },
            "destination": {
                "lat": float(r.dest_lat),
                "lng": float(r.dest_lng)
            }
        }
        for r in routes
    ]


@router.get("/{route_id}")
async def get_route(route_id: int, db: Session = Depends(get_db)):
    """
    Get specific route details
    """
    route = db.query(Route).filter(Route.id == route_id).first()
    
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return {
        "id": route.id,
        "route_code": route.route_code,
        "origin_name": route.origin_name,
        "destination_name": route.destination_name,
        "distance_km": float(route.distance_km),
        "estimated_duration_mins": route.estimated_duration_mins,
        "short_route_fare": float(route.short_route_fare),
        "full_route_fare": float(route.full_route_fare),
        "halfway_point_km": float(route.halfway_point_km),
        "is_active": route.is_active,
        "origin": {
            "lat": float(route.origin_lat),
            "lng": float(route.origin_lng)
        },
        "destination": {
            "lat": float(route.dest_lat),
            "lng": float(route.dest_lng)
        }
    }


@router.get("/test")
async def routes_test():
    """
    Test endpoint
    """
    return {
        "message": "Routes API is working",
        "status": "ok"
    }