import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.models import GSCProperty
from backend.app.services.sync_service import execute_synchronization

logger = logging.getLogger("seo_scheduler")
scheduler = BackgroundScheduler()

def daily_scheduled_sync_job():
    """Daily automated synchronization for all active GSC properties."""
    logger.info("Executing scheduled daily SEO synchronization job...")
    db = SessionLocal()
    try:
        active_props = db.query(GSCProperty).filter(GSCProperty.is_active == True).all()
        for prop in active_props:
            try:
                execute_synchronization(
                    db=db,
                    property_id=prop.id,
                    triggered_by="SCHEDULED_DAILY_CRON"
                )
                logger.info(f"Successfully synced property {prop.site_url}")
            except Exception as e:
                logger.error(f"Error syncing property {prop.site_url}: {str(e)}")
    finally:
        db.close()

def start_scheduler():
    """Initializes and starts the background daily sync scheduler."""
    if not scheduler.running:
        trigger = CronTrigger(hour=settings.DAILY_SYNC_HOUR, minute=0)
        scheduler.add_job(
            daily_scheduled_sync_job,
            trigger=trigger,
            id="daily_gsc_sync",
            name="Daily Google Search Console Sync",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Scheduler started: Daily GSC sync scheduled at {settings.DAILY_SYNC_HOUR:02d}:00.")

def shutdown_scheduler():
    """Graceful shutdown of scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
