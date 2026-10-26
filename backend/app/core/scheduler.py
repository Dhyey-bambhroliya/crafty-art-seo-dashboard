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

def check_and_run_due_syncs(force: bool = False):
    """
    Checks if active properties need daily synchronization.
    If the last successful sync was more than 20 hours ago (or force=True),
    automatically executes the sync without requiring user manual action.
    """
    logger.info("Checking for overdue Google Search Console synchronizations...")
    db = SessionLocal()
    results = []
    try:
        active_props = db.query(GSCProperty).filter(GSCProperty.is_active == True).all()
        for prop in active_props:
            latest_run = db.query(SyncRun).filter(
                SyncRun.property_id == prop.id,
                SyncRun.status == "SUCCESS"
            ).order_by(SyncRun.end_time.desc()).first()

            needs_sync = force
            if not latest_run or not latest_run.end_time:
                needs_sync = True
            else:
                end_t = latest_run.end_time
                if end_t.tzinfo is None:
                    end_t = end_t.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - end_t > timedelta(hours=20):
                    needs_sync = True

            if needs_sync:
                # Avoid overlapping sync
                recent_running = db.query(SyncRun).filter(
                    SyncRun.property_id == prop.id,
                    SyncRun.status == "RUNNING",
                    SyncRun.start_time >= datetime.now(timezone.utc) - timedelta(minutes=20)
                ).first()
                if recent_running:
                    logger.info(f"Sync already running for '{prop.site_url}'. Skipping.")
                    continue

                try:
                    res = execute_synchronization(
                        db=db,
                        property_id=prop.id,
                        triggered_by="AUTO_DAILY_DUE_SYNC"
                    )
                    results.append({"site_url": prop.site_url, "status": "SUCCESS", "pages": res.get("pages_synced", 0)})
                    logger.info(f"Auto-sync completed for {prop.site_url}")
                except Exception as e:
                    results.append({"site_url": prop.site_url, "status": "FAILED", "error": str(e)})
                    logger.error(f"Auto-sync failed for {prop.site_url}: {str(e)}")
    finally:
        db.close()
    return results

def start_scheduler():
    """Initializes and starts the background daily sync scheduler if enabled."""
    if not settings.ENABLE_SCHEDULER:
        logger.info("Background scheduler is disabled via ENABLE_SCHEDULER setting.")
        return

    cleanup_stale_sync_runs()

    if not scheduler.running:
        # 1. Scheduled daily cron at configured hour (e.g. 03:00 UTC)
        trigger = CronTrigger(hour=settings.DAILY_SYNC_HOUR, minute=0)
        scheduler.add_job(
            daily_scheduled_sync_job,
            trigger=trigger,
            id="daily_gsc_sync",
            name="Daily Google Search Console Sync",
            replace_existing=True
        )

        # 2. Periodic overdue check every 60 minutes while instance is active
        scheduler.add_job(
            check_and_run_due_syncs,
            trigger="interval",
            minutes=60,
            id="periodic_due_check",
            name="Periodic Overdue Sync Check",
            replace_existing=True
        )

        scheduler.start()
        logger.info(f"Scheduler started: Daily GSC sync scheduled at {settings.DAILY_SYNC_HOUR:02d}:00 UTC and interval overdue check active.")

def shutdown_scheduler():
    """Graceful shutdown of scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
