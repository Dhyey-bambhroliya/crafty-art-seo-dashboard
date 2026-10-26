from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.models import GSCProperty, SyncRun, User, UserRole
from backend.app.schemas.schemas import (
    GSCPropertyOut, GSCAuthUrlOut, SyncRunOut, GSCConfigStatusResponse, GSCConfigUpdateRequest
)
from backend.app.api.deps import require_manager, require_team_leader_or_manager
from backend.app.services.gsc_service import GSCService
from backend.app.services.sync_service import execute_synchronization
from backend.app.services.demo_data_service import seed_demo_dataset, purge_demo_dataset
from backend.app.models.models import DailyPageMetrics, GSCProperty, SyncRun, User, UserRole
from backend.app.services.metric_service import get_latest_data_date

from backend.app.services.settings_service import get_system_setting, set_system_setting

router = APIRouter(prefix="/gsc", tags=["Google Search Console"])

@router.get("/config-status", response_model=GSCConfigStatusResponse)
def get_gsc_config_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Check if Google OAuth Client ID and Secret are configured in database or environment."""
    client_id = get_system_setting(db, "GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
    client_secret = get_system_setting(db, "GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)
    redirect_uri = get_system_setting(db, "GOOGLE_REDIRECT_URI", settings.GOOGLE_REDIRECT_URI)

    has_id = bool(client_id and len(client_id.strip()) > 5)
    has_secret = bool(client_secret and len(client_secret.strip()) > 5)
    return GSCConfigStatusResponse(
        is_configured=has_id and has_secret,
        client_id_configured=has_id,
        client_secret_configured=has_secret,
        client_id=client_id if has_id else None,
        redirect_uri=redirect_uri
    )

@router.post("/config", response_model=GSCConfigStatusResponse)
def update_gsc_config(
    payload: GSCConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Save or update Google OAuth Client ID and Secret securely into PostgreSQL database."""
    clean_id = payload.client_id.strip()
    clean_secret = payload.client_secret.strip()
    clean_redirect = payload.redirect_uri.strip() if payload.redirect_uri else settings.GOOGLE_REDIRECT_URI

    # 1. Persist to database (permanent across Render restarts and deploys)
    set_system_setting(db, "GOOGLE_CLIENT_ID", clean_id)
    set_system_setting(db, "GOOGLE_CLIENT_SECRET", clean_secret)
    set_system_setting(db, "GOOGLE_REDIRECT_URI", clean_redirect)

    # 2. Update active in-memory settings
    settings.GOOGLE_CLIENT_ID = clean_id
    settings.GOOGLE_CLIENT_SECRET = clean_secret
    settings.GOOGLE_REDIRECT_URI = clean_redirect

    # 3. Best-effort persistence to local .env (for local development convenience)
    try:
        env_path = ".env"
        lines = []
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            pass

        updated = {
            "GOOGLE_CLIENT_ID": f'GOOGLE_CLIENT_ID="{clean_id}"\n',
            "GOOGLE_CLIENT_SECRET": f'GOOGLE_CLIENT_SECRET="{clean_secret}"\n',
            "GOOGLE_REDIRECT_URI": f'GOOGLE_REDIRECT_URI="{clean_redirect}"\n'
        }

        new_lines = []
        for line in lines:
            k = line.split("=")[0].strip()
            if k in updated:
                new_lines.append(updated.pop(k))
            else:
                new_lines.append(line)
        for k, val in updated.items():
            new_lines.append(val)

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception:
        pass

    return GSCConfigStatusResponse(
        is_configured=True,
        client_id_configured=True,
        client_secret_configured=True,
        client_id=clean_id,
        redirect_uri=clean_redirect
    )

class OAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None

class PropertySelectRequest(BaseModel):
    site_url: str

@router.get("/auth-url", response_model=GSCAuthUrlOut)
def get_gsc_auth_url(
    redirect_uri: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Generate Google OAuth 2.0 authorization URL for GSC."""
    client_id = get_system_setting(db, "GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
    client_secret = get_system_setting(db, "GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)
    configured_redirect = get_system_setting(db, "GOOGLE_REDIRECT_URI", settings.GOOGLE_REDIRECT_URI)

    target_redirect = redirect_uri or configured_redirect
    url, err = GSCService.generate_authorization_url(
        redirect_uri=target_redirect,
        client_id=client_id,
        client_secret=client_secret
    )
    if err or not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Could not generate authorization URL. Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are configured."
        )
    return GSCAuthUrlOut(auth_url=url)

@router.post("/oauth-callback")
def handle_oauth_callback(
    payload: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Complete OAuth code exchange on the server and discover properties."""
    client_id = get_system_setting(db, "GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
    client_secret = get_system_setting(db, "GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)
    configured_redirect = get_system_setting(db, "GOOGLE_REDIRECT_URI", settings.GOOGLE_REDIRECT_URI)

    target_redirect = payload.redirect_uri or configured_redirect
    token_data, err = GSCService.exchange_code(
        code=payload.code,
        redirect_uri=target_redirect,
        client_id=client_id,
        client_secret=client_secret
    )
    if err or not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err or "Failed token exchange.")

    # Validate and fetch verified properties from GSC
    creds = GSCService.get_valid_credentials(
        refresh_token=token_data["refresh_token"],
        access_token=token_data["access_token"],
        client_id=token_data.get("client_id") or client_id,
        client_secret=token_data.get("client_secret") or client_secret
    )
    if not creds:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to initialize credentials.")

    try:
        discovered_sites = GSCService.list_properties(creds)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google API Error: {str(e)}")

    if not discovered_sites:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Search Console properties were found for this Google account. Ensure the account has verified site access."
        )

    # Save properties in database
    created_properties = []
    for s in discovered_sites:
        site_url = s["site_url"]
        prop = db.query(GSCProperty).filter(GSCProperty.site_url == site_url).first()
        if not prop:
            prop = GSCProperty(
                site_url=site_url,
                permission_level=s["permission_level"],
                is_active=True,
                is_demo=False,
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                refresh_token=token_data["refresh_token"],
                access_token=token_data["access_token"],
                token_expiry=token_data["token_expiry"],
                connected_by_user_id=current_user.id
            )
            db.add(prop)
        else:
            prop.refresh_token = token_data["refresh_token"]
            prop.access_token = token_data["access_token"]
            prop.token_expiry = token_data["token_expiry"]
            prop.permission_level = s["permission_level"]
            prop.is_active = True
        created_properties.append(site_url)

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully connected Google Search Console. Found {len(discovered_sites)} property/properties.",
        "properties": discovered_sites
    }

@router.get("/properties", response_model=List[GSCPropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """List configured Search Console properties and their connection status."""
    props = db.query(GSCProperty).order_by(GSCProperty.is_active.desc(), GSCProperty.id.desc()).all()
    results = []
    for p in props:
        latest = get_latest_data_date(db, property_id=p.id)
        results.append(GSCPropertyOut(
            id=p.id,
            site_url=p.site_url,
            permission_level=p.permission_level,
            is_active=p.is_active,
            is_demo=p.is_demo,
            is_connected=bool(p.refresh_token or p.is_demo),
            latest_data_date=str(latest) if latest else None,
            created_at=p.created_at
        ))
    return results

class PropertyManualCreate(BaseModel):
    site_url: str
    permission_level: Optional[str] = "siteOwner"

@router.post("/properties/manual", response_model=GSCPropertyOut)
def add_property_manually(
    payload: PropertyManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Directly connect a real Search Console property URL."""
    clean_url = payload.site_url.strip()
    if not clean_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site URL is required.")
        
    prop = db.query(GSCProperty).filter(GSCProperty.site_url == clean_url).first()
    if not prop:
        prop = GSCProperty(
            site_url=clean_url,
            permission_level=payload.permission_level or "siteOwner",
            is_active=True,
            is_demo=False,
            connected_by_user_id=current_user.id
        )
        db.add(prop)
    else:
        prop.is_active = True
        prop.is_demo = False
        
    db.commit()
    db.refresh(prop)
    
    latest = get_latest_data_date(db, property_id=prop.id)
    return GSCPropertyOut(
        id=prop.id,
        site_url=prop.site_url,
        permission_level=prop.permission_level,
        is_active=prop.is_active,
        is_demo=prop.is_demo,
        is_connected=True,
        latest_data_date=str(latest) if latest else None,
        created_at=prop.created_at
    )

def _run_sync_task(property_id: int, triggered_by: str):
    from backend.app.core.database import SessionLocal
    with SessionLocal() as db:
        try:
            execute_synchronization(
                db=db,
                property_id=property_id,
                triggered_by=triggered_by
            )
        except Exception as e:
            import logging
            logging.getLogger("crafty_art_sync").error(f"Background sync error for property {property_id}: {e}")

@router.post("/properties/{property_id}/sync")
def trigger_property_sync(
    property_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Trigger immediate background synchronization."""
    prop = db.query(GSCProperty).filter(GSCProperty.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found.")

    background_tasks.add_task(
        _run_sync_task,
        property_id=prop.id,
        triggered_by=f"USER:{current_user.id}:{current_user.full_name}"
    )

    return {
        "status": "RUNNING",
        "message": f"Synchronization for '{prop.site_url}' started in background.",
        "property_id": prop.id
    }

@router.get("/sync-runs", response_model=List[SyncRunOut])
def list_sync_history(
    property_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """View synchronization logs and data freshness status."""
    query = db.query(SyncRun, GSCProperty).outerjoin(GSCProperty, SyncRun.property_id == GSCProperty.id)
    if property_id:
        query = query.filter(SyncRun.property_id == property_id)
    runs = query.order_by(SyncRun.id.desc()).limit(limit).all()

    return [
        SyncRunOut(
            id=r.SyncRun.id,
            property_id=r.SyncRun.property_id,
            property_site_url=r.GSCProperty.site_url if r.GSCProperty else "None",
            triggered_by=r.SyncRun.triggered_by,
            start_time=r.SyncRun.start_time,
            end_time=r.SyncRun.end_time,
            status=r.SyncRun.status,
            pages_synced=r.SyncRun.pages_synced,
            records_created=r.SyncRun.records_created,
            alerts_generated=r.SyncRun.alerts_generated,
            latest_data_date=r.SyncRun.latest_data_date,
            error_message=r.SyncRun.error_message
        )
        for r in runs
    ]

@router.post("/seed-demo")
def seed_demo_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Manager only: Generates realistic Crafty Art SEO demonstration data
    (56 days of daily metrics, 4 categories, 2 team leaders, alerts).
    Clearly marked with is_synthetic=True and [DEMO DATA].
    """
    try:
        res = seed_demo_dataset(db, manager_user_id=current_user.id)
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Demo seed failed: {str(e)}")

@router.post("/purge-demo")
def purge_demo_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Manager only: Remove synthetic Crafty Art demonstration data.
    Purges demo properties, synthetic metrics, demo categories, demo alerts, and demo team leaders.
    """
    try:
        res = purge_demo_dataset(db, purge_all=False, keep_manager_id=current_user.id)
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Purge demo failed: {str(e)}")

@router.post("/reset-workspace")
def reset_workspace_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Manager only: Full workspace clean reset.
    Wipes all categories, pages, metrics, properties, sync logs, and team leaders,
    leaving only the current Manager account active and 100% clean for real production data.
    """
    try:
        res = purge_demo_dataset(db, purge_all=True, keep_manager_id=current_user.id)
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Reset failed: {str(e)}")

@router.delete("/properties/{property_id}")
def delete_gsc_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Disconnect and delete a Search Console property and all its associated metrics."""
    prop = db.query(GSCProperty).filter(GSCProperty.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found.")

    site_url = prop.site_url
    # Delete daily metrics
    db.query(DailyPageMetrics).filter(DailyPageMetrics.property_id == property_id).delete()
    # Delete sync runs
    db.query(SyncRun).filter(SyncRun.property_id == property_id).delete()
    # Delete property
    db.delete(prop)
    db.commit()

    return {"message": f"Search Console property '{site_url}' and its metrics deleted successfully."}

@router.api_route("/cron-sync", methods=["GET", "POST"])
def trigger_automated_cron_sync(
    background_tasks: BackgroundTasks,
    force: bool = Query(False)
):
    """
    Automated webhook / cron endpoint for daily synchronization.
    Callable by external free cron schedulers (e.g. GitHub Actions, cron-job.org, UptimeRobot)
    or internal systems to keep Google Search Console data fresh every day without manual clicks.
    """
    from backend.app.core.scheduler import check_and_run_due_syncs
    background_tasks.add_task(check_and_run_due_syncs, force=force)
    return {
        "status": "triggered",
        "message": "Automated synchronization job started in the background."
    }

