from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import User, UserRole, Category, CategoryPage, Alert, DailyPageMetrics
from backend.app.schemas.schemas import PageSummary, ComparisonMetrics, PeriodMetrics, DailyTrendPoint
from backend.app.api.deps import require_team_leader_or_manager
from backend.app.services.metric_service import (
    get_latest_data_date, get_28day_date_windows, get_page_aggregated_metrics,
    calculate_comparison_metrics, get_daily_trends
)

router = APIRouter(prefix="/pages", tags=["Pages Monitoring"])

@router.get("", response_model=List[PageSummary])
def list_pages_monitoring(
    category_id: Optional[int] = Query(None, description="Filter by category"),
    leader_id: Optional[int] = Query(None, description="Filter by assigned team leader"),
    sort_by: Optional[str] = Query("traffic_loss", description="traffic_loss | pct_loss | impressions_loss | clicks | impressions"),
    search: Optional[str] = Query(None, description="Search URL"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    List mapped pages with 28-day vs previous 28-day performance metrics.
    Supports sorting by largest traffic loss, percentage loss, or impressions loss.
    """
    query = (
        db.query(CategoryPage, Category, User)
        .join(Category, CategoryPage.category_id == Category.id)
        .join(User, Category.assigned_leader_id == User.id)
        .filter(CategoryPage.status == "ACTIVE")
    )

    if category_id:
        query = query.filter(CategoryPage.category_id == category_id)

    if leader_id:
        query = query.filter(Category.assigned_leader_id == leader_id)

    if search:
        query = query.filter(CategoryPage.full_url.ilike(f"%{search}%"))

    items = query.all()
    if not items:
        return []

    norm_urls = list({item.CategoryPage.normalized_url for item in items})
    latest_date = get_latest_data_date(db)
    curr_start, curr_end, prev_start, prev_end = get_28day_date_windows(latest_date)

    curr_metrics = get_page_aggregated_metrics(db, norm_urls, curr_start, curr_end)
    prev_metrics = get_page_aggregated_metrics(db, norm_urls, prev_start, prev_end)

    # Active alerts mapping
    active_alerts = (
        db.query(Alert.normalized_url)
        .filter(Alert.status == "PENDING", Alert.normalized_url.in_(norm_urls))
        .all()
    )
    alert_counts = {}
    for a in active_alerts:
        alert_counts[a.normalized_url] = alert_counts.get(a.normalized_url, 0) + 1

    summaries = []
    for item in items:
        page = item.CategoryPage
        cat = item.Category
        leader = item.User

        c = curr_metrics.get(page.normalized_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})
        p = prev_metrics.get(page.normalized_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})

        comp = calculate_comparison_metrics(
            c["clicks"], c["impressions"], c["pos_imp_sum"],
            p["clicks"], p["impressions"], p["pos_imp_sum"]
        )

        summaries.append(PageSummary(
            id=page.id,
            full_url=page.full_url,
            normalized_url=page.normalized_url,
            category_id=cat.id,
            category_name=cat.name,
            assigned_leader_id=leader.id,
            leader_name=leader.full_name,
            status=page.status,
            metrics=comp,
            active_alerts=alert_counts.get(page.normalized_url, 0)
        ))

    # Sort
    if sort_by == "traffic_loss":
        summaries.sort(key=lambda x: x.metrics.click_diff)  # most negative click_diff first
    elif sort_by == "pct_loss":
        summaries.sort(key=lambda x: x.metrics.click_pct_change)
    elif sort_by == "impressions_loss":
        summaries.sort(key=lambda x: x.metrics.impression_diff)
    elif sort_by == "clicks":
        summaries.sort(key=lambda x: x.metrics.current.clicks, reverse=True)
    elif sort_by == "impressions":
        summaries.sort(key=lambda x: x.metrics.current.impressions, reverse=True)

    return summaries[:limit]

@router.get("/{page_id}")
def get_page_detail(
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Detailed page performance report with 28-day comparison, daily trend points, and alert history.
    """
    page_record = (
        db.query(CategoryPage, Category, User)
        .join(Category, CategoryPage.category_id == Category.id)
        .join(User, Category.assigned_leader_id == User.id)
        .filter(CategoryPage.id == page_id)
        .first()
    )
    if not page_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found.")

    page, category, leader = page_record

    latest_date = get_latest_data_date(db)
    curr_start, curr_end, prev_start, prev_end = get_28day_date_windows(latest_date)

    curr_metrics = get_page_aggregated_metrics(db, [page.normalized_url], curr_start, curr_end)
    prev_metrics = get_page_aggregated_metrics(db, [page.normalized_url], prev_start, prev_end)

    c = curr_metrics.get(page.normalized_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})
    p = prev_metrics.get(page.normalized_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})

    comparison = calculate_comparison_metrics(
        c["clicks"], c["impressions"], c["pos_imp_sum"],
        p["clicks"], p["impressions"], p["pos_imp_sum"]
    )

    daily_trends = get_daily_trends(db, normalized_urls=[page.normalized_url], latest_date=latest_date)

    alerts = (
        db.query(Alert)
        .filter(Alert.normalized_url == page.normalized_url)
        .order_by(Alert.detection_date.desc(), Alert.id.desc())
        .all()
    )

    has_metrics_history = db.query(DailyPageMetrics).filter(
        DailyPageMetrics.normalized_url == page.normalized_url
    ).count() > 0

    return {
        "id": page.id,
        "full_url": page.full_url,
        "normalized_url": page.normalized_url,
        "status": page.status,
        "category_id": category.id,
        "category_name": category.name,
        "assigned_leader_id": leader.id,
        "leader_name": leader.full_name,
        "created_at": page.created_at,
        "has_data": has_metrics_history,
        "latest_data_date": str(latest_date) if latest_date else None,
        "comparison": comparison,
        "daily_trends": daily_trends,
        "alerts": alerts
    }
