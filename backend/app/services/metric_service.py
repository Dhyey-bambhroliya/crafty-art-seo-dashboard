from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from backend.app.models.models import DailyPageMetrics, CategoryPage, Category, User
from backend.app.schemas.schemas import (
    PeriodMetrics, ComparisonMetrics, DailyTrendPoint, CategorySummary, PageSummary, DashboardKPIs
)

def normalize_url(raw_url: str) -> str:
    """
    Standardize URL format for reliable GSC matching:
    - Lowercase scheme and hostname
    - Strip common analytics/tracking query params (utm_*, gclid, etc.)
    - Remove fragment (#...)
    - Normalize trailing slash (remove trailing slash unless it's just the root domain path)
    """
    if not raw_url:
        return ""
    
    raw_url = raw_url.strip()
    if not raw_url.lower().startswith(("http://", "https://")):
        raw_url = "https://" + raw_url
    
    parsed = urlparse(raw_url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    
    # Must have a valid hostname with at least one dot (domain.tld)
    if "." not in netloc or len(netloc) < 3 or netloc.startswith("."):
        return ""
    
    # Strip www prefix if present for uniform comparison or keep standard
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = "/"
    
    # Filter tracking query parameters
    query_parts = []
    if parsed.query:
        for param in parsed.query.split("&"):
            if param:
                key = param.split("=")[0].lower()
                if not (key.startswith("utm_") or key in ["fbclid", "gclid", "_ga", "ref"]):
                    query_parts.append(param)
    
    clean_query = "&".join(query_parts) if query_parts else ""
    return urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))

def get_latest_data_date(db: Session, property_id: Optional[int] = None) -> Optional[date]:
    """Find the most recent metric date recorded in the system."""
    query = db.query(func.max(DailyPageMetrics.date))
    if property_id:
        query = query.filter(DailyPageMetrics.property_id == property_id)
    return query.scalar()

def get_28day_date_windows(latest_date: Optional[date] = None) -> Tuple[date, date, date, date]:
    """
    Returns (curr_start, curr_end, prev_start, prev_end)
    Current period: [latest_date - 27 days, latest_date] (28 complete days)
    Previous period: [latest_date - 55 days, latest_date - 28 days] (28 preceding complete days)
    """
    if not latest_date:
        latest_date = date.today() - timedelta(days=2)  # GSC usually has ~2-3 days latency
    
    curr_end = latest_date
    curr_start = latest_date - timedelta(days=27)
    prev_end = latest_date - timedelta(days=28)
    prev_start = latest_date - timedelta(days=55)
    
    return curr_start, curr_end, prev_start, prev_end

def calculate_comparison_metrics(
    curr_clicks: int,
    curr_impressions: int,
    curr_pos_imp_sum: float,
    prev_clicks: int,
    prev_impressions: int,
    prev_pos_imp_sum: float
) -> ComparisonMetrics:
    """
    Computes CTR and Impression-Weighted Average Position:
    - CTR = clicks / impressions
    - Position = sum(position * impressions) / sum(impressions)
    """
    # Current period calculations
    curr_ctr = (curr_clicks / curr_impressions * 100.0) if curr_impressions > 0 else 0.0
    curr_pos = (curr_pos_imp_sum / curr_impressions) if curr_impressions > 0 else 0.0
    
    # Previous period calculations
    prev_ctr = (prev_clicks / prev_impressions * 100.0) if prev_impressions > 0 else 0.0
    prev_pos = (prev_pos_imp_sum / prev_impressions) if prev_impressions > 0 else 0.0
    
    click_diff = curr_clicks - prev_clicks
    click_pct = ((click_diff / prev_clicks) * 100.0) if prev_clicks > 0 else (100.0 if curr_clicks > 0 else 0.0)
    
    imp_diff = curr_impressions - prev_impressions
    imp_pct = ((imp_diff / prev_impressions) * 100.0) if prev_impressions > 0 else (100.0 if curr_impressions > 0 else 0.0)
    
    ctr_diff = curr_ctr - prev_ctr
    pos_diff = curr_pos - prev_pos
    
    # For position, lower is better (e.g. 3.0 vs 5.0 is -2.0 diff -> IMPROVED)
    if pos_diff < -0.3:
        pos_status = "IMPROVED"
    elif pos_diff > 0.3:
        pos_status = "DECLINED"
    else:
        pos_status = "STABLE"
    
    return ComparisonMetrics(
        current=PeriodMetrics(
            clicks=curr_clicks,
            impressions=curr_impressions,
            ctr=round(curr_ctr, 2),
            position=round(curr_pos, 2)
        ),
        previous=PeriodMetrics(
            clicks=prev_clicks,
            impressions=prev_impressions,
            ctr=round(prev_ctr, 2),
            position=round(prev_pos, 2)
        ),
        click_diff=click_diff,
        click_pct_change=round(click_pct, 2),
        impression_diff=imp_diff,
        impression_pct_change=round(imp_pct, 2),
        ctr_diff=round(ctr_diff, 2),
        position_diff=round(pos_diff, 2),
        position_status=pos_status
    )

def get_page_aggregated_metrics(
    db: Session,
    normalized_urls: List[str],
    start_date: date,
    end_date: date
) -> Dict[str, Dict[str, float]]:
    """
    Returns metrics per normalized_url in given date range:
    { norm_url: { 'clicks': x, 'impressions': y, 'pos_imp_sum': z } }
    """
    if not normalized_urls:
        return {}
    
    # Query aggregated daily metrics
    rows = (
        db.query(
            DailyPageMetrics.normalized_url,
            func.sum(DailyPageMetrics.clicks).label("clicks"),
            func.sum(DailyPageMetrics.impressions).label("impressions"),
            func.sum(DailyPageMetrics.position * DailyPageMetrics.impressions).label("pos_imp_sum")
        )
        .filter(
            DailyPageMetrics.normalized_url.in_(normalized_urls),
            DailyPageMetrics.date >= start_date,
            DailyPageMetrics.date <= end_date
        )
        .group_by(DailyPageMetrics.normalized_url)
        .all()
    )
    
    res = {}
    for row in rows:
        res[row.normalized_url] = {
            "clicks": int(row.clicks or 0),
            "impressions": int(row.impressions or 0),
            "pos_imp_sum": float(row.pos_imp_sum or 0.0)
        }
    return res

def get_daily_trends(
    db: Session,
    normalized_urls: Optional[List[str]] = None,
    latest_date: Optional[date] = None
) -> List[DailyTrendPoint]:
    """Generates 28-day daily points with matching day-of-week comparison from previous 28 days."""
    if not latest_date:
        latest_date = get_latest_data_date(db)
    curr_start, curr_end, prev_start, prev_end = get_28day_date_windows(latest_date)
    
    curr_query = (
        db.query(
            DailyPageMetrics.date,
            func.sum(DailyPageMetrics.clicks).label("clicks"),
            func.sum(DailyPageMetrics.impressions).label("impressions"),
            func.sum(DailyPageMetrics.position * DailyPageMetrics.impressions).label("pos_imp_sum")
        )
        .filter(DailyPageMetrics.date >= curr_start, DailyPageMetrics.date <= curr_end)
    )
    if normalized_urls:
        curr_query = curr_query.filter(DailyPageMetrics.normalized_url.in_(normalized_urls))
    curr_rows = {r.date: r for r in curr_query.group_by(DailyPageMetrics.date).all()}
    
    # Previous period data
    prev_query = (
        db.query(
            DailyPageMetrics.date,
            func.sum(DailyPageMetrics.clicks).label("clicks"),
            func.sum(DailyPageMetrics.impressions).label("impressions")
        )
        .filter(DailyPageMetrics.date >= prev_start, DailyPageMetrics.date <= prev_end)
    )
    if normalized_urls:
        prev_query = prev_query.filter(DailyPageMetrics.normalized_url.in_(normalized_urls))
    prev_rows = {r.date: r for r in prev_query.group_by(DailyPageMetrics.date).all()}
    
    trends = []
    # Loop over the 28 days
    curr_day = curr_start
    while curr_day <= curr_end:
        # Corresponding day in previous period (shifted 28 days back for aligned day-of-week)
        prev_day = curr_day - timedelta(days=28)
        
        c_row = curr_rows.get(curr_day)
        p_row = prev_rows.get(prev_day)
        
        c_clicks = int(c_row.clicks or 0) if c_row else 0
        c_imps = int(c_row.impressions or 0) if c_row else 0
        c_pos_imp = float(c_row.pos_imp_sum or 0.0) if c_row else 0.0
        
        p_clicks = int(p_row.clicks or 0) if p_row else 0
        p_imps = int(p_row.impressions or 0) if p_row else 0
        
        ctr = round((c_clicks / c_imps * 100.0), 2) if c_imps > 0 else 0.0
        pos = round((c_pos_imp / c_imps), 2) if c_imps > 0 else 0.0
        
        trends.append(DailyTrendPoint(
            date=curr_day.strftime("%b %d"),
            current_clicks=c_clicks,
            current_impressions=c_imps,
            previous_clicks=p_clicks,
            previous_impressions=p_imps,
            ctr=ctr,
            position=pos
        ))
        curr_day += timedelta(days=1)
    
    return trends
