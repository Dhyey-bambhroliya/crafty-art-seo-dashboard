from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import Alert, AlertSetting, User, UserRole, Category
from backend.app.schemas.schemas import (
    AlertOut, AlertStatusUpdate, AlertSettingOut, AlertSettingUpdate
)
from backend.app.api.deps import (
    require_team_leader_or_manager, require_manager
)
from backend.app.services.alert_service import get_or_create_alert_settings

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertOut])
def list_alerts(
    severity: Optional[str] = Query(None, description="WARNING | CRITICAL"),
    status_filter: Optional[str] = Query(None, description="PENDING | REVIEWED | DISMISSED"),
    category_id: Optional[int] = Query(None, description="Filter by Category"),
    leader_id: Optional[int] = Query(None, description="Filter by Team Leader"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    List SEO alerts with filtering by severity, review status, category, or team leader.
    """
    query = (
        db.query(Alert, Category, User)
        .outerjoin(Category, Alert.category_id == Category.id)
        .outerjoin(User, Alert.assigned_leader_id == User.id)
    )

    if severity:
        query = query.filter(Alert.severity == severity.upper())

    if status_filter:
        query = query.filter(Alert.status == status_filter.upper())

    if category_id:
        query = query.filter(Alert.category_id == category_id)

    if leader_id:
        query = query.filter(Alert.assigned_leader_id == leader_id)

    # If team leader, they can see alerts for their categories, but we also allow viewing all alerts
    # Team leaders specifically focus on their own categories
    alerts = query.order_by(Alert.detection_date.desc(), Alert.id.desc()).limit(limit).all()

    results = []
    for item in alerts:
        a = item.Alert
        cat = item.Category
        leader = item.User
        results.append(AlertOut(
            id=a.id,
            page_url=a.page_url,
            normalized_url=a.normalized_url,
            category_id=a.category_id,
            category_name=cat.name if cat else "Uncategorized",
            assigned_leader_id=a.assigned_leader_id,
            leader_name=leader.full_name if leader else "Unassigned",
            alert_type=a.alert_type,
            severity=a.severity,
            current_value=a.current_value,
            previous_value=a.previous_value,
            pct_change=a.pct_change,
            detection_date=a.detection_date,
            period_start=a.period_start,
            period_end=a.period_end,
            status=a.status,
            created_at=a.created_at,
            reviewed_at=a.reviewed_at
        ))
    return results

@router.put("/{alert_id}/status", response_model=AlertOut)
def update_alert_status(
    alert_id: int,
    status_update: AlertStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Mark alert as REVIEWED or DISMISSED.
    - Managers can update any alert.
    - Team leaders can update alerts for categories assigned to them.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    if current_user.role != UserRole.MANAGER and alert.assigned_leader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You can only review alerts for categories assigned to you."
        )

    alert.status = status_update.status
    alert.reviewed_by_user_id = current_user.id
    alert.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)

    cat = db.query(Category).filter(Category.id == alert.category_id).first() if alert.category_id else None
    leader = db.query(User).filter(User.id == alert.assigned_leader_id).first() if alert.assigned_leader_id else None

    return AlertOut(
        id=alert.id,
        page_url=alert.page_url,
        normalized_url=alert.normalized_url,
        category_id=alert.category_id,
        category_name=cat.name if cat else "Uncategorized",
        assigned_leader_id=alert.assigned_leader_id,
        leader_name=leader.full_name if leader else "Unassigned",
        alert_type=alert.alert_type,
        severity=alert.severity,
        current_value=alert.current_value,
        previous_value=alert.previous_value,
        pct_change=alert.pct_change,
        detection_date=alert.detection_date,
        period_start=alert.period_start,
        period_end=alert.period_end,
        status=alert.status,
        created_at=alert.created_at,
        reviewed_at=alert.reviewed_at
    )

@router.get("/settings", response_model=AlertSettingOut)
def get_alert_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Get current alert thresholds and noise reduction parameters."""
    return get_or_create_alert_settings(db)

@router.put("/settings", response_model=AlertSettingOut)
def update_alert_settings(
    settings_in: AlertSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Configure alert thresholds and sensitivity."""
    setting = get_or_create_alert_settings(db)

    if settings_in.click_warning_pct is not None:
        setting.click_warning_pct = settings_in.click_warning_pct
    if settings_in.click_critical_pct is not None:
        setting.click_critical_pct = settings_in.click_critical_pct
    if settings_in.impression_warning_pct is not None:
        setting.impression_warning_pct = settings_in.impression_warning_pct
    if settings_in.position_drop_warning is not None:
        setting.position_drop_warning = settings_in.position_drop_warning
    if settings_in.min_previous_clicks is not None:
        setting.min_previous_clicks = settings_in.min_previous_clicks
    if settings_in.min_previous_impressions is not None:
        setting.min_previous_impressions = settings_in.min_previous_impressions

    db.commit()
    db.refresh(setting)
    return setting
