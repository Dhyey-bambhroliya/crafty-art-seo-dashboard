from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from backend.app.core.database import get_db
from backend.app.models.models import User, UserRole, Category, CategoryPage, Alert
from backend.app.schemas.schemas import (
    CategoryCreate, CategoryUpdate, CategoryOut, CategoryPageOut,
    PageAddRequest, DuplicateCheckResponse, CategorySummary, ComparisonMetrics, PeriodMetrics,
    PageBulkAddRequest, PageBulkAddResult, BulkDuplicateCheckRequest, BulkDuplicateCheckItem, BulkDuplicateCheckResponse
)
from backend.app.api.deps import (
    get_current_user, require_team_leader_or_manager, check_category_edit_permission
)
from backend.app.services.metric_service import (
    normalize_url, get_latest_data_date, get_28day_date_windows,
    get_page_aggregated_metrics, calculate_comparison_metrics, get_daily_trends
)

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=List[CategoryOut])
def list_categories(
    leader_id: Optional[int] = Query(None, description="Filter by assigned team leader ID"),
    search: Optional[str] = Query(None, description="Search category name"),
    status_filter: Optional[str] = Query(None, description="Filter by status (ACTIVE/INACTIVE)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    List all categories with leader info and page counts.
    Accessible to both Manager and Team Leader (read-only for all categories).
    """
    query = db.query(Category).outerjoin(User, Category.assigned_leader_id == User.id)

    if leader_id is not None:
        query = query.filter(Category.assigned_leader_id == leader_id)

    if search:
        query = query.filter(Category.name.ilike(f"%{search}%"))

    if status_filter:
        query = query.filter(Category.status == status_filter.upper())

    categories = query.order_by(Category.name).all()
    if not categories:
        return []

    cat_ids = [c.id for c in categories]
    # Fetch page counts in 1 aggregated query
    counts_rows = (
        db.query(CategoryPage.category_id, func.count(CategoryPage.id))
        .filter(CategoryPage.category_id.in_(cat_ids), CategoryPage.status == "ACTIVE")
        .group_by(CategoryPage.category_id)
        .all()
    )
    counts_map = dict(counts_rows)

    results = []
    for cat in categories:
        results.append(CategoryOut(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            assigned_leader_id=cat.assigned_leader_id,
            leader_name=cat.leader.full_name if cat.leader else "Unassigned",
            leader_email=cat.leader.email if cat.leader else None,
            status=cat.status,
            page_count=counts_map.get(cat.id, 0),
            created_at=cat.created_at,
            updated_at=cat.updated_at
        ))
    return results

@router.post("", response_model=CategoryOut)
def create_category(
    cat_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Create a new category.
    - Managers can assign to any active team leader.
    - Team leaders can only create categories assigned to themselves.
    """
    if current_user.role != UserRole.MANAGER:
        assigned_id = current_user.id
    else:
        assigned_id = cat_in.assigned_leader_id

    # Verify target leader exists
    leader = db.query(User).filter(User.id == assigned_id, User.is_active == True).first()
    if not leader:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assigned user with ID {assigned_id} does not exist or is inactive."
        )

    # Check for duplicate category name
    existing = db.query(Category).filter(Category.name.ilike(cat_in.name)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A category named '{cat_in.name}' already exists."
        )

    new_cat = Category(
        name=cat_in.name,
        description=cat_in.description,
        assigned_leader_id=assigned_id,
        status="ACTIVE"
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)

    return CategoryOut(
        id=new_cat.id,
        name=new_cat.name,
        description=new_cat.description,
        assigned_leader_id=new_cat.assigned_leader_id,
        leader_name=leader.full_name,
        leader_email=leader.email,
        status=new_cat.status,
        page_count=0,
        created_at=new_cat.created_at,
        updated_at=new_cat.updated_at
    )

@router.get("/{category_id}")
def get_category_details(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Detailed category view including 28-day comparison metrics, daily trends,
    top gaining and declining pages, and active alerts.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    pages = db.query(CategoryPage).filter(
        CategoryPage.category_id == category.id,
        CategoryPage.status == "ACTIVE"
    ).all()

    norm_urls = [p.normalized_url for p in pages]
    latest_date = get_latest_data_date(db)
    curr_start, curr_end, prev_start, prev_end = get_28day_date_windows(latest_date)

    curr_metrics = get_page_aggregated_metrics(db, norm_urls, curr_start, curr_end)
    prev_metrics = get_page_aggregated_metrics(db, norm_urls, prev_start, prev_end)

    # Aggregate category totals (sum clicks/impressions from uniquely mapped pages)
    curr_total_clicks = sum(m["clicks"] for m in curr_metrics.values())
    curr_total_imps = sum(m["impressions"] for m in curr_metrics.values())
    curr_pos_imp = sum(m["pos_imp_sum"] for m in curr_metrics.values())

    prev_total_clicks = sum(m["clicks"] for m in prev_metrics.values())
    prev_total_imps = sum(m["impressions"] for m in prev_metrics.values())
    prev_pos_imp = sum(m["pos_imp_sum"] for m in prev_metrics.values())

    category_comparison = calculate_comparison_metrics(
        curr_total_clicks, curr_total_imps, curr_pos_imp,
        prev_total_clicks, prev_total_imps, prev_pos_imp
    )

    # Build page breakdown
    page_breakdown = []
    for p in pages:
        c = curr_metrics.get(p.normalized_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})
        pr = prev_metrics.get(p.normalized_url, {"clicks": 0, "impressions": 0, "pos_imp_sum": 0.0})
        comp = calculate_comparison_metrics(
            c["clicks"], c["impressions"], c["pos_imp_sum"],
            pr["clicks"], pr["impressions"], pr["pos_imp_sum"]
        )
        alerts_count = db.query(Alert).filter(
            Alert.normalized_url == p.normalized_url,
            Alert.status == "PENDING"
        ).count()

        page_breakdown.append({
            "id": p.id,
            "full_url": p.full_url,
            "normalized_url": p.normalized_url,
            "status": p.status,
            "created_at": p.created_at,
            "metrics": comp,
            "active_alerts": alerts_count
        })

    # Sort pages for top decliners and top gainers
    sorted_by_decline = sorted(page_breakdown, key=lambda x: x["metrics"].click_diff)
    top_declines = [x for x in sorted_by_decline if x["metrics"].click_diff < 0][:5]
    top_improvements = [x for x in reversed(sorted_by_decline) if x["metrics"].click_diff > 0][:5]

    # Daily trends for chart
    daily_trends = get_daily_trends(db, normalized_urls=norm_urls, latest_date=latest_date)

    # Category alerts
    alerts = (
        db.query(Alert)
        .filter(Alert.category_id == category.id)
        .order_by(Alert.detection_date.desc(), Alert.id.desc())
        .limit(20)
        .all()
    )

    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "assigned_leader_id": category.assigned_leader_id,
        "leader_name": category.leader.full_name if category.leader else "Unassigned",
        "leader_email": category.leader.email if category.leader else None,
        "status": category.status,
        "page_count": len(pages),
        "created_at": category.created_at,
        "updated_at": category.updated_at,
        "comparison": category_comparison,
        "latest_data_date": str(latest_date) if latest_date else None,
        "top_declines": top_declines,
        "top_improvements": top_improvements,
        "pages": page_breakdown,
        "daily_trends": daily_trends,
        "alerts": alerts
    }

@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    cat_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Edit category details.
    - Managers can edit any category and reassign to any leader.
    - Team leaders can only edit their own category details (and CANNOT reassign to another leader).
    """
    category = check_category_edit_permission(category_id, current_user, db)

    if cat_in.name is not None and cat_in.name != category.name:
        existing = db.query(Category).filter(Category.name.ilike(cat_in.name), Category.id != category_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A category with this name already exists.")
        category.name = cat_in.name

    if cat_in.description is not None:
        category.description = cat_in.description

    if cat_in.status is not None:
        category.status = cat_in.status.upper()

    # Reassignment check
    if cat_in.assigned_leader_id is not None and cat_in.assigned_leader_id != category.assigned_leader_id:
        if current_user.role != UserRole.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Managers can reassign category ownership to another leader."
            )
        target_leader = db.query(User).filter(User.id == cat_in.assigned_leader_id, User.is_active == True).first()
        if not target_leader:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned leader does not exist or is inactive.")
        category.assigned_leader_id = cat_in.assigned_leader_id

    db.commit()
    db.refresh(category)

    page_count = db.query(CategoryPage).filter(CategoryPage.category_id == category.id, CategoryPage.status == "ACTIVE").count()
    return CategoryOut(
        id=category.id,
        name=category.name,
        description=category.description,
        assigned_leader_id=category.assigned_leader_id,
        leader_name=category.leader.full_name if category.leader else "Unassigned",
        leader_email=category.leader.email if category.leader else None,
        status=category.status,
        page_count=page_count,
        created_at=category.created_at,
        updated_at=category.updated_at
    )

@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Delete or archive a category.
    - Managers can delete any category.
    - Team leaders can only delete categories they own.
    """
    category = check_category_edit_permission(category_id, current_user, db)
    
    from backend.app.models.models import Alert
    # Clean up any alerts referencing this category
    db.query(Alert).filter(Alert.category_id == category_id).delete()
    # Clean up pages mapped to this category
    db.query(CategoryPage).filter(CategoryPage.category_id == category_id).delete()
    
    cat_name = category.name
    db.delete(category)
    db.commit()
    return {"message": f"Category '{cat_name}' deleted successfully."}

# ----------------- CATEGORY PAGES MANAGEMENT -----------------

@router.get("/{category_id}/pages", response_model=List[CategoryPageOut])
def list_category_pages(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """List all pages mapped to a category."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    pages = db.query(CategoryPage).filter(CategoryPage.category_id == category_id).all()
    return [
        CategoryPageOut(
            id=p.id,
            category_id=p.category_id,
            category_name=category.name,
            full_url=p.full_url,
            normalized_url=p.normalized_url,
            status=p.status,
            created_at=p.created_at
        )
        for p in pages
    ]

@router.post("/{category_id}/pages/check-duplicate", response_model=DuplicateCheckResponse)
def check_url_mapping(
    category_id: int,
    request: PageAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Checks URL for duplicate mapping before adding:
    - Flags if already inside this category
    - Warns if mapped to other categories (which causes double-counting in SEO reporting)
    """
    norm_url = normalize_url(request.full_url)
    
    # Check if duplicate in same category
    in_curr = db.query(CategoryPage).filter(
        CategoryPage.category_id == category_id,
        CategoryPage.normalized_url == norm_url
    ).first()

    # Check if mapped to other categories
    other_mappings = (
        db.query(CategoryPage, Category)
        .join(Category, CategoryPage.category_id == Category.id)
        .filter(CategoryPage.category_id != category_id, CategoryPage.normalized_url == norm_url)
        .all()
    )
    other_names = [item.Category.name for item in other_mappings]

    warning = None
    if other_names:
        warning = f"Notice: This URL is already mapped to: {', '.join(other_names)}. Mapping to multiple categories may cause double counting in category aggregate totals."

    return DuplicateCheckResponse(
        normalized_url=norm_url,
        is_duplicate_in_category=in_curr is not None,
        is_mapped_to_other_categories=len(other_names) > 0,
        other_category_names=other_names,
        warning_message=warning
    )

@router.post("/{category_id}/pages", response_model=CategoryPageOut)
def add_page_to_category(
    category_id: int,
    page_in: PageAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Add a page URL to a category.
    - Managers can add pages to any category.
    - Team leaders can only add pages to categories they own.
    - Enforces uniqueness within the category.
    """
    category = check_category_edit_permission(category_id, current_user, db)
    norm_url = normalize_url(page_in.full_url)

    # Check duplicate in this category
    existing = db.query(CategoryPage).filter(
        CategoryPage.category_id == category_id,
        CategoryPage.normalized_url == norm_url
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This URL is already mapped to '{category.name}'."
        )

    new_page = CategoryPage(
        category_id=category_id,
        full_url=page_in.full_url.strip(),
        normalized_url=norm_url,
        status="ACTIVE"
    )
    db.add(new_page)
    db.commit()
    db.refresh(new_page)

    return CategoryPageOut(
        id=new_page.id,
        category_id=new_page.category_id,
        category_name=category.name,
        full_url=new_page.full_url,
        normalized_url=new_page.normalized_url,
        status=new_page.status,
        created_at=new_page.created_at
    )

@router.delete("/{category_id}/pages/{page_id}")
def remove_page_from_category(
    category_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Remove a page from a category.
    - Managers can remove from any category.
    - Team leaders can only remove pages from categories they own.
    """
    check_category_edit_permission(category_id, current_user, db)

    page = db.query(CategoryPage).filter(
        CategoryPage.id == page_id,
        CategoryPage.category_id == category_id
    ).first()

    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found in this category.")

    db.delete(page)
    db.commit()
    return {"message": "Page removed from category successfully."}

@router.post("/{category_id}/pages/check-duplicates-bulk", response_model=BulkDuplicateCheckResponse)
def check_urls_bulk(
    category_id: int,
    request: BulkDuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Checks multiple URLs at once for validity, duplicates within this category,
    and cross-category mappings (warning for double-counting).
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
        
    items = []
    seen_in_batch = set()
    total_valid = 0
    total_duplicates = 0
    total_warnings = 0
    
    # Pre-fetch existing category pages for fast lookup
    existing_in_cat = {
        p.normalized_url for p in db.query(CategoryPage.normalized_url).filter(CategoryPage.category_id == category_id).all()
    }
    
    # Pre-fetch other category mappings
    other_pages = (
        db.query(CategoryPage.normalized_url, Category.name)
        .join(Category, CategoryPage.category_id == Category.id)
        .filter(CategoryPage.category_id != category_id)
        .all()
    )
    other_map = {}
    for norm_u, cat_name in other_pages:
        other_map.setdefault(norm_u, []).append(cat_name)

    for raw in request.urls:
        raw_clean = raw.strip()
        if not raw_clean:
            continue
            
        norm = normalize_url(raw_clean)
        if not norm:
            items.append(BulkDuplicateCheckItem(
                url=raw_clean,
                normalized_url="",
                is_valid=False,
                is_duplicate_in_category=False,
                is_mapped_to_other_categories=False,
                other_category_names=[],
                warning=None,
                error="Invalid URL format."
            ))
            continue
            
        is_dup_batch = norm in seen_in_batch
        seen_in_batch.add(norm)
        is_dup_cat = (norm in existing_in_cat) or is_dup_batch
        other_names = other_map.get(norm, [])
        is_other = len(other_names) > 0
        
        warn = None
        if is_other:
            warn = f"Mapped to: {', '.join(other_names)} (potential double counting in category totals)"
            total_warnings += 1
            
        err = None
        if is_dup_cat:
            total_duplicates += 1
            err = "Already mapped in this category" if (norm in existing_in_cat) else "Duplicate in this input list"
        else:
            total_valid += 1
            
        items.append(BulkDuplicateCheckItem(
            url=raw_clean,
            normalized_url=norm,
            is_valid=not is_dup_cat,
            is_duplicate_in_category=is_dup_cat,
            is_mapped_to_other_categories=is_other,
            other_category_names=other_names,
            warning=warn,
            error=err
        ))
        
    return BulkDuplicateCheckResponse(
        items=items,
        total_valid=total_valid,
        total_duplicates=total_duplicates,
        total_warnings=total_warnings
    )

@router.post("/{category_id}/pages/bulk", response_model=PageBulkAddResult)
def add_pages_to_category_bulk(
    category_id: int,
    request: PageBulkAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """
    Leader or Manager can add multiple URLs at once to a category.
    Enforces category ownership permissions.
    Safely skips duplicates and warns on multi-category mapping.
    """
    category = check_category_edit_permission(category_id, current_user, db)
    
    existing_in_cat = {
        p.normalized_url for p in db.query(CategoryPage.normalized_url).filter(CategoryPage.category_id == category_id).all()
    }
    
    other_pages = (
        db.query(CategoryPage.normalized_url, Category.name)
        .join(Category, CategoryPage.category_id == Category.id)
        .filter(CategoryPage.category_id != category_id)
        .all()
    )
    other_map = {}
    for norm_u, cat_name in other_pages:
        other_map.setdefault(norm_u, []).append(cat_name)

    added_pages = []
    seen_in_batch = set()
    skipped_count = 0
    warnings = []
    errors = []

    for raw in request.urls:
        raw_clean = raw.strip()
        if not raw_clean:
            continue
            
        norm = normalize_url(raw_clean)
        if not norm:
            errors.append(f"Invalid URL skipped: '{raw_clean}'")
            skipped_count += 1
            continue
            
        if norm in existing_in_cat or norm in seen_in_batch:
            skipped_count += 1
            continue
            
        seen_in_batch.add(norm)
        
        if norm in other_map:
            warnings.append(f"URL '{norm}' is also mapped to {', '.join(other_map[norm])}.")
            
        new_page = CategoryPage(
            category_id=category_id,
            full_url=raw_clean,
            normalized_url=norm,
            status="ACTIVE"
        )
        db.add(new_page)
        added_pages.append(new_page)
        
    db.commit()
    for p in added_pages:
        db.refresh(p)
        
    return PageBulkAddResult(
        added_count=len(added_pages),
        skipped_count=skipped_count,
        pages=[
            CategoryPageOut(
                id=p.id,
                category_id=p.category_id,
                category_name=category.name,
                full_url=p.full_url,
                normalized_url=p.normalized_url,
                status=p.status,
                created_at=p.created_at
            )
            for p in added_pages
        ],
        warnings=warnings,
        errors=errors
    )
