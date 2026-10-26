from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import User, UserRole, Category, CategoryPage, Alert, DailyPageMetrics, SyncRun
from backend.app.schemas.schemas import (
    PageSummary, ComparisonMetrics, PeriodMetrics, DailyTrendPoint,
    LandingPageTrafficResponse, LandingPageTrafficItem, LandingPageTrafficSummary,
    TrafficWindowMetrics, TrafficComparison
)
from backend.app.api.deps import require_team_leader_or_manager
from backend.app.services.metric_service import (
    get_latest_data_date, get_28day_date_windows, get_page_aggregated_metrics,
    calculate_comparison_metrics, get_daily_trends, get_landing_page_traffic_metrics
)
from backend.app.services.settings_service import get_system_setting

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
    Enforces strict role-based visibility: Team leaders can only access their assigned categories/pages.
    """
    query = (
        db.query(CategoryPage, Category, User)
        .join(Category, CategoryPage.category_id == Category.id)
        .join(User, Category.assigned_leader_id == User.id)
        .filter(CategoryPage.status == "ACTIVE")
    )

    # Role-based visibility enforcement
    if current_user.role == UserRole.TEAM_LEADER:
        if leader_id and leader_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team leaders can only access metrics for their own assigned categories."
            )
        query = query.filter(Category.assigned_leader_id == current_user.id)
    elif leader_id:
        query = query.filter(Category.assigned_leader_id == leader_id)

    if category_id:
        if current_user.role == UserRole.TEAM_LEADER:
            cat_check = db.query(Category).filter(
                Category.id == category_id,
                Category.assigned_leader_id == current_user.id
            ).first()
            if not cat_check:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to view pages for this category."
                )
        query = query.filter(CategoryPage.category_id == category_id)

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

@router.get("/traffic", response_model=LandingPageTrafficResponse)
def get_landing_page_traffic(
    category_id: Optional[int] = Query(None, description="Filter by category"),
    leader_id: Optional[int] = Query(None, description="Filter by assigned team leader (Managers only)"),
    search: Optional[str] = Query(None, description="Search landing page URL"),
    sort_by: Optional[str] = Query("clicks_28d_desc", description="clicks_28d_desc | clicks_28d_asc | clicks_7d_desc | clicks_7d_asc | clicks_3d_desc | growth_desc | drop_desc | url_asc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Landing Page Traffic Monitoring:
    1. Returns mapped landing page URLs with 24h, 3d, 7d, and 28d traffic metrics.
    2. Enforces strict role-based visibility:
       - Manager: Can view all, filter by any Team Leader.
       - Team Leader: Can ONLY view assigned categories and URLs.
    3. Handles 24h traffic status:
       - Reports 'GA4 Required' since GA4 is not yet integrated.
       - Returns 'Latest GSC Day Clicks' from Search Console.
    4. Computes 7-day and 28-day growth/drop comparisons with division-by-zero protection.
    5. Returns summary KPI metrics and pagination metadata.
    """
    query = (
        db.query(CategoryPage, Category, User)
        .join(Category, CategoryPage.category_id == Category.id)
        .join(User, Category.assigned_leader_id == User.id)
        .filter(CategoryPage.status == "ACTIVE")
    )

    # Role-based visibility enforcement
    if current_user.role == UserRole.TEAM_LEADER:
        if leader_id and leader_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team leaders can only access traffic metrics for their own assigned categories."
            )
        query = query.filter(Category.assigned_leader_id == current_user.id)
    elif leader_id:
        query = query.filter(Category.assigned_leader_id == leader_id)

    if category_id:
        if current_user.role == UserRole.TEAM_LEADER:
            cat_check = db.query(Category).filter(
                Category.id == category_id,
                Category.assigned_leader_id == current_user.id
            ).first()
            if not cat_check:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to view traffic for this category."
                )
        query = query.filter(CategoryPage.category_id == category_id)

    if search:
        query = query.filter(CategoryPage.full_url.ilike(f"%{search}%"))

    all_matching_items = query.all()
    if not all_matching_items:
        latest_date = get_latest_data_date(db)
        return LandingPageTrafficResponse(
            items=[],
            total_items=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            summary=LandingPageTrafficSummary(
                total_pages_monitored=0,
                total_clicks_7d=0,
                total_clicks_28d=0,
                total_impressions_28d=0,
                avg_position_28d=0.0,
                growing_pages_count=0,
                declining_pages_count=0,
                ga4_connected=False,
                latest_data_date=str(latest_date) if latest_date else None,
            )
        )

    norm_urls = list({item.CategoryPage.normalized_url for item in all_matching_items})
    latest_date = get_latest_data_date(db)
    traffic_metrics, ranges = get_landing_page_traffic_metrics(db, norm_urls, latest_date=latest_date)

    # Check GA4 configuration
    ga4_prop_id = get_system_setting(db, "GA4_PROPERTY_ID")
    ga4_connected = bool(ga4_prop_id)
    ga4_status_label = "Connected" if ga4_connected else "GA4 Required"

    # Get latest successful sync run
    last_sync = db.query(SyncRun).filter(SyncRun.status == "SUCCESS").order_by(SyncRun.id.desc()).first()
    last_sync_time_str = last_sync.end_time.isoformat() if (last_sync and last_sync.end_time) else None

    # Construct items
    items_list: List[LandingPageTrafficItem] = []
    tot_clicks_7d = 0
    tot_clicks_28d = 0
    tot_imp_28d = 0
    pos_imp_sum_28d = 0.0
    growing_count = 0
    declining_count = 0

    for item in all_matching_items:
        page_rec = item.CategoryPage
        cat_rec = item.Category
        leader_rec = item.User

        tm = traffic_metrics.get(page_rec.normalized_url, {
            "latest_gsc_day_clicks": 0,
            "latest_gsc_date": ranges.get("latest_gsc_date"),
            "traffic_3d": {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0, "start_date": None, "end_date": None},
            "traffic_7d": {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0, "start_date": None, "end_date": None},
            "traffic_28d": {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0, "start_date": None, "end_date": None},
            "comparison_7d": {"current_clicks": 0, "previous_clicks": 0, "click_diff": 0, "pct_change": 0.0, "status": "NEUTRAL"},
            "comparison_28d": {"current_clicks": 0, "previous_clicks": 0, "click_diff": 0, "pct_change": 0.0, "status": "NEUTRAL"},
        })

        t3 = tm["traffic_3d"]
        t7 = tm["traffic_7d"]
        t28 = tm["traffic_28d"]
        c7 = tm["comparison_7d"]
        c28 = tm["comparison_28d"]

        tot_clicks_7d += t7["clicks"]
        tot_clicks_28d += t28["clicks"]
        tot_imp_28d += t28["impressions"]
        pos_imp_sum_28d += (t28["position"] * t28["impressions"])

        if c28["status"] == "GROWTH":
            growing_count += 1
        elif c28["status"] == "DECLINE":
            declining_count += 1

        items_list.append(LandingPageTrafficItem(
            id=page_rec.id,
            full_url=page_rec.full_url,
            normalized_url=page_rec.normalized_url,
            category_id=cat_rec.id,
            category_name=cat_rec.name,
            assigned_leader_id=leader_rec.id,
            leader_name=leader_rec.full_name,
            ga4_status=ga4_status_label,
            latest_gsc_day_clicks=tm["latest_gsc_day_clicks"],
            latest_gsc_date=tm["latest_gsc_date"],
            traffic_3d=TrafficWindowMetrics(**t3),
            traffic_7d=TrafficWindowMetrics(**t7),
            traffic_28d=TrafficWindowMetrics(**t28),
            comparison_7d=TrafficComparison(**c7),
            comparison_28d=TrafficComparison(**c28),
            last_updated=last_sync_time_str or (str(latest_date) if latest_date else None)
        ))

    # Sorting
    if sort_by == "clicks_28d_desc":
        items_list.sort(key=lambda x: x.traffic_28d.clicks, reverse=True)
    elif sort_by == "clicks_28d_asc":
        items_list.sort(key=lambda x: x.traffic_28d.clicks)
    elif sort_by == "clicks_7d_desc":
        items_list.sort(key=lambda x: x.traffic_7d.clicks, reverse=True)
    elif sort_by == "clicks_7d_asc":
        items_list.sort(key=lambda x: x.traffic_7d.clicks)
    elif sort_by == "clicks_3d_desc":
        items_list.sort(key=lambda x: x.traffic_3d.clicks, reverse=True)
    elif sort_by == "growth_desc":
        items_list.sort(key=lambda x: x.comparison_28d.pct_change, reverse=True)
    elif sort_by == "drop_desc":
        items_list.sort(key=lambda x: x.comparison_28d.pct_change)
    elif sort_by == "url_asc":
        items_list.sort(key=lambda x: x.full_url.lower())
    else:
        items_list.sort(key=lambda x: x.traffic_28d.clicks, reverse=True)

    # Summary
    avg_pos_28d = round(pos_imp_sum_28d / tot_imp_28d, 2) if tot_imp_28d > 0 else 0.0
    summary = LandingPageTrafficSummary(
        total_pages_monitored=len(items_list),
        total_clicks_7d=tot_clicks_7d,
        total_clicks_28d=tot_clicks_28d,
        total_impressions_28d=tot_imp_28d,
        avg_position_28d=avg_pos_28d,
        growing_pages_count=growing_count,
        declining_pages_count=declining_count,
        ga4_connected=ga4_connected,
        latest_data_date=str(latest_date) if latest_date else None,
        reporting_range_28d=ranges.get("range_28d"),
        reporting_range_7d=ranges.get("range_7d"),
        reporting_range_3d=ranges.get("range_3d"),
        last_sync_time=last_sync_time_str
    )

    # Pagination
    total_items = len(items_list)
    import math
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_items = items_list[start_idx:end_idx]

    return LandingPageTrafficResponse(
        items=paged_items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        summary=summary
    )

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
