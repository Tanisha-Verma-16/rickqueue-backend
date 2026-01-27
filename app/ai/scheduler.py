"""
Background Scheduler for Smart Dispatch AI
Runs every 30 seconds to analyze forming groups
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.database.session import get_db
from app.ai.smart_dispatch import SmartDispatchService

logger = logging.getLogger(__name__)

scheduler = None


def run_dispatch_analysis_job():
    """
    Job that runs every 30 seconds
    Analyzes all forming groups and makes dispatch decisions
    """
    try:
        db = next(get_db())
        dispatch_service = SmartDispatchService(db)
        
        stats = dispatch_service.run_dispatch_analysis()
        
        logger.info(f"✅ Dispatch analysis completed: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Error in dispatch analysis job: {e}", exc_info=True)
    finally:
        db.close()


def start_smart_dispatch_scheduler():
    """
    Start the background scheduler
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    scheduler = BackgroundScheduler()
    
    # Add job: run every 30 seconds
    scheduler.add_job(
        func=run_dispatch_analysis_job,
        trigger=IntervalTrigger(seconds=30),
        id='smart_dispatch_job',
        name='Smart Dispatch Analysis',
        replace_existing=True,
        max_instances=1  # Ensure only one instance runs at a time
    )
    
    scheduler.start()
    logger.info("🤖 Smart Dispatch Scheduler started (runs every 30 seconds)")


def stop_smart_dispatch_scheduler():
    """
    Stop the scheduler gracefully
    """
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("🛑 Smart Dispatch Scheduler stopped")