import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.models import GSCProperty, SyncRun
from backend.app.services.sync_service import execute_synchronization

logger = logging.getLogger("seo_scheduler")
scheduler = BackgroundScheduler()

def cleanup_stale_sync_runs():
    """Marks orphaned 'RUNNING' sync runs from server restarts as INTERRUPTED."""
    db = SessionLocal()
    try:
        stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        stale_runs = db.query(SyncRun).filter(
            SyncRun.status == "RUNNING",
            SyncRun.start_time < stale_cutoff
        ).all()
        for r in stale_runs:
            r.status = "INTERRUPTED"
            r.end_time = datetime.now(timezone.utc)
            r.error_message = "Server restarted or previous process was terminated while sync was running."
        if stale_runs:
            db.commit()
            logger.info(f"Cleaned up {len(stale_runs)} stale sync run(s) from previous server sessions.")
    except Exception as e:
        logger.warning(f"Could not clean up stale sync runs: {str(e)}")
        db.rollback()
    finally:
        db.close()

def daily_scheduled_sync_job():
    """Daily automated synchronization for all active GSC properties."""
    logger.info("Executing scheduled daily SEO synchronization job...")
    db = SessionLocal()
    try:
        active_props = db.query(GSCProperty).filter(GSCProperty.is_active == True).all()
        for prop in active_props:
            # Prevent duplicate overlapping sync if one is currently in progress
            recent_running = db.query(SyncRun).filter(
                SyncRun.property_id == prop.id,
                SyncRun.status == "RUNNING",
                SyncRun.start_time >= datetime.now(timezone.utc) - timedelta(minutes=20)
            ).first()
            if recent_running:
                logger.info(f"Sync already actively running for property '{prop.site_url}'. Skipping duplicate trigger.")
                continue

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
    """Initializes and starts the background daily sync scheduler if enabled."""
    if not settings.ENABLE_SCHEDULER:
        logger.info("Background scheduler is disabled via ENABLE_SCHEDULER setting.")
        return

    cleanup_stale_sync_runs()

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
        logger.info(f"Scheduler started: Daily GSC sync scheduled at {settings.DAILY_SYNC_HOUR:02d}:00 UTC.")

def shutdown_scheduler():
    """Graceful shutdown of scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
