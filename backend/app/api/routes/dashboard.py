from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.models.models import (
    User, UserRole, Category, CategoryPage, DailyPageMetrics, GSCProperty
)
from backend.app.schemas.schemas import DashboardKPIs, DailyTrendPoint, CategorySummary
from backend.app.api.deps import require_team_leader_or_manager
from backend.app.services.metric_service import (
    get_latest_data_date, get_28day_date_windows, get_page_aggregated_metrics,
    calculate_comparison_metrics, get_daily_trends
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/kpis", response_model=DashboardKPIs)
def get_dashboard_kpis(
    leader_id: Optional[int] = Query(None, description="Filter by Team Leader"),
    category_id: Optional[int] = Query(None, description="Filter by Category"),
    property_id: Optional[int] = Query(None, description="Filter by GSC Property"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Computes top-level KPI metrics comparing the latest 28 complete days
    with the immediately preceding 28 complete days.
    """
    # 1. Base counts
    total_leaders = db.query(User).filter(User.role == UserRole.TEAM_LEADER, User.is_active == True).count()
    
    cat_query = db.query(Category).filter(Category.status == "ACTIVE")
    if leader_id:
        cat_query = cat_query.filter(Category.assigned_leader_id == leader_id)
    if category_id:
        cat_query = cat_query.filter(Category.id == category_id)
    target_categories = cat_query.all()
    target_cat_ids = [c.id for c in target_categories]

    page_query = db.query(CategoryPage).filter(
        CategoryPage.category_id.in_(target_cat_ids),
        CategoryPage.status == "ACTIVE"
    )
    mapped_pages = page_query.all()
    norm_urls = list({p.normalized_url for p in mapped_pages})

    latest_date = get_latest_data_date(db, property_id)
    curr_start, curr_end, prev_start, prev_end = get_28day_date_windows(latest_date)

    curr_metrics = get_page_aggregated_metrics(db, norm_urls, curr_start, curr_end)
    prev_metrics = get_page_aggregated_metrics(db, norm_urls, prev_start, prev_end)

    curr_clicks = sum(m["clicks"] for m in curr_metrics.values())
    curr_imps = sum(m["impressions"] for m in curr_metrics.values())
    curr_pos_imp = sum(m["pos_imp_sum"] for m in curr_metrics.values())

    prev_clicks = sum(m["clicks"] for m in prev_metrics.values())
    prev_imps = sum(m["impressions"] for m in prev_metrics.values())
    prev_pos_imp = sum(m["pos_imp_sum"] for m in prev_metrics.values())

    comp = calculate_comparison_metrics(
        curr_clicks, curr_imps, curr_pos_imp,
        prev_clicks, prev_imps, prev_pos_imp
    )

    # Count pages with traffic decline
    pages_declining = 0
    for url in norm_urls:
        c_c = curr_metrics.get(url, {}).get("clicks", 0)
        p_c = prev_metrics.get(url, {}).get("clicks", 0)
        if c_c < p_c:
            pages_declining += 1

    # Check if demo property is active
    demo_prop = db.query(GSCProperty).filter(GSCProperty.is_demo == True, GSCProperty.is_active == True).first()
    is_demo = demo_prop is not None

    return DashboardKPIs(
        total_leaders=total_leaders,
        total_categories=len(target_categories),
        total_mapped_pages=len(mapped_pages),
        current_clicks=comp.current.clicks,
        previous_clicks=comp.previous.clicks,
        click_diff=comp.click_diff,
        click_pct_change=comp.click_pct_change,
        current_impressions=comp.current.impressions,
        previous_impressions=comp.previous.impressions,
        impression_diff=comp.impression_diff,
        impression_pct_change=comp.impression_pct_change,
        current_ctr=comp.current.ctr,
        previous_ctr=comp.previous.ctr,
        current_avg_position=comp.current.position,
        previous_avg_position=comp.previous.position,
        pages_with_decline=pages_declining,
        latest_data_date=str(latest_date) if latest_date else None,
        is_demo_data=is_demo
    )

@router.get("/trends", response_model=List[DailyTrendPoint])
def get_dashboard_trends(
    leader_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    property_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Returns 28-day daily click, impression, CTR, and position trends for charting."""
    cat_query = db.query(Category).filter(Category.status == "ACTIVE")
    if leader_id:
        cat_query = cat_query.filter(Category.assigned_leader_id == leader_id)
    if category_id:
        cat_query = cat_query.filter(Category.id == category_id)
    target_cat_ids = [c.id for c in cat_query.all()]

    pages = db.query(CategoryPage).filter(
        CategoryPage.category_id.in_(target_cat_ids),
        CategoryPage.status == "ACTIVE"
    ).all()
    norm_urls = list({p.normalized_url for p in pages})

    latest_date = get_latest_data_date(db, property_id)
    return get_daily_trends(db, normalized_urls=norm_urls if norm_urls else None, latest_date=latest_date)

@router.get("/categories-summary", response_model=List[CategorySummary])
def get_categories_comparison_summary(
    leader_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Returns all categories with their 28-day vs previous 28-day performance summary."""
    query = db.query(Category).join(User, Category.assigned_leader_id == User.id).filter(Category.status == "ACTIVE")
    if leader_id:
        query = query.filter(Category.assigned_leader_id == leader_id)
    categories = query.order_by(Category.name).all()

    latest_date = get_latest_data_date(db)
    curr_start, curr_end, prev_start, prev_end = get_28day_date_windows(latest_date)

    results = []
    for cat in categories:
        pages = db.query(CategoryPage).filter(
            CategoryPage.category_id == cat.id,
            CategoryPage.status == "ACTIVE"
        ).all()
        norm_urls = [p.normalized_url for p in pages]

        curr_m = get_page_aggregated_metrics(db, norm_urls, curr_start, curr_end)
        prev_m = get_page_aggregated_metrics(db, norm_urls, prev_start, prev_end)

        c_clicks = sum(m["clicks"] for m in curr_m.values())
        c_imps = sum(m["impressions"] for m in curr_m.values())
        c_pos = sum(m["pos_imp_sum"] for m in curr_m.values())

        p_clicks = sum(m["clicks"] for m in prev_m.values())
        p_imps = sum(m["impressions"] for m in prev_m.values())
        p_pos = sum(m["pos_imp_sum"] for m in prev_m.values())

        comp = calculate_comparison_metrics(c_clicks, c_imps, c_pos, p_clicks, p_imps, p_pos)

        results.append(CategorySummary(
            id=cat.id,
            name=cat.name,
            assigned_leader_id=cat.assigned_leader_id,
            leader_name=cat.leader.full_name if cat.leader else "Unassigned",
            page_count=len(pages),
            status=cat.status,
            metrics=comp
        ))

    return results
