from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import (
    Alert, AlertSetting, CategoryPage, Category, DailyPageMetrics
)
from backend.app.services.metric_service import (
    get_latest_data_date, get_28day_date_windows, get_page_aggregated_metrics, calculate_comparison_metrics
)

def get_or_create_alert_settings(db: Session) -> AlertSetting:
    """Retrieves existing alert settings or initializes defaults."""
    setting = db.query(AlertSetting).first()
    if not setting:
        setting = AlertSetting(
            click_warning_pct=10.0,
            click_critical_pct=20.0,
            impression_warning_pct=20.0,
            position_drop_warning=3.0,
            min_previous_clicks=5,
            min_previous_impressions=25
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting

def evaluate_page_alerts(
    db: Session,
    property_id: Optional[int] = None,
    evaluation_date: Optional[date] = None
) -> int:
    """
    Evaluates all mapped active pages against configurable thresholds.
    Generates alerts while strictly deduplicating active/pending alerts.
    Returns count of newly generated alerts                                     .
    """
    if not evaluation_date:
        evaluation_date = get_latest_data_date(db, property_id)
        if not evaluation_date:
            return 0
    
    settings = get_or_create_alert_settings(db)
    curr_start, curr_end, prev_start, prev_end = get_28day_date_windows(evaluation_date)
    
    # Query all active mapped category pages
    pages = (
        db.query(CategoryPage, Category)
        .join(Category, CategoryPage.category_id == Category.id)
        .filter(CategoryPage.status == "ACTIVE", Category.status == "ACTIVE")
        .all()
    )
    
    if not pages:
        return 0
    
    norm_urls = list({p.CategoryPage.normalized_url for p in pages})
    curr_metrics = get_page_aggregated_metrics(db, norm_urls, curr_start, curr_end)
    prev_metrics = get_page_aggregated_metrics(db, norm_urls, prev_start, prev_end)
    
    # Existing active alerts to prevent duplication
    existing_alerts = {
        (a.normalized_url, a.alert_type, a.detection_date)
        for a in db.query(Alert).filter(Alert.status == "PENDING").all()
    }
    
    alerts_created = 0
    
    for page_item in pages:
        page = page_item.CategoryPage
        category = page_item.Category
        norm_url = page.normalized_url
        
        curr = curr_metrics.get(norm_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})
        prev = prev_metrics.get(norm_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})
        
        comparison = calculate_comparison_metrics(
            curr["clicks"], curr["impressions"], curr["pos_imp_sum"],
            prev["clicks"], prev["impressions"], prev["pos_imp_sum"]
        )
        
        prev_clicks = comparison.previous.clicks
        prev_impressions = comparison.previous.impressions
        curr_clicks = comparison.current.clicks
        curr_impressions = comparison.current.impressions
        
        # 1. Click Decline Critical Alert (>= 20% decline)
        if prev_clicks >= settings.min_previous_clicks and comparison.click_pct_change <= -settings.click_critical_pct:
            key = (norm_url, "CLICK_DECLINE_CRITICAL", evaluation_date)
            if key not in existing_alerts:
                alert = Alert(
                    page_url=page.full_url,
                    normalized_url=norm_url,
                    category_id=category.id,
                    assigned_leader_id=category.assigned_leader_id,
                    alert_type="CLICK_DECLINE_CRITICAL",
                    severity="CRITICAL",
                    current_value=float(curr_clicks),
                    previous_value=float(prev_clicks),
                    pct_change=comparison.click_pct_change,
                    detection_date=evaluation_date,
                    period_start=curr_start,
                    period_end=curr_end,
                    status="PENDING"
                )
                db.add(alert)
                existing_alerts.add(key)
                alerts_created += 1

        # 2. Click Decline Warning Alert (>= 10% decline and < 20% decline)
        elif prev_clicks >= settings.min_previous_clicks and comparison.click_pct_change <= -settings.click_warning_pct:
            key = (norm_url, "CLICK_DECLINE_WARNING", evaluation_date)
            if key not in existing_alerts:
                alert = Alert(
                    page_url=page.full_url,
                    normalized_url=norm_url,
                    category_id=category.id,
                    assigned_leader_id=category.assigned_leader_id,
                    alert_type="CLICK_DECLINE_WARNING",
                    severity="WARNING",
                    current_value=float(curr_clicks),
                    previous_value=float(prev_clicks),
                    pct_change=comparison.click_pct_change,
                    detection_date=evaluation_date,
                    period_start=curr_start,
                    period_end=curr_end,
                    status="PENDING"
                )
                db.add(alert)
                existing_alerts.add(key)
                alerts_created += 1
        
        # 3. Visibility (Impression) Warning (>= 20% decline)
        if prev_impressions >= settings.min_previous_impressions and comparison.impression_pct_change <= -settings.impression_warning_pct:
            key = (norm_url, "IMPRESSION_DECLINE_WARNING", evaluation_date)
            if key not in existing_alerts:
                alert = Alert(
                    page_url=page.full_url,
                    normalized_url=norm_url,
                    category_id=category.id,
                    assigned_leader_id=category.assigned_leader_id,
                    alert_type="IMPRESSION_DECLINE_WARNING",
                    severity="WARNING",
                    current_value=float(curr_impressions),
                    previous_value=float(prev_impressions),
                    pct_change=comparison.impression_pct_change,
                    detection_date=evaluation_date,
                    period_start=curr_start,
                    period_end=curr_end,
                    status="PENDING"
                )
                db.add(alert)
                existing_alerts.add(key)
                alerts_created += 1
        
        # 4. Ranking Warning (Average position worsened by >= 3.0 positions)
        if prev_impressions >= settings.min_previous_impressions and comparison.position_diff >= settings.position_drop_warning:
            key = (norm_url, "POSITION_DROP_WARNING", evaluation_date)
            if key not in existing_alerts:
                alert = Alert(
                    page_url=page.full_url,
                    normalized_url=norm_url,
                    category_id=category.id,
                    assigned_leader_id=category.assigned_leader_id,
                    alert_type="POSITION_DROP_WARNING",
                    severity="WARNING",
                    current_value=float(comparison.current.position),
                    previous_value=float(comparison.previous.position),
                    pct_change=round(comparison.position_diff, 2),
                    detection_date=evaluation_date,
                    period_start=curr_start,
                    period_end=curr_end,
                    status="PENDING"
                )
                db.add(alert)
                existing_alerts.add(key)
                alerts_created += 1
                
    if alerts_created > 0:
        db.commit()
        
    return alerts_created
