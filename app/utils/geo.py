"""
Geographic utility functions
Distance calculations, proximity checks, etc.
"""

import math
from typing import Tuple


def calculate_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
) -> int:
    """
    Calculate distance between two coordinates using Haversine formula
    
    Args:
        lat1, lng1: First coordinate
        lat2, lng2: Second coordinate
        
    Returns:
        Distance in meters (int)
    """
    
    # Earth's radius in meters
    EARTH_RADIUS = 6371000
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) *
        math.sin(delta_lng / 2) ** 2
    )
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = EARTH_RADIUS * c
    
    return int(distance)


def is_within_radius(
    center_lat: float,
    center_lng: float,
    point_lat: float,
    point_lng: float,
    radius_meters: int
) -> bool:
    """
    Check if a point is within a certain radius of a center point
    
    Returns:
        True if within radius, False otherwise
    """
    
    distance = calculate_distance(center_lat, center_lng, point_lat, point_lng)
    return distance <= radius_meters


def get_bounding_box(
    center_lat: float,
    center_lng: float,
    radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box for efficient database queries
    
    Returns:
        (min_lat, max_lat, min_lng, max_lng)
    """
    
    # Approximate: 1 degree latitude = 111 km
    # 1 degree longitude varies by latitude
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * math.cos(math.radians(center_lat)))
    
    min_lat = center_lat - lat_delta
    max_lat = center_lat + lat_delta
    min_lng = center_lng - lng_delta
    max_lng = center_lng + lng_delta
    
    return (min_lat, max_lat, min_lng, max_lng)


def calculate_bearing(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
) -> float:
    """
    Calculate bearing (direction) from point 1 to point 2
    
    Returns:
        Bearing in degrees (0-360, where 0 is North)
    """
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lng = math.radians(lng2 - lng1)
    
    x = math.sin(delta_lng) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad) -
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lng)
    )
    
    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360
    bearing_deg = (bearing_deg + 360) % 360
    
    return bearing_deg


def estimate_travel_time(
    distance_meters: int,
    avg_speed_kmh: float = 25.0
) -> int:
    """
    Estimate travel time based on distance and average speed
    
    Args:
        distance_meters: Distance in meters
        avg_speed_kmh: Average speed in km/h (default 25 for e-rickshaw)
        
    Returns:
        Estimated time in seconds
    """
    
    distance_km = distance_meters / 1000
    time_hours = distance_km / avg_speed_kmh
    time_seconds = time_hours * 3600
    
    return int(time_seconds)


def get_compass_direction(bearing: float) -> str:
    """
    Convert bearing to compass direction
    
    Returns:
        Direction string like "North", "Northeast", etc.
    """
    
    directions = [
        "North", "Northeast", "East", "Southeast",
        "South", "Southwest", "West", "Northwest"
    ]
    
    index = int((bearing + 22.5) / 45) % 8
    
    return directions[index]