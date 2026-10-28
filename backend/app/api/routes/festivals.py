from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import User, UserRole
from backend.app.schemas.festival_schemas import (
    FestivalCreate, FestivalUpdate, FestivalOut, FestivalDetailOut,
    FestivalYearDateCreate, FestivalYearDateUpdate, FestivalYearDateOut,
    FestivalDateApprovalRequest, SuggestedFestivalOut, ApplySuggestionsRequest,
    ApplySuggestionsResponse, FestivalSubcategoryCreate, FestivalSubcategoryOut,
    FestivalPageCreate, FestivalPageOut, FestivalSeasonComparisonResponse,
    FestivalPageComparison, RelativeDailyTrendPoint, AvailableHistoricalRangeResponse,
    FestivalTaskCreate, FestivalTaskUpdate, FestivalTaskStatusUpdate, FestivalTaskOut
)
from backend.app.api.deps import (
    get_current_user, require_manager, require_team_leader_or_manager
)
from backend.app.services.festival_service import (
    list_festivals as service_list_festivals,
    get_festival_by_id,
    create_festival as service_create_festival,
    update_festival as service_update_festival,
    delete_festival as service_delete_festival,
    add_festival_year_date,
    update_festival_year_date,
    approve_festival_year_date,
    get_festival_suggestions,
    apply_festival_suggestions,
    create_festival_subcategory,
    map_festival_landing_page,
    list_festival_landing_pages,
    delete_festival_landing_page,
    create_festival_task,
    list_festival_tasks,
    update_festival_task,
    update_festival_task_status,
    delete_festival_task,
    list_overdue_tasks,
    list_all_tasks as service_list_all_tasks
)
from backend.app.services.festival_analytics_service import (
    compare_festival_seasons,
    get_festival_available_range
)
from backend.app.services.festival_calendar_provider import calendar_provider

router = APIRouter(prefix="/festivals", tags=["Festivals"])

def format_task_out(task) -> FestivalTaskOut:
    """Helper to populate user and page metadata on task response."""
    return FestivalTaskOut(
        id=task.id,
        festival_id=task.festival_id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        milestone_stage=task.milestone_stage,
        status=task.status,
        due_date=task.due_date,
        landing_page_id=task.landing_page_id,
        festival_year_date_id=task.festival_year_date_id,
        assigned_user_id=task.assigned_user_id,
        assigned_user_name=task.assigned_user.full_name if task.assigned_user else None,
        assigned_user_email=task.assigned_user.email if task.assigned_user else None,
        landing_page_url=task.landing_page.full_url if task.landing_page else None,
        completion_date=task.completion_date,
        completed_by_name=task.completed_by_user.full_name if task.completed_by_user else None,
        created_at=task.created_at,
        updated_at=task.updated_at
    )

def format_festival_out(fest, target_year: Optional[int] = None) -> FestivalOut:
    """Helper to populate upcoming edition dates and counts for list view."""
    latest_yd = None
    if target_year:
        latest_yd = next((yd for yd in fest.year_dates if yd.year == target_year), None)
    if not latest_yd:
        sorted_dates = sorted(fest.year_dates, key=lambda yd: yd.year, reverse=True)
        latest_yd = sorted_dates[0] if sorted_dates else None

    # Calculate task completion percentage
    total_tasks = len(fest.tasks)
    completed_tasks = sum(1 for t in fest.tasks if t.status == "COMPLETED")
    pct = (completed_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0

    return FestivalOut(
        id=fest.id,
        name=fest.name,
        slug=fest.slug,
        country_code=fest.country_code,
        region=fest.region,
        category_group=fest.category_group,
        description=fest.description,
        assigned_leader_id=fest.assigned_leader_id,
        assigned_leader_name=fest.assigned_leader.full_name if fest.assigned_leader else "Unassigned",
        assigned_leader_email=fest.assigned_leader.email if fest.assigned_leader else None,
        is_active=fest.is_active,
        upcoming_edition_year=latest_yd.year if latest_yd else None,
        upcoming_start_date=latest_yd.start_date if latest_yd else None,
        upcoming_end_date=latest_yd.end_date if latest_yd else None,
        date_status=latest_yd.date_status if latest_yd else None,
        approval_status=latest_yd.approval_status if latest_yd else None,
        page_count=len(fest.pages),
        task_completion_pct=round(pct, 1),
        created_at=fest.created_at,
        updated_at=fest.updated_at
    )

@router.get("", response_model=List[FestivalOut])
def list_festivals(
    country_code: Optional[str] = Query(None, description="Filter by country (e.g. IN, US, UK, CA, AU, AE)"),
    region: Optional[str] = Query(None, description="Filter by region keyword"),
    assigned_leader_id: Optional[int] = Query(None, description="Filter by assigned team leader ID"),
    search: Optional[str] = Query(None, description="Search festival name or slug"),
    year: Optional[int] = Query(None, description="Filter festivals active in specified year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    List festivals with role-based access:
    - Managers see all festivals matching filters.
    - Team Leaders ONLY see festivals assigned to them.
    """
    festivals = service_list_festivals(
        db=db,
        current_user=current_user,
        country_code=country_code,
        region=region,
        assigned_leader_id=assigned_leader_id,
        search=search,
        year=year
    )
    return [format_festival_out(f, target_year=year) for f in festivals]

@router.get("/countries")
def get_supported_countries(
    current_user: User = Depends(require_team_leader_or_manager)
):
    """List supported countries for festival calendars and automatic suggestions."""
    return calendar_provider.get_supported_countries()

@router.get("/suggestions", response_model=List[SuggestedFestivalOut])
def preview_suggestions(
    country_code: str = Query(..., description="Country code (e.g. IN, US, GB, CA, AU, AE)"),
    year: int = Query(..., description="Target calendar year (e.g. 2025, 2026)"),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Preview automatic festival suggestions for a country and year.
    All suggestions start with approval_status='PENDING'.
    Dates with astronomical uncertainty are explicitly marked 'UNVERIFIED' or 'ESTIMATED'.
    """
    suggestions = get_festival_suggestions(country_code, year)
    return [
        SuggestedFestivalOut(
            name=s.name,
            slug=s.slug,
            country_code=s.country_code,
            region=s.region,
            category_group=s.category_group,
            calculation_type=s.calculation_type,
            year=s.year,
            start_date=s.start_date,
            end_date=s.end_date,
            prep_start_date=s.prep_start_date,
            prep_deadline_date=s.prep_deadline_date,
            season_comparison_start=s.season_comparison_start,
            season_comparison_end=s.season_comparison_end,
            date_status=s.date_status,
            approval_status=s.approval_status,
            description=s.description,
            notes=s.notes
        )
        for s in suggestions
    ]

@router.post("/suggestions/apply", response_model=ApplySuggestionsResponse)
def apply_suggestions(
    req: ApplySuggestionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Import suggested festivals into the database.
    - Added festival dates are saved with approval_status='PENDING'.
    - Dates are NOT automatically approved.
    """
    res = apply_festival_suggestions(
        db=db,
        country_code=req.country_code,
        year=req.year,
        selected_slugs=req.selected_slugs,
        current_user=current_user
    )
    return ApplySuggestionsResponse(
        status=res["status"],
        created_festivals=res["created_festivals"],
        created_year_dates=res["created_year_dates"],
        skipped_existing=res["skipped_existing"]
    )

@router.post("", response_model=FestivalOut)
def create_custom_festival(
    fest_in: FestivalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Create a custom festival.
    - Managers can assign to any active Team Leader.
    - Team leaders can only create festivals assigned strictly to themselves.
    """
    fest = service_create_festival(db, fest_in, current_user)
    return format_festival_out(fest)

@router.get("/tasks/overdue", response_model=List[FestivalTaskOut])
def get_overdue_tasks(
    festival_id: Optional[int] = Query(None, description="Optional festival filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    List overdue preparation tasks:
    - Managers view all overdue tasks across all festivals.
    - Team Leaders view only overdue tasks on festivals assigned to them or tasks assigned to them.
    """
    tasks = list_overdue_tasks(db, current_user, festival_id)
    return [format_task_out(t) for t in tasks]

@router.get("/tasks", response_model=List[FestivalTaskOut])
def get_all_tasks(
    festival_id: Optional[int] = Query(None, description="Optional festival filter"),
    status: Optional[str] = Query(None, description="Optional task status filter"),
    milestone_stage: Optional[str] = Query(None, description="Optional milestone stage filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    List preparation tasks across all festivals:
    - Managers view all tasks.
    - Team Leaders view tasks on festivals assigned to them or assigned to them directly.
    """
    tasks = service_list_all_tasks(db, current_user, festival_id, status, milestone_stage)
    return [format_task_out(t) for t in tasks]

@router.get("/{festival_id}", response_model=FestivalDetailOut)
def get_festival_detail(
    festival_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Get detailed festival information including year dates, subcategories, pages, and tasks.
    Enforces cross-leader permission barrier.
    """
    fest = get_festival_by_id(db, festival_id, current_user)
    base_out = format_festival_out(fest)

    return FestivalDetailOut(
        **base_out.model_dump(),
        year_dates=[FestivalYearDateOut.model_validate(yd) for yd in fest.year_dates],
        subcategories=fest.subcategories,
        pages=fest.pages,
        tasks=fest.tasks
    )

@router.put("/{festival_id}", response_model=FestivalOut)
def update_festival(
    festival_id: int,
    fest_in: FestivalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Update festival details.
    - Managers can update all fields including country, slug, and leader assignment.
    - Team Leaders can only update description for festivals assigned to them.
    """
    fest = service_update_festival(db, festival_id, fest_in, current_user)
    return format_festival_out(fest)

@router.delete("/{festival_id}")
def delete_festival(
    festival_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager-only: Delete festival and its associated dates and tasks."""
    return service_delete_festival(db, festival_id, current_user)

@router.post("/{festival_id}/years", response_model=FestivalYearDateOut)
def add_year_edition(
    festival_id: int,
    yd_in: FestivalYearDateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Add a year edition for a festival (e.g. Diwali in 2026).
    Dates default to UNVERIFIED and PENDING approval.
    """
    yd = add_festival_year_date(db, festival_id, yd_in, current_user)
    return FestivalYearDateOut.model_validate(yd)

@router.put("/{festival_id}/years/{year}", response_model=FestivalYearDateOut)
def update_year_edition(
    festival_id: int,
    year: int,
    yd_in: FestivalYearDateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Update year-specific dates, preparation milestones, or comparison windows."""
    yd = update_festival_year_date(db, festival_id, year, yd_in, current_user)
    return FestivalYearDateOut.model_validate(yd)

@router.put("/{festival_id}/years/{year}/approve", response_model=FestivalYearDateOut)
def approve_date_edition(
    festival_id: int,
    year: int,
    approval_in: FestivalDateApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Manager-only: Formally approve or reject festival calendar dates.
    Sets date_status='CONFIRMED', records approved_by_user_id and timestamp.
    Team Leaders are rejected with 403 Forbidden.
    """
    fest = get_festival_by_id(db, festival_id, current_user)
    yd = next((y for y in fest.year_dates if y.year == year), None)
    if not yd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Date record for year {year} not found for festival '{fest.name}'."
        )

    updated_yd = approve_festival_year_date(
        db=db,
        year_date=yd,
        current_user=current_user,
        approval_status=approval_in.approval_status,
        notes=approval_in.notes
    )
    return FestivalYearDateOut.model_validate(updated_yd)

# ----------------- SUBCATEGORIES & LANDING PAGES -----------------

@router.post("/{festival_id}/subcategories", response_model=FestivalSubcategoryOut)
def create_subcategory(
    festival_id: int,
    subcat_in: FestivalSubcategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Create a subcategory under a festival (e.g. Diwali Invitation Templates)."""
    subcat = create_festival_subcategory(db, festival_id, subcat_in, current_user)
    return FestivalSubcategoryOut.model_validate(subcat)

@router.get("/{festival_id}/pages", response_model=List[FestivalPageOut])
def get_festival_pages(
    festival_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """List mapped landing pages for a festival."""
    pages = list_festival_landing_pages(db, festival_id, current_user)
    return [FestivalPageOut.model_validate(p) for p in pages]

@router.post("/{festival_id}/pages", response_model=FestivalPageOut)
def map_page(
    festival_id: int,
    page_in: FestivalPageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Map a landing page URL to a festival (deduplicating URLs)."""
    page = map_festival_landing_page(db, festival_id, page_in, current_user)
    return FestivalPageOut.model_validate(page)

@router.delete("/{festival_id}/pages/{page_id}")
def delete_page(
    festival_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Delete a mapped festival landing page."""
    delete_festival_landing_page(db, festival_id, page_id, current_user)
    return {"status": "SUCCESS", "message": "Landing page unmapped from festival."}

# ----------------- YEAR-OVER-YEAR ANALYTICS ENDPOINTS -----------------

@router.get("/{festival_id}/analytics/comparison", response_model=FestivalSeasonComparisonResponse)
def get_festival_yoy_comparison(
    festival_id: int,
    current_year: int = Query(..., description="Target current festival edition year (e.g. 2026)"),
    previous_year: Optional[int] = Query(None, description="Previous comparison festival edition year (defaults to current_year - 1)"),
    searcher_country: Optional[str] = Query(None, description="Searcher country code (e.g. IN, US, GB) or None/ALL for Worldwide"),
    relative_days_before: int = Query(30, ge=1, le=180, description="Days before festival start date"),
    relative_days_after: int = Query(5, ge=0, le=90, description="Days after festival start date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Year-over-Year Google Search Console performance comparison for a festival.
    - Anchored on relative days (e.g. Day -30 to Day +5)
    - Apples-to-apples comparison on incomplete seasons
    - Zero impression & missing data differentiation
    - URL deduplication across landing pages
    - Country-level filtering via additive storage
    - Team Leader RBAC authorization enforcement
    """
    return compare_festival_seasons(
        db=db,
        festival_id=festival_id,
        current_year=current_year,
        previous_year=previous_year,
        searcher_country=searcher_country,
        relative_days_before=relative_days_before,
        relative_days_after=relative_days_after,
        current_user=current_user
    )

@router.get("/{festival_id}/analytics/pages", response_model=List[FestivalPageComparison])
def get_festival_pages_comparison(
    festival_id: int,
    current_year: int = Query(..., description="Target current festival edition year (e.g. 2026)"),
    previous_year: Optional[int] = Query(None, description="Previous comparison festival edition year"),
    searcher_country: Optional[str] = Query(None, description="Searcher country code or None/ALL for Worldwide"),
    relative_days_before: int = Query(30, ge=1, le=180),
    relative_days_after: int = Query(5, ge=0, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """URL-level Year-over-Year landing page comparison for a festival."""
    res = compare_festival_seasons(
        db=db,
        festival_id=festival_id,
        current_year=current_year,
        previous_year=previous_year,
        searcher_country=searcher_country,
        relative_days_before=relative_days_before,
        relative_days_after=relative_days_after,
        current_user=current_user
    )
    return res.landing_pages

@router.get("/{festival_id}/analytics/trends", response_model=List[RelativeDailyTrendPoint])
def get_festival_trends(
    festival_id: int,
    current_year: int = Query(..., description="Target current festival edition year (e.g. 2026)"),
    previous_year: Optional[int] = Query(None, description="Previous comparison festival edition year"),
    searcher_country: Optional[str] = Query(None, description="Searcher country code or None/ALL for Worldwide"),
    relative_days_before: int = Query(30, ge=1, le=180),
    relative_days_after: int = Query(5, ge=0, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Relative-day trend series (Day -30 to Day +5) for festival season visualization."""
    res = compare_festival_seasons(
        db=db,
        festival_id=festival_id,
        current_year=current_year,
        previous_year=previous_year,
        searcher_country=searcher_country,
        relative_days_before=relative_days_before,
        relative_days_after=relative_days_after,
        current_user=current_user
    )
    return res.relative_trends

@router.get("/{festival_id}/analytics/available-ranges", response_model=AvailableHistoricalRangeResponse)
def get_historical_ranges(
    festival_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Retrieve available historical date ranges, configured years, and supported searcher countries."""
    return get_festival_available_range(db, festival_id, current_user)

# ----------------- PREPARATION TASKS ENDPOINTS -----------------

@router.post("/{festival_id}/tasks", response_model=FestivalTaskOut)
def create_task(
    festival_id: int,
    task_in: FestivalTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Create a preparation task for a festival."""
    task = create_festival_task(db, festival_id, task_in, current_user)
    return format_task_out(task)

@router.get("/{festival_id}/tasks", response_model=List[FestivalTaskOut])
def get_festival_tasks(
    festival_id: int,
    status: Optional[str] = Query(None, description="Filter by task status"),
    milestone_stage: Optional[str] = Query(None, description="Filter by milestone stage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """List tasks under a festival."""
    tasks = list_festival_tasks(db, festival_id, current_user, status_filter=status, milestone_stage=milestone_stage)
    return [format_task_out(t) for t in tasks]

@router.put("/{festival_id}/tasks/{task_id}", response_model=FestivalTaskOut)
def update_task_details(
    festival_id: int,
    task_id: int,
    task_in: FestivalTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Update task details and assignments."""
    task = update_festival_task(db, festival_id, task_id, task_in, current_user)
    return format_task_out(task)

@router.put("/{festival_id}/tasks/{task_id}/status", response_model=FestivalTaskOut)
def update_task_status_endpoint(
    festival_id: int,
    task_id: int,
    status_in: FestivalTaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Update task status (e.g. NOT_STARTED -> IN_PROGRESS -> READY_FOR_REVIEW -> COMPLETED)."""
    task = update_festival_task_status(db, festival_id, task_id, status_in.status, current_user)
    return format_task_out(task)

@router.delete("/{festival_id}/tasks/{task_id}")
def delete_task(
    festival_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """Delete a preparation task."""
    delete_festival_task(db, festival_id, task_id, current_user)
    return {"status": "SUCCESS", "message": "Festival task deleted."}


