from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status

from backend.app.models.models import User, UserRole, GSCProperty, DailyPageMetrics, Category, CategoryPage
from backend.app.models.festival_models import (
    Festival, FestivalYearDate, FestivalSubcategory, FestivalPage,
    DailyPageCountryMetrics, FestivalApprovalStatus
)
from backend.app.schemas.festival_schemas import (
    FestivalSeasonComparisonResponse, FestivalYoYSummary,
    FestivalMetricPeriod, FestivalPageComparison,
    RelativeDailyTrendPoint, AvailableHistoricalRangeResponse
)
from backend.app.services.festival_service import (
    get_festival_by_id, check_festival_access_permission
)

def calculate_growth_metrics(curr: int, prev: int) -> Tuple[Optional[float], str]:
    """
    Computes percentage growth and status label with zero-baseline handling:
    - If prev > 0: returns (round(((curr - prev) / prev) * 100.0, 2), f"{pct:+.1f}%")
    - If prev == 0 and curr > 0: returns (None, "NEW_TRAFFIC")
    - If prev == 0 and curr == 0: returns (None, "NO_BASELINE")
    Never returns 100% when there is no historical baseline.
    """
    if prev > 0:
        pct = round(((curr - prev) / prev) * 100.0, 2)
        return pct, f"{pct:+.1f}%"
    elif curr > 0:
        return None, "NEW_TRAFFIC"
    else:
        return None, "NO_BASELINE"


def get_festival_available_range(
    db: Session,
    festival_id: int,
    current_user: User
) -> AvailableHistoricalRangeResponse:
    """Returns available historical date ranges, configured years, and supported searcher countries."""
    festival = get_festival_by_id(db, festival_id, current_user)
    
    # Check configured years
    years = [yd.year for yd in db.query(FestivalYearDate.year).filter(FestivalYearDate.festival_id == festival_id).order_by(FestivalYearDate.year).all()]
    
    # Get distinct mapped normalized URLs
    mapped_pages = db.query(FestivalPage).filter(
        FestivalPage.festival_id == festival_id,
        FestivalPage.status == "ACTIVE"
    ).all()
    norm_urls = list({p.normalized_url for p in mapped_pages})
    
    earliest_date = None
    latest_date = None
    if norm_urls:
        earliest_date = db.query(func.min(DailyPageMetrics.date)).filter(DailyPageMetrics.normalized_url.in_(norm_urls)).scalar()
        latest_date = db.query(func.max(DailyPageMetrics.date)).filter(DailyPageMetrics.normalized_url.in_(norm_urls)).scalar()
        
    # Supported countries with data
    countries_query = db.query(DailyPageCountryMetrics.country_code).filter(
        DailyPageCountryMetrics.normalized_url.in_(norm_urls)
    ).distinct().all() if norm_urls else []
    supported_countries = sorted([c[0].upper() for c in countries_query])
    
    return AvailableHistoricalRangeResponse(
        festival_id=festival.id,
        festival_name=festival.name,
        earliest_date=earliest_date,
        latest_date=latest_date,
        configured_years=years,
        supported_searcher_countries=supported_countries,
        mapped_page_count=len(norm_urls),
        note="Historical worldwide metrics are retained locally. Country-level metrics are tracked additively."
    )

def compare_festival_seasons(
    db: Session,
    festival_id: int,
    current_year: int,
    previous_year: Optional[int] = None,
    searcher_country: Optional[str] = None,
    relative_days_before: int = 30,
    relative_days_after: int = 5,
    current_user: Optional[User] = None
) -> FestivalSeasonComparisonResponse:
    """
    Performs year-over-year GSC performance comparisons for a festival based on
    equivalent relative days anchored to the festival date.
    
    Handles:
    - Relative day alignment (Day -30 to Day +5)
    - Incomplete seasons (apples-to-apples comparison of available days)
    - Zero impression & missing data differentiation
    - Deduplication of mapped URLs across multiple subcategories
    - Country-level filtering via additive storage
    - Team Leader authorization enforcement
    """
    if current_user:
        festival = get_festival_by_id(db, festival_id, current_user)
    else:
        festival = db.query(Festival).filter(Festival.id == festival_id).first()
        if not festival:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival not found.")

    if previous_year is None:
        previous_year = current_year - 1

    # Fetch current year edition
    curr_yd = db.query(FestivalYearDate).filter(
        FestivalYearDate.festival_id == festival_id,
        FestivalYearDate.year == current_year
    ).first()
    if not curr_yd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Festival '{festival.name}' does not have date records configured for year {current_year}."
        )

    # Fetch previous year edition
    prev_yd = db.query(FestivalYearDate).filter(
        FestivalYearDate.festival_id == festival_id,
        FestivalYearDate.year == previous_year
    ).first()

    curr_start_date = curr_yd.start_date
    prev_start_date = prev_yd.start_date if prev_yd else None

    # Fetch mapped landing pages (deduplicating URLs)
    mapped_pages = db.query(FestivalPage).filter(
        FestivalPage.festival_id == festival_id,
        FestivalPage.status == "ACTIVE"
    ).all()

    # Group pages by normalized_url to prevent duplicate counting
    pages_by_norm_url: Dict[str, FestivalPage] = {}
    subcategory_names: Dict[int, str] = {}
    
    # Cache subcategory names
    subcats = db.query(FestivalSubcategory).filter(FestivalSubcategory.festival_id == festival_id).all()
    for sc in subcats:
        subcategory_names[sc.id] = sc.name

    for p in mapped_pages:
        if p.normalized_url not in pages_by_norm_url:
            pages_by_norm_url[p.normalized_url] = p

    norm_urls = list(pages_by_norm_url.keys())

    # Build relative day offset window
    # e.g., relative_days_before = 30 -> offset -30 to +relative_days_after (+5)
    relative_offsets = list(range(-abs(relative_days_before), abs(relative_days_after) + 1))
    total_window_days = len(relative_offsets)

    # Identify date mapping for both years
    curr_date_by_offset: Dict[int, date] = {r: curr_start_date + timedelta(days=r) for r in relative_offsets}
    prev_date_by_offset: Dict[int, date] = (
        {r: prev_start_date + timedelta(days=r) for r in relative_offsets}
        if prev_start_date else {}
    )

    all_curr_dates = list(curr_date_by_offset.values())
    all_prev_dates = list(prev_date_by_offset.values())

    # Country filter handling
    norm_searcher_country = searcher_country.strip().upper() if searcher_country and searcher_country.strip().upper() not in ["ALL", "WORLDWIDE"] else None
    searcher_country_label = norm_searcher_country if norm_searcher_country else "Worldwide (All Countries)"

    # Query metrics from DB:
    # If specific country requested: query DailyPageCountryMetrics
    # If worldwide: query DailyPageMetrics
    country_data_available = True
    raw_curr_metrics: List[Any] = []
    raw_prev_metrics: List[Any] = []

    # Check latest date with any GSC data in the system
    system_latest_date = None

    if norm_searcher_country:
        system_latest_date = db.query(func.max(DailyPageCountryMetrics.date)).filter(
            DailyPageCountryMetrics.country_code.in_([norm_searcher_country.lower(), norm_searcher_country])
        ).scalar()
        
        # Check if country data exists for these URLs
        country_records_count = db.query(func.count(DailyPageCountryMetrics.id)).filter(
            DailyPageCountryMetrics.normalized_url.in_(norm_urls) if norm_urls else False,
            DailyPageCountryMetrics.country_code.in_([norm_searcher_country.lower(), norm_searcher_country])
        ).scalar() if norm_urls else 0

        if country_records_count == 0:
            country_data_available = False

        if country_data_available and norm_urls:
            raw_curr_metrics = db.query(
                DailyPageCountryMetrics.normalized_url,
                DailyPageCountryMetrics.date,
                DailyPageCountryMetrics.clicks,
                DailyPageCountryMetrics.impressions,
                DailyPageCountryMetrics.position
            ).filter(
                DailyPageCountryMetrics.normalized_url.in_(norm_urls),
                DailyPageCountryMetrics.date.in_(all_curr_dates),
                DailyPageCountryMetrics.country_code.in_([norm_searcher_country.lower(), norm_searcher_country])
            ).all()

            if all_prev_dates:
                raw_prev_metrics = db.query(
                    DailyPageCountryMetrics.normalized_url,
                    DailyPageCountryMetrics.date,
                    DailyPageCountryMetrics.clicks,
                    DailyPageCountryMetrics.impressions,
                    DailyPageCountryMetrics.position
                ).filter(
                    DailyPageCountryMetrics.normalized_url.in_(norm_urls),
                    DailyPageCountryMetrics.date.in_(all_prev_dates),
                    DailyPageCountryMetrics.country_code.in_([norm_searcher_country.lower(), norm_searcher_country])
                ).all()
    else:
        system_latest_date = db.query(func.max(DailyPageMetrics.date)).scalar()
        if norm_urls:
            raw_curr_metrics = db.query(
                DailyPageMetrics.normalized_url,
                DailyPageMetrics.date,
                DailyPageMetrics.clicks,
                DailyPageMetrics.impressions,
                DailyPageMetrics.position
            ).filter(
                DailyPageMetrics.normalized_url.in_(norm_urls),
                DailyPageMetrics.date.in_(all_curr_dates)
            ).all()

            if all_prev_dates:
                raw_prev_metrics = db.query(
                    DailyPageMetrics.normalized_url,
                    DailyPageMetrics.date,
                    DailyPageMetrics.clicks,
                    DailyPageMetrics.impressions,
                    DailyPageMetrics.position
                ).filter(
                    DailyPageMetrics.normalized_url.in_(norm_urls),
                    DailyPageMetrics.date.in_(all_prev_dates)
                ).all()

    # Index metrics by (normalized_url, date)
    curr_page_date_map: Dict[Tuple[str, date], Dict[str, Any]] = {}
    for r in raw_curr_metrics:
        curr_page_date_map[(r[0], r[1])] = {
            "clicks": r[2],
            "impressions": r[3],
            "position": r[4]
        }

    prev_page_date_map: Dict[Tuple[str, date], Dict[str, Any]] = {}
    for r in raw_prev_metrics:
        prev_page_date_map[(r[0], r[1])] = {
            "clicks": r[2],
            "impressions": r[3],
            "position": r[4]
        }

    # Determine availability of dates based on system_latest_date
    # A date is available if it has arrived and is <= system_latest_date
    is_curr_date_available = lambda d: (system_latest_date is not None and d <= system_latest_date)
    is_prev_date_available = lambda d: (system_latest_date is not None and d <= system_latest_date)

    # Calculate Season Status
    available_curr_offsets = [r for r in relative_offsets if is_curr_date_available(curr_date_by_offset[r])]
    available_prev_offsets = [r for r in relative_offsets if prev_date_by_offset and is_prev_date_available(prev_date_by_offset[r])]

    if not country_data_available:
        season_status = "DATA_UNAVAILABLE"
    elif not available_curr_offsets:
        season_status = "DATA_UNAVAILABLE"
    elif len(available_curr_offsets) < total_window_days:
        season_status = "SEASON_TO_DATE"
    else:
        season_status = "COMPLETE"

    # Equivalent Available Days for Fair Apples-to-Apples Summary:
    # If both seasons have data, compare intersection of available relative offsets
    if prev_yd and available_prev_offsets:
        compared_offsets = sorted(list(set(available_curr_offsets).intersection(set(available_prev_offsets))))
    else:
        compared_offsets = sorted(available_curr_offsets)

    # 1. Festival-level Daily Trends
    relative_trends: List[RelativeDailyTrendPoint] = []
    for r in relative_offsets:
        c_date = curr_date_by_offset[r]
        p_date = prev_date_by_offset.get(r)
        
        c_avail = is_curr_date_available(c_date) and country_data_available
        p_avail = (p_date is not None) and is_prev_date_available(p_date) and country_data_available

        # Aggregate across distinct URLs for day r
        c_clicks = sum(curr_page_date_map.get((u, c_date), {}).get("clicks", 0) for u in norm_urls) if c_avail else None
        c_imp = sum(curr_page_date_map.get((u, c_date), {}).get("impressions", 0) for u in norm_urls) if c_avail else None
        
        c_ctr = None
        c_pos = None
        if c_avail and c_imp is not None:
            c_ctr = round((c_clicks / c_imp * 100.0), 2) if c_imp > 0 else 0.0
            pos_sum = sum(curr_page_date_map.get((u, c_date), {}).get("position", 0.0) * curr_page_date_map.get((u, c_date), {}).get("impressions", 0) for u in norm_urls)
            c_pos = round((pos_sum / c_imp), 2) if c_imp > 0 else 0.0

        p_clicks = sum(prev_page_date_map.get((u, p_date), {}).get("clicks", 0) for u in norm_urls) if p_avail else None
        p_imp = sum(prev_page_date_map.get((u, p_date), {}).get("impressions", 0) for u in norm_urls) if p_avail else None
        
        p_ctr = None
        p_pos = None
        if p_avail and p_imp is not None:
            p_ctr = round((p_clicks / p_imp * 100.0), 2) if p_imp > 0 else 0.0
            p_pos_sum = sum(prev_page_date_map.get((u, p_date), {}).get("position", 0.0) * prev_page_date_map.get((u, p_date), {}).get("impressions", 0) for u in norm_urls)
            p_pos = round((p_pos_sum / p_imp), 2) if p_imp > 0 else 0.0

        relative_trends.append(RelativeDailyTrendPoint(
            relative_day=r,
            current_date=c_date,
            previous_date=p_date,
            is_current_available=c_avail,
            is_previous_available=p_avail,
            current_clicks=c_clicks,
            previous_clicks=p_clicks,
            current_impressions=c_imp,
            previous_impressions=p_imp,
            current_ctr=c_ctr,
            previous_ctr=p_ctr,
            current_position=c_pos,
            previous_position=p_pos
        ))

    # 2. Individual Landing Page Comparisons
    landing_pages: List[FestivalPageComparison] = []
    
    for u in norm_urls:
        page_model = pages_by_norm_url[u]
        subcat_name = subcategory_names.get(page_model.subcategory_id) if page_model.subcategory_id else None

        # Calculate totals across compared_offsets for this URL
        p_curr_clicks = sum(curr_page_date_map.get((u, curr_date_by_offset[r]), {}).get("clicks", 0) for r in compared_offsets) if country_data_available else 0
        p_curr_imp = sum(curr_page_date_map.get((u, curr_date_by_offset[r]), {}).get("impressions", 0) for r in compared_offsets) if country_data_available else 0
        p_curr_pos_sum = sum(curr_page_date_map.get((u, curr_date_by_offset[r]), {}).get("position", 0.0) * curr_page_date_map.get((u, curr_date_by_offset[r]), {}).get("impressions", 0) for r in compared_offsets) if country_data_available else 0.0

        p_prev_clicks = sum(prev_page_date_map.get((u, prev_date_by_offset[r]), {}).get("clicks", 0) for r in compared_offsets) if (prev_yd and country_data_available) else 0
        p_prev_imp = sum(prev_page_date_map.get((u, prev_date_by_offset[r]), {}).get("impressions", 0) for r in compared_offsets) if (prev_yd and country_data_available) else 0
        p_prev_pos_sum = sum(prev_page_date_map.get((u, prev_date_by_offset[r]), {}).get("position", 0.0) * prev_page_date_map.get((u, prev_date_by_offset[r]), {}).get("impressions", 0) for r in compared_offsets) if (prev_yd and country_data_available) else 0.0

        # CTR and Positions
        curr_ctr = round((p_curr_clicks / p_curr_imp * 100.0), 2) if p_curr_imp > 0 else 0.0
        curr_pos = round((p_curr_pos_sum / p_curr_imp), 2) if p_curr_imp > 0 else 0.0

        prev_ctr = round((p_prev_clicks / p_prev_imp * 100.0), 2) if p_prev_imp > 0 else 0.0
        prev_pos = round((p_prev_pos_sum / p_prev_imp), 2) if p_prev_imp > 0 else 0.0

        # Growth & differences
        c_diff = p_curr_clicks - p_prev_clicks
        c_growth_pct, c_growth_status = calculate_growth_metrics(p_curr_clicks, p_prev_clicks)

        i_diff = p_curr_imp - p_prev_imp
        i_growth_pct, i_growth_status = calculate_growth_metrics(p_curr_imp, p_prev_imp)

        ctr_diff = round(curr_ctr - prev_ctr, 2)
        pos_diff = round(curr_pos - prev_pos, 2)

        if pos_diff < -0.3:
            pos_status = "IMPROVED"
        elif pos_diff > 0.3:
            pos_status = "DECLINED"
        else:
            pos_status = "STABLE"

        # Landing page daily trends
        page_trends: List[RelativeDailyTrendPoint] = []
        for r in relative_offsets:
            c_date = curr_date_by_offset[r]
            p_date = prev_date_by_offset.get(r)
            
            c_avail = is_curr_date_available(c_date) and country_data_available
            p_avail = (p_date is not None) and is_prev_date_available(p_date) and country_data_available

            u_c_clicks = curr_page_date_map.get((u, c_date), {}).get("clicks", 0) if c_avail else None
            u_c_imp = curr_page_date_map.get((u, c_date), {}).get("impressions", 0) if c_avail else None
            u_c_ctr = round((u_c_clicks / u_c_imp * 100.0), 2) if (c_avail and u_c_imp and u_c_imp > 0) else (0.0 if c_avail else None)
            u_c_pos = round(curr_page_date_map.get((u, c_date), {}).get("position", 0.0), 2) if c_avail else None

            u_p_clicks = prev_page_date_map.get((u, p_date), {}).get("clicks", 0) if p_avail else None
            u_p_imp = prev_page_date_map.get((u, p_date), {}).get("impressions", 0) if p_avail else None
            u_p_ctr = round((u_p_clicks / u_p_imp * 100.0), 2) if (p_avail and u_p_imp and u_p_imp > 0) else (0.0 if p_avail else None)
            u_p_pos = round(prev_page_date_map.get((u, p_date), {}).get("position", 0.0), 2) if p_avail else None

            page_trends.append(RelativeDailyTrendPoint(
                relative_day=r,
                current_date=c_date,
                previous_date=p_date,
                is_current_available=c_avail,
                is_previous_available=p_avail,
                current_clicks=u_c_clicks,
                previous_clicks=u_p_clicks,
                current_impressions=u_c_imp,
                previous_impressions=u_p_imp,
                current_ctr=u_c_ctr,
                previous_ctr=u_p_ctr,
                current_position=u_c_pos,
                previous_position=u_p_pos
            ))

        landing_pages.append(FestivalPageComparison(
            page_url=page_model.full_url,
            normalized_url=u,
            page_title=page_model.page_title,
            subcategory_id=page_model.subcategory_id,
            subcategory_name=subcat_name,
            priority=page_model.priority,
            current_clicks=p_curr_clicks,
            previous_clicks=p_prev_clicks,
            click_growth_pct=c_growth_pct,
            click_growth_status=c_growth_status,
            current_impressions=p_curr_imp,
            previous_impressions=p_prev_imp,
            impression_growth_pct=i_growth_pct,
            impression_growth_status=i_growth_status,
            current_ctr=curr_ctr,
            previous_ctr=prev_ctr,
            ctr_diff=ctr_diff,
            current_position=curr_pos,
            previous_position=prev_pos,
            position_diff=pos_diff,
            position_status=pos_status,
            daily_trends=page_trends
        ))

    # 3. Overall Festival YoY Summary (Aggregated across compared_offsets)
    tot_curr_clicks = sum(lp.current_clicks for lp in landing_pages)
    tot_prev_clicks = sum(lp.previous_clicks for lp in landing_pages)
    tot_curr_imp = sum(lp.current_impressions for lp in landing_pages)
    tot_prev_imp = sum(lp.previous_impressions for lp in landing_pages)

    tot_curr_pos_sum = sum(lp.current_position * lp.current_impressions for lp in landing_pages)
    tot_prev_pos_sum = sum(lp.previous_position * lp.previous_impressions for lp in landing_pages)

    sum_curr_ctr = round((tot_curr_clicks / tot_curr_imp * 100.0), 2) if tot_curr_imp > 0 else 0.0
    sum_curr_pos = round((tot_curr_pos_sum / tot_curr_imp), 2) if tot_curr_imp > 0 else 0.0

    sum_prev_ctr = round((tot_prev_clicks / tot_prev_imp * 100.0), 2) if tot_prev_imp > 0 else 0.0
    sum_prev_pos = round((tot_prev_pos_sum / tot_prev_imp), 2) if tot_prev_imp > 0 else 0.0

    click_diff = tot_curr_clicks - tot_prev_clicks
    click_growth_pct, click_growth_status = calculate_growth_metrics(tot_curr_clicks, tot_prev_clicks)

    imp_diff = tot_curr_imp - tot_prev_imp
    imp_growth_pct, imp_growth_status = calculate_growth_metrics(tot_curr_imp, tot_prev_imp)

    ctr_diff = round(sum_curr_ctr - sum_prev_ctr, 2)
    pos_diff = round(sum_curr_pos - sum_prev_pos, 2)

    if pos_diff < -0.3:
        overall_pos_status = "IMPROVED"
    elif pos_diff > 0.3:
        overall_pos_status = "DECLINED"
    else:
        overall_pos_status = "STABLE"

    # Contextual note for incomplete or missing data
    note = None
    if not country_data_available:
        note = f"Country-level breakdown for '{searcher_country_label}' is not available in historical records. Aggregate worldwide metrics are available."
    elif season_status == "SEASON_TO_DATE":
        note = f"Season in progress: Comparing {len(compared_offsets)} equivalent available days (Day {relative_offsets[0]} to Day {compared_offsets[-1]} relative to festival date) for accurate apples-to-apples performance."
    elif season_status == "DATA_UNAVAILABLE":
        note = "No Google Search Console data is currently available for the requested festival season window."
    elif not prev_yd:
        note = f"Previous year ({previous_year}) date edition is not configured. Showing current season data."

    summary = FestivalYoYSummary(
        current_year=current_year,
        previous_year=previous_year,
        season_status=season_status,
        searcher_country=norm_searcher_country,
        searcher_country_label=searcher_country_label,
        country_data_available=country_data_available,
        relative_window_start_day=relative_offsets[0],
        relative_window_end_day=relative_offsets[-1],
        total_window_days=total_window_days,
        compared_days_count=len(compared_offsets),
        current_period=FestivalMetricPeriod(
            clicks=tot_curr_clicks,
            impressions=tot_curr_imp,
            ctr=sum_curr_ctr,
            position=sum_curr_pos
        ),
        previous_period=FestivalMetricPeriod(
            clicks=tot_prev_clicks,
            impressions=tot_prev_imp,
            ctr=sum_prev_ctr,
            position=sum_prev_pos
        ),
        click_diff=click_diff,
        click_growth_pct=click_growth_pct,
        click_growth_status=click_growth_status,
        impression_diff=imp_diff,
        impression_growth_pct=imp_growth_pct,
        impression_growth_status=imp_growth_status,
        ctr_diff=ctr_diff,
        position_diff=pos_diff,
        position_status=overall_pos_status,
        note=note
    )

    return FestivalSeasonComparisonResponse(
        festival_id=festival.id,
        festival_name=festival.name,
        festival_slug=festival.slug,
        festival_country_code=festival.country_code,
        current_year=current_year,
        previous_year=previous_year,
        current_start_date=curr_start_date,
        previous_start_date=prev_start_date,
        summary=summary,
        landing_pages=landing_pages,
        relative_trends=relative_trends
    )
