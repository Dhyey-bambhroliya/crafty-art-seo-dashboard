from datetime import datetime, timezone, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import re

from backend.app.models.models import User, UserRole, Category, CategoryPage, utc_now
from backend.app.models.festival_models import (
    Festival, FestivalYearDate, FestivalSubcategory, FestivalPage,
    FestivalTask, FestivalNotification, FestivalTaskStatus,
    FestivalDateStatus, FestivalApprovalStatus
)
from backend.app.schemas.festival_schemas import (
    FestivalCreate, FestivalUpdate, FestivalYearDateCreate, FestivalYearDateUpdate,
    FestivalPageCreate, FestivalSubcategoryCreate, FestivalTaskCreate, FestivalTaskUpdate
)
from backend.app.services.festival_calendar_provider import (
    calendar_provider, SuggestedFestivalItem
)

# ----------------- PERMISSION & AUTHORIZATION GUARDS -----------------

def require_manager(current_user: User) -> None:
    """Strictly requires user to hold the MANAGER role."""
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Manager privileges required for this action."
        )

def require_manager_for_approval(current_user: User) -> None:
    """Strictly requires MANAGER role to approve or reject festival dates."""
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Only Managers can approve or reject festival dates."
        )

def check_festival_access_permission(festival: Festival, current_user: User) -> None:
    """
    Enforces Primary Festival Ownership Rule:
    - Managers can view and access all festivals across all countries.
    - Team Leaders can ONLY access festivals explicitly assigned to them.
    - Cross-leader access is strictly forbidden with HTTP 403.
    """
    if current_user.role == UserRole.MANAGER:
        return

    if festival.assigned_leader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Festival '{festival.name}' is assigned to another team leader."
        )

def check_festival_page_access_permission(festival_page: FestivalPage, current_user: User, db: Session) -> None:
    """
    Enforces Category-Landing Page Hybrid Access Rule:
    - Managers have global access to all festival landing pages.
    - Team Leaders can access a festival landing page IF:
      1) They are the assigned leader of the parent Festival, OR
      2) They are the assigned leader of the underlying Category linked via category_page_id.
    - Any attempt by a leader without festival or category ownership raises HTTP 403.
    """
    if current_user.role == UserRole.MANAGER:
        return

    # Check festival assignment
    if festival_page.festival and festival_page.festival.assigned_leader_id == current_user.id:
        return

    # Check underlying category assignment if page references an existing category page
    if festival_page.category_page_id:
        cat_page = db.query(CategoryPage).join(
            Category, CategoryPage.category_id == Category.id
        ).filter(
            CategoryPage.id == festival_page.category_page_id,
            Category.assigned_leader_id == current_user.id
        ).first()
        if cat_page:
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: You do not have permission to view or manage landing pages for this category."
    )

def check_festival_edit_permission(festival: Festival, current_user: User, updates: Optional[FestivalUpdate] = None) -> None:
    """
    Enforces modification rules:
    - Managers can edit all fields (name, country, slug, reassignment of leaders).
    - Team Leaders can only edit their own festival's description.
    - Team Leaders cannot reassign festivals to other leaders or rename core festival identifiers.
    """
    if current_user.role == UserRole.MANAGER:
        return

    if festival.assigned_leader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: You can only edit festivals assigned to you."
        )

    if updates:
        if updates.assigned_leader_id is not None and updates.assigned_leader_id != festival.assigned_leader_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Only Managers can reassign festival leadership."
            )
        if updates.country_code is not None and updates.country_code != festival.country_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Only Managers can change festival country."
            )

# ----------------- SLUG GENERATION UTILITY -----------------

def generate_slug(text: str) -> str:
    """Generate a clean URL-friendly slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")

# ----------------- FESTIVAL CORE CRUD -----------------

def list_festivals(
    db: Session,
    current_user: User,
    country_code: Optional[str] = None,
    region: Optional[str] = None,
    assigned_leader_id: Optional[int] = None,
    search: Optional[str] = None,
    year: Optional[int] = None
) -> List[Festival]:
    """
    Lists festivals with role-based filtering:
    - Managers see all festivals matching criteria.
    - Team Leaders ONLY see festivals assigned to them.
    """
    query = db.query(Festival)

    # Role enforcement
    if current_user.role == UserRole.TEAM_LEADER:
        query = query.filter(Festival.assigned_leader_id == current_user.id)
    elif assigned_leader_id is not None:
        query = query.filter(Festival.assigned_leader_id == assigned_leader_id)

    if country_code:
        c = country_code.strip().upper()
        if c == "UK":
            c = "GB"
        query = query.filter(Festival.country_code == c)

    if region:
        query = query.filter(Festival.region.ilike(f"%{region}%"))

    if search:
        query = query.filter(
            or_(
                Festival.name.ilike(f"%{search}%"),
                Festival.slug.ilike(f"%{search}%"),
                Festival.category_group.ilike(f"%{search}%")
            )
        )

    festivals = query.order_by(Festival.name).all()

    # If specific year filter is requested, filter or sort by that year
    # Include festivals that have dates for that year OR festivals with no year dates yet
    if year:
        festivals = [f for f in festivals if not f.year_dates or any(yd.year == year for yd in f.year_dates)]

    return festivals

def get_festival_by_id(db: Session, festival_id: int, current_user: User) -> Festival:
    """Fetch single festival and enforce access permission."""
    fest = db.query(Festival).filter(Festival.id == festival_id).first()
    if not fest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Festival with ID {festival_id} not found."
        )
    check_festival_access_permission(fest, current_user)
    return fest

def create_festival(db: Session, fest_in: FestivalCreate, current_user: User) -> Festival:
    """
    Managers create festivals.
    If Team Leader creates, it is automatically assigned strictly to themselves.
    """
    if current_user.role == UserRole.MANAGER:
        assigned_id = fest_in.assigned_leader_id
    else:
        assigned_id = current_user.id

    if assigned_id is not None:
        leader = db.query(User).filter(User.id == assigned_id, User.is_active == True).first()
        if not leader:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assigned leader with ID {assigned_id} does not exist or is inactive."
            )

    norm_country = (fest_in.country_code or "IN").strip().upper()
    if norm_country == "UK":
        norm_country = "GB"

    slug = fest_in.slug or generate_slug(fest_in.name)

    # Check for existing festival slug
    existing = db.query(Festival).filter(Festival.slug == slug).first()
    if existing:
        # If the same slug exists for another country, disambiguate with country code
        if existing.country_code != norm_country and not fest_in.slug:
            candidate_slug = f"{slug}-{norm_country.lower()}"
            if not db.query(Festival).filter(Festival.slug == candidate_slug).first():
                slug = candidate_slug
                existing = None
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A festival with slug '{slug}' already exists."
            )

    festival = Festival(
        name=fest_in.name.strip(),
        slug=slug,
        country_code=norm_country,
        region=fest_in.region,
        category_group=fest_in.category_group or "Cultural",
        description=fest_in.description,
        assigned_leader_id=assigned_id,
        is_active=fest_in.is_active
    )
    db.add(festival)
    db.commit()
    db.refresh(festival)

    # Initial year date if provided
    if fest_in.initial_year_date:
        yd_in = fest_in.initial_year_date
        year_date = FestivalYearDate(
            festival_id=festival.id,
            year=yd_in.year,
            start_date=yd_in.start_date,
            end_date=yd_in.end_date,
            prep_start_date=yd_in.prep_start_date or (yd_in.start_date - timedelta(days=45)),
            prep_deadline_date=yd_in.prep_deadline_date or (yd_in.start_date - timedelta(days=15)),
            season_comparison_start=yd_in.season_comparison_start or (yd_in.start_date - timedelta(days=45)),
            season_comparison_end=yd_in.season_comparison_end or (yd_in.end_date + timedelta(days=2)),
            date_status=yd_in.date_status or FestivalDateStatus.UNVERIFIED,
            approval_status=FestivalApprovalStatus.PENDING,
            notes=yd_in.notes
        )
        db.add(year_date)
        db.commit()
        db.refresh(festival)

    return festival

def update_festival(db: Session, festival_id: int, fest_in: FestivalUpdate, current_user: User) -> Festival:
    """Updates festival details honoring permission boundaries."""
    festival = get_festival_by_id(db, festival_id, current_user)
    check_festival_edit_permission(festival, current_user, fest_in)

    if fest_in.name is not None:
        festival.name = fest_in.name.strip()
    if fest_in.slug is not None:
        existing = db.query(Festival).filter(Festival.slug == fest_in.slug, Festival.id != festival_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slug '{fest_in.slug}' is already in use.")
        festival.slug = fest_in.slug
    if fest_in.country_code is not None:
        c = fest_in.country_code.strip().upper()
        festival.country_code = "GB" if c == "UK" else c
    if fest_in.region is not None:
        festival.region = fest_in.region
    if fest_in.category_group is not None:
        festival.category_group = fest_in.category_group
    if fest_in.description is not None:
        festival.description = fest_in.description
    if fest_in.is_active is not None:
        festival.is_active = fest_in.is_active
    if fest_in.assigned_leader_id is not None and current_user.role == UserRole.MANAGER:
        festival.assigned_leader_id = fest_in.assigned_leader_id

    db.commit()
    db.refresh(festival)
    return festival

def delete_festival(db: Session, festival_id: int, current_user: User) -> Dict[str, str]:
    """Managers alone can delete festivals."""
    require_manager(current_user)
    fest = db.query(Festival).filter(Festival.id == festival_id).first()
    if not fest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival not found.")
    name = fest.name
    db.delete(fest)
    db.commit()
    return {"message": f"Festival '{name}' and associated dates/tasks deleted successfully."}

# ----------------- YEAR-SPECIFIC FESTIVAL DATES -----------------

def add_festival_year_date(
    db: Session,
    festival_id: int,
    yd_in: FestivalYearDateCreate,
    current_user: User
) -> FestivalYearDate:
    """Add a specific year edition for a festival."""
    festival = get_festival_by_id(db, festival_id, current_user)

    # Check for existing year record
    existing = db.query(FestivalYearDate).filter(
        FestivalYearDate.festival_id == festival_id,
        FestivalYearDate.year == yd_in.year
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Festival '{festival.name}' already has date records configured for year {yd_in.year}."
        )

    prep_start = yd_in.prep_start_date or (yd_in.start_date - timedelta(days=45))
    prep_deadline = yd_in.prep_deadline_date or (yd_in.start_date - timedelta(days=15))
    comp_start = yd_in.season_comparison_start or prep_start
    comp_end = yd_in.season_comparison_end or (yd_in.end_date + timedelta(days=2))

    # Any new dates added start as PENDING approval and UNVERIFIED
    year_date = FestivalYearDate(
        festival_id=festival.id,
        year=yd_in.year,
        start_date=yd_in.start_date,
        end_date=yd_in.end_date,
        prep_start_date=prep_start,
        prep_deadline_date=prep_deadline,
        season_comparison_start=comp_start,
        season_comparison_end=comp_end,
        date_status=yd_in.date_status or FestivalDateStatus.UNVERIFIED,
        approval_status=FestivalApprovalStatus.PENDING,
        notes=yd_in.notes
    )
    db.add(year_date)
    db.commit()
    db.refresh(year_date)
    return year_date

def update_festival_year_date(
    db: Session,
    festival_id: int,
    year: int,
    yd_in: FestivalYearDateUpdate,
    current_user: User
) -> FestivalYearDate:
    """Updates dates, deadlines, or comparison windows for a festival edition."""
    festival = get_festival_by_id(db, festival_id, current_user)
    year_date = db.query(FestivalYearDate).filter(
        FestivalYearDate.festival_id == festival_id,
        FestivalYearDate.year == year
    ).first()
    if not year_date:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Date records for year {year} not found for festival '{festival.name}'."
        )

    # Date approvals must use the approve_festival_date endpoint
    if yd_in.approval_status is not None:
        require_manager_for_approval(current_user)
        year_date.approval_status = yd_in.approval_status.upper()
        if year_date.approval_status == FestivalApprovalStatus.APPROVED:
            year_date.date_status = FestivalDateStatus.CONFIRMED
            year_date.approved_by_user_id = current_user.id
            year_date.approved_at = datetime.now(timezone.utc)

    if yd_in.start_date is not None:
        year_date.start_date = yd_in.start_date
    if yd_in.end_date is not None:
        year_date.end_date = yd_in.end_date
    if yd_in.prep_start_date is not None:
        year_date.prep_start_date = yd_in.prep_start_date
    if yd_in.prep_deadline_date is not None:
        year_date.prep_deadline_date = yd_in.prep_deadline_date
    if yd_in.season_comparison_start is not None:
        year_date.season_comparison_start = yd_in.season_comparison_start
    if yd_in.season_comparison_end is not None:
        year_date.season_comparison_end = yd_in.season_comparison_end
    if yd_in.date_status is not None:
        year_date.date_status = yd_in.date_status.upper()
    if yd_in.notes is not None:
        year_date.notes = yd_in.notes

    db.commit()
    db.refresh(year_date)
    return year_date

def approve_festival_year_date(
    db: Session,
    year_date: FestivalYearDate,
    current_user: User,
    approval_status: str,
    notes: Optional[str] = None
) -> FestivalYearDate:
    """
    Manager-only workflow to approve or reject a festival's year date edition.
    """
    require_manager_for_approval(current_user)

    norm_status = approval_status.upper()
    if norm_status not in [FestivalApprovalStatus.APPROVED, FestivalApprovalStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid approval status '{approval_status}'. Must be APPROVED or REJECTED."
        )

    year_date.approval_status = norm_status
    year_date.approved_by_user_id = current_user.id
    year_date.approved_at = datetime.now(timezone.utc)
    if notes:
        year_date.notes = notes

    if norm_status == FestivalApprovalStatus.APPROVED:
        year_date.date_status = FestivalDateStatus.CONFIRMED

    db.commit()
    db.refresh(year_date)
    return year_date

# ----------------- SUGGESTION ENGINE -----------------

def get_festival_suggestions(country_code: str, year: int) -> List[SuggestedFestivalItem]:
    """Generates suggested festivals for a given country and year."""
    return calendar_provider.suggest_festivals(country_code, year)

def apply_festival_suggestions(
    db: Session,
    country_code: str,
    year: int,
    selected_slugs: Optional[List[str]],
    current_user: User
) -> Dict[str, Any]:
    """
    Imports suggested festivals into the database:
    - Creates Festival if missing (assigned to current leader or unassigned).
    - Adds FestivalYearDate with date_status from registry and approval_status=PENDING.
    - Never overwrites existing customized festivals or approved dates.
    """
    suggestions = calendar_provider.suggest_festivals(country_code, year)
    if selected_slugs:
        slug_set = set(selected_slugs)
        suggestions = [s for s in suggestions if s.slug in slug_set]

    created_festivals = 0
    created_year_dates = 0
    skipped_count = 0

    assigned_id = current_user.id if current_user.role == UserRole.TEAM_LEADER else None

    for item in suggestions:
        fest = db.query(Festival).filter(Festival.slug == item.slug).first()
        if not fest:
            fest = Festival(
                name=item.name,
                slug=item.slug,
                country_code=item.country_code,
                region=item.region,
                category_group=item.category_group,
                description=item.description,
                assigned_leader_id=assigned_id,
                is_active=True
            )
            db.add(fest)
            db.commit()
            db.refresh(fest)
            created_festivals += 1

        # Check year date
        existing_yd = db.query(FestivalYearDate).filter(
            FestivalYearDate.festival_id == fest.id,
            FestivalYearDate.year == year
        ).first()

        if not existing_yd:
            yd = FestivalYearDate(
                festival_id=fest.id,
                year=year,
                start_date=item.start_date,
                end_date=item.end_date,
                prep_start_date=item.prep_start_date,
                prep_deadline_date=item.prep_deadline_date,
                season_comparison_start=item.season_comparison_start,
                season_comparison_end=item.season_comparison_end,
                date_status=item.date_status,
                approval_status=FestivalApprovalStatus.PENDING,  # Must be PENDING
                notes=item.notes
            )
            db.add(yd)
            db.commit()
            created_year_dates += 1
        else:
            skipped_count += 1

    return {
        "status": "SUCCESS",
        "created_festivals": created_festivals,
        "created_year_dates": created_year_dates,
        "skipped_existing": skipped_count
    }

# ----------------- SUBCATEGORIES & LANDING PAGES -----------------

def create_festival_subcategory(
    db: Session,
    festival_id: int,
    subcat_in: FestivalSubcategoryCreate,
    current_user: User
) -> FestivalSubcategory:
    """Create a festival subcategory (e.g. Diwali Invitation Templates)."""
    festival = get_festival_by_id(db, festival_id, current_user)
    check_festival_edit_permission(festival, current_user)

    slug = subcat_in.slug or re.sub(r'[^a-z0-9]+', '-', subcat_in.name.lower()).strip('-')

    existing = db.query(FestivalSubcategory).filter(
        FestivalSubcategory.festival_id == festival_id,
        FestivalSubcategory.slug == slug
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subcategory with slug '{slug}' already exists under festival '{festival.name}'."
        )

    subcat = FestivalSubcategory(
        festival_id=festival_id,
        name=subcat_in.name,
        slug=slug,
        description=subcat_in.description,
        target_keywords=subcat_in.target_keywords
    )
    db.add(subcat)
    db.commit()
    db.refresh(subcat)
    return subcat

def map_festival_landing_page(
    db: Session,
    festival_id: int,
    page_in: FestivalPageCreate,
    current_user: User
) -> FestivalPage:
    """
    Map a landing page to a festival.
    Enforces URL deduplication under the same festival.
    """
    from backend.app.services.metric_service import normalize_url

    festival = get_festival_by_id(db, festival_id, current_user)
    check_festival_edit_permission(festival, current_user)

    norm_url = normalize_url(page_in.full_url)
    if not norm_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL provided."
        )

    # Check duplicate under same festival
    existing = db.query(FestivalPage).filter(
        FestivalPage.festival_id == festival_id,
        FestivalPage.normalized_url == norm_url
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"URL '{page_in.full_url}' is already mapped to festival '{festival.name}'."
        )

    # Optional subcategory check
    if page_in.subcategory_id:
        sc = db.query(FestivalSubcategory).filter(
            FestivalSubcategory.id == page_in.subcategory_id,
            FestivalSubcategory.festival_id == festival_id
        ).first()
        if not sc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified subcategory does not belong to this festival."
            )

    page = FestivalPage(
        festival_id=festival_id,
        subcategory_id=page_in.subcategory_id,
        category_page_id=page_in.category_page_id,
        full_url=page_in.full_url.strip(),
        normalized_url=norm_url,
        page_title=page_in.page_title,
        priority=page_in.priority or "PRIMARY",
        status=page_in.status or "ACTIVE",
        notes=page_in.notes
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page

def list_festival_landing_pages(
    db: Session,
    festival_id: int,
    current_user: User
) -> List[FestivalPage]:
    """List all mapped landing pages for a festival."""
    festival = get_festival_by_id(db, festival_id, current_user)
    return db.query(FestivalPage).filter(FestivalPage.festival_id == festival_id).all()

def delete_festival_landing_page(
    db: Session,
    festival_id: int,
    page_id: int,
    current_user: User
) -> None:
    """Delete a mapped festival landing page."""
    festival = get_festival_by_id(db, festival_id, current_user)
    check_festival_edit_permission(festival, current_user)

    page = db.query(FestivalPage).filter(
        FestivalPage.id == page_id,
        FestivalPage.festival_id == festival_id
    ).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Festival page mapping not found."
        )
    db.delete(page)
    db.commit()

# ----------------- PREPARATION TASK MANAGEMENT -----------------

def create_festival_task(
    db: Session,
    festival_id: int,
    task_in: FestivalTaskCreate,
    current_user: User
) -> FestivalTask:
    """Create a preparation task for a festival."""
    festival = get_festival_by_id(db, festival_id, current_user)
    check_festival_edit_permission(festival, current_user)

    # Optional year_date validation
    if task_in.festival_year_date_id:
        yd = db.query(FestivalYearDate).filter(
            FestivalYearDate.id == task_in.festival_year_date_id,
            FestivalYearDate.festival_id == festival_id
        ).first()
        if not yd:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specified year date edition not found for this festival.")

    # Optional landing page validation
    if task_in.landing_page_id:
        p = db.query(FestivalPage).filter(
            FestivalPage.id == task_in.landing_page_id,
            FestivalPage.festival_id == festival_id
        ).first()
        if not p:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specified landing page does not belong to this festival.")

    task = FestivalTask(
        festival_id=festival_id,
        festival_year_date_id=task_in.festival_year_date_id,
        landing_page_id=task_in.landing_page_id,
        assigned_user_id=task_in.assigned_user_id or festival.assigned_leader_id,
        title=task_in.title.strip(),
        description=task_in.description,
        task_type=task_in.task_type or "CONTENT",
        milestone_stage=task_in.milestone_stage or "T_MINUS_30",
        status=FestivalTaskStatus.NOT_STARTED,
        due_date=task_in.due_date
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def list_festival_tasks(
    db: Session,
    festival_id: int,
    current_user: User,
    status_filter: Optional[str] = None,
    milestone_stage: Optional[str] = None
) -> List[FestivalTask]:
    """List tasks under a festival with authorization checking."""
    festival = get_festival_by_id(db, festival_id, current_user)
    query = db.query(FestivalTask).filter(FestivalTask.festival_id == festival_id)

    if status_filter:
        query = query.filter(FestivalTask.status == status_filter)
    if milestone_stage:
        query = query.filter(FestivalTask.milestone_stage == milestone_stage)

    return query.order_by(FestivalTask.due_date.asc().nulls_last()).all()

def update_festival_task(
    db: Session,
    festival_id: int,
    task_id: int,
    task_in: FestivalTaskUpdate,
    current_user: User
) -> FestivalTask:
    """Update task details and assignments."""
    festival = get_festival_by_id(db, festival_id, current_user)
    check_festival_edit_permission(festival, current_user)

    task = db.query(FestivalTask).filter(
        FestivalTask.id == task_id,
        FestivalTask.festival_id == festival_id
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival task not found.")

    if task_in.title is not None:
        task.title = task_in.title.strip()
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.task_type is not None:
        task.task_type = task_in.task_type
    if task_in.milestone_stage is not None:
        task.milestone_stage = task_in.milestone_stage
    if task_in.due_date is not None:
        task.due_date = task_in.due_date
    if task_in.landing_page_id is not None:
        task.landing_page_id = task_in.landing_page_id
    if task_in.assigned_user_id is not None:
        task.assigned_user_id = task_in.assigned_user_id
    if task_in.status is not None:
        task.status = task_in.status
        if task_in.status == FestivalTaskStatus.COMPLETED:
            task.completion_date = utc_now()
            task.completed_by_user_id = current_user.id

    db.commit()
    db.refresh(task)
    return task

def update_festival_task_status(
    db: Session,
    festival_id: int,
    task_id: int,
    new_status: str,
    current_user: User
) -> FestivalTask:
    """Update the progress status of a task."""
    festival = get_festival_by_id(db, festival_id, current_user)

    task = db.query(FestivalTask).filter(
        FestivalTask.id == task_id,
        FestivalTask.festival_id == festival_id
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival task not found.")

    # Permissions: Manager or assigned festival leader or task assigned user
    can_update = (
        current_user.role == UserRole.MANAGER or
        festival.assigned_leader_id == current_user.id or
        task.assigned_user_id == current_user.id
    )
    if not can_update:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You do not have permission to update this task.")

    valid_statuses = [
        FestivalTaskStatus.NOT_STARTED,
        FestivalTaskStatus.IN_PROGRESS,
        FestivalTaskStatus.READY_FOR_REVIEW,
        FestivalTaskStatus.COMPLETED
    ]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status. Must be one of: {valid_statuses}")

    task.status = new_status
    if new_status == FestivalTaskStatus.COMPLETED:
        task.completion_date = utc_now()
        task.completed_by_user_id = current_user.id
    else:
        task.completion_date = None
        task.completed_by_user_id = None

    db.commit()
    db.refresh(task)
    return task

def delete_festival_task(
    db: Session,
    festival_id: int,
    task_id: int,
    current_user: User
) -> None:
    """Delete a task."""
    festival = get_festival_by_id(db, festival_id, current_user)
    check_festival_edit_permission(festival, current_user)

    task = db.query(FestivalTask).filter(
        FestivalTask.id == task_id,
        FestivalTask.festival_id == festival_id
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festival task not found.")
    db.delete(task)
    db.commit()

def list_overdue_tasks(
    db: Session,
    current_user: User,
    festival_id: Optional[int] = None
) -> List[FestivalTask]:
    """List overdue tasks. Enforces role-based isolation."""
    today = date.today()
    query = (
        db.query(FestivalTask)
        .join(Festival, FestivalTask.festival_id == Festival.id)
        .filter(
            Festival.is_active == True,
            FestivalTask.status != FestivalTaskStatus.COMPLETED,
            FestivalTask.due_date != None,
            FestivalTask.due_date < today
        )
    )

    if current_user.role != UserRole.MANAGER:
        # Team Leader: only tasks on festivals assigned to them OR assigned directly to them
        query = query.filter(
            or_(
                Festival.assigned_leader_id == current_user.id,
                FestivalTask.assigned_user_id == current_user.id
            )
        )

    if festival_id:
        query = query.filter(FestivalTask.festival_id == festival_id)

    return query.order_by(FestivalTask.due_date.asc()).all()

def list_all_tasks(
    db: Session,
    current_user: User,
    festival_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    milestone_stage: Optional[str] = None
) -> List[FestivalTask]:
    """List preparation tasks across festivals with role-based access."""
    query = (
        db.query(FestivalTask)
        .join(Festival, FestivalTask.festival_id == Festival.id)
        .filter(Festival.is_active == True)
    )

    if current_user.role != UserRole.MANAGER:
        query = query.filter(
            or_(
                Festival.assigned_leader_id == current_user.id,
                FestivalTask.assigned_user_id == current_user.id
            )
        )

    if festival_id:
        query = query.filter(FestivalTask.festival_id == festival_id)
    if status_filter:
        query = query.filter(FestivalTask.status == status_filter)
    if milestone_stage:
        query = query.filter(FestivalTask.milestone_stage == milestone_stage)

    return query.order_by(FestivalTask.due_date.asc().nulls_last()).all()


