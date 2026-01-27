"""
RickQueue Backend - FastAPI Application
Focus: Operational Excellence & Smart Dispatch (NO Payment Processing)
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config.settings import settings
from app.database.session import engine, Base
from app.ai.scheduler import start_smart_dispatch_scheduler, stop_smart_dispatch_scheduler

# Import routers
from app.api import auth, queue, driver, routes_api

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    # STARTUP
    logger.info("🚀 Starting RickQueue Backend...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
    
    # Start AI Dispatch Scheduler (runs every 30 seconds)
    start_smart_dispatch_scheduler()
    logger.info("🤖 AI Dispatch Scheduler started")
    
    yield
    
    # SHUTDOWN
    logger.info("🛑 Shutting down RickQueue Backend...")
    stop_smart_dispatch_scheduler()
    logger.info("✅ AI Scheduler stopped")


# Initialize FastAPI app
app = FastAPI(
    title="RickQueue API",
    description="Smart Queue Management for Shared E-Rickshaws",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== HEALTH CHECK =====
@app.get("/")
async def root():
    return {
        "app": "RickQueue API",
        "status": "running",
        "version": "1.0.0",
        "ai_engine": "active"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    from app.database.session import get_db
    
    try:
        # Test database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return {
        "status": "ok",
        "database": db_status,
        "ai_scheduler": "running"  # Could add actual scheduler status check
    }


# ===== INCLUDE ROUTERS =====

# Authentication
app.include_router(auth.router, prefix="/api/v1")

# Queue Management (User-facing)
app.include_router(queue.router, prefix="/api/v1")

# Driver Dashboard & Operations
app.include_router(driver.router, prefix="/api/v1")

# Routes Management
app.include_router(routes_api.router, prefix="/api/v1")


# ===== ERROR HANDLERS =====

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom validation error handler
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# ===== WEBSOCKET SETUP =====

import socketio

# Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ORIGINS
)

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, app)


# WebSocket Events
@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def join_group_room(sid, data):
    """
    User/Driver joins a group room for real-time updates
    """
    group_id = data.get('group_id')
    if group_id:
        await sio.enter_room(sid, f"group_{group_id}")
        logger.info(f"Client {sid} joined group room: group_{group_id}")


@sio.event
async def driver_location_update(sid, data):
    """
    Driver sends live location updates
    """
    driver_id = data.get('driver_id')
    lat = data.get('lat')
    lng = data.get('lng')
    
    # Update database
    from app.database.session import get_db
    from app.models.driver import Driver
    from datetime import datetime
    
    db = next(get_db())
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    
    if driver:
        driver.current_lat = lat
        driver.current_lng = lng
        driver.last_location_update = datetime.utcnow()
        db.commit()
        
        # Broadcast to passengers in assigned group
        if driver.assigned_groups:
            for group in driver.assigned_groups:
                await sio.emit(
                    'driver_location',
                    {'lat': lat, 'lng': lng},
                    room=f"group_{group.id}"
                )


# ===== ADMIN ENDPOINTS (for testing) =====

@app.post("/admin/seed-routes")
async def seed_sample_routes():
    """
    Seed database with sample routes (for development)
    """
    from app.database.session import get_db
    from app.models.driver import Route
    
    db = next(get_db())
    
    sample_routes = [
        Route(
            route_code="METRO_COLLEGE_A",
            origin_name="Metro Station Gate 1",
            destination_name="City College",
            origin_lat=28.6139,
            origin_lng=77.2090,
            dest_lat=28.6289,
            dest_lng=77.2265,
            distance_km=5.2,
            estimated_duration_mins=15,
            halfway_point_km=2.6,
            short_route_fare=30.0,
            full_route_fare=50.0
        ),
        Route(
            route_code="MARKET_HOSPITAL_B",
            origin_name="Central Market",
            destination_name="City Hospital",
            origin_lat=28.6200,
            origin_lng=77.2100,
            dest_lat=28.6350,
            dest_lng=77.2250,
            distance_km=4.0,
            estimated_duration_mins=12,
            halfway_point_km=2.0,
            short_route_fare=25.0,
            full_route_fare=40.0
        )
    ]
    
    for route in sample_routes:
        existing = db.query(Route).filter(Route.route_code == route.route_code).first()
        if not existing:
            db.add(route)
    
    db.commit()
    
    return {"message": "Sample routes seeded successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:socket_app",  # Use socket_app instead of app
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )