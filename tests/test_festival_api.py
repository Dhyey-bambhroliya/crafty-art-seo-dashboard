import pytest
from datetime import date
from fastapi.testclient import TestClient

from backend.app.models.models import User, UserRole
from backend.app.models.festival_models import Festival, FestivalYearDate, FestivalDateStatus, FestivalApprovalStatus
from backend.app.core.security import hash_password, create_access_token

def get_auth_headers(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role)
    return {"Authorization": f"Bearer {token}"}

def test_festival_api_create_and_list_by_manager(client: TestClient, db_session):
    """Verify Manager can create custom festivals and list them."""
    manager = User(email="mgr_fest_api@craftyart.com", full_name="Festival Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    leader = User(email="lead_fest_api@craftyart.com", full_name="Festival Team Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([manager, leader])
    db_session.commit()

    mgr_headers = get_auth_headers(manager)

    # Create festival with initial year date
    payload = {
        "name": "Diwali Festival 2026",
        "slug": "diwali-fest-2026",
        "country_code": "IN",
        "region": "National",
        "category_group": "Cultural & Religious",
        "description": "Grand Diwali celebration",
        "assigned_leader_id": leader.id,
        "is_active": True,
        "initial_year_date": {
            "year": 2026,
            "start_date": "2026-11-08",
            "end_date": "2026-11-10",
            "prep_start_date": "2026-09-10",
            "prep_deadline_date": "2026-10-25"
        }
    }

    res = client.post("/api/festivals", json=payload, headers=mgr_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["name"] == "Diwali Festival 2026"
    assert data["country_code"] == "IN"
    assert data["assigned_leader_id"] == leader.id
    assert data["assigned_leader_name"] == "Festival Team Leader"
    assert data["upcoming_edition_year"] == 2026
    assert data["date_status"] == "UNVERIFIED"
    assert data["approval_status"] == "PENDING"

    # List festivals
    list_res = client.get("/api/festivals", headers=mgr_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert any(f["slug"] == "diwali-fest-2026" for f in list_res.json())

def test_festival_api_country_and_search_filters(client: TestClient, db_session):
    """Verify filtering by country_code, region, search, and year."""
    manager = User(email="mgr_filter@craftyart.com", full_name="Filter Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    db_session.add(manager)
    db_session.commit()
    headers = get_auth_headers(manager)

    f_in = Festival(name="Holi Festival", slug="holi-india", country_code="IN", region="North India", is_active=True)
    f_us = Festival(name="Independence Day", slug="independence-day-usa", country_code="US", region="National", is_active=True)
    f_uk = Festival(name="Bonfire Night", slug="bonfire-night-uk", country_code="GB", region="England", is_active=True)
    db_session.add_all([f_in, f_us, f_uk])
    db_session.commit()

    # Filter by country_code=IN
    in_res = client.get("/api/festivals?country_code=IN", headers=headers)
    assert in_res.status_code == 200
    slugs_in = [x["slug"] for x in in_res.json()]
    assert "holi-india" in slugs_in
    assert "independence-day-usa" not in slugs_in

    # Filter by country_code=US
    us_res = client.get("/api/festivals?country_code=US", headers=headers)
    assert us_res.status_code == 200
    slugs_us = [x["slug"] for x in us_res.json()]
    assert "independence-day-usa" in slugs_us
    assert "holi-india" not in slugs_us

    # Filter by search keyword
    search_res = client.get("/api/festivals?search=Bonfire", headers=headers)
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1
    assert search_res.json()[0]["slug"] == "bonfire-night-uk"

def test_suggestions_engine_preview_and_apply(client: TestClient, db_session):
    """
    Verify automatic festival suggestions for countries and application into database.
    Verifies that suggestions start with UNVERIFIED/PENDING status and are not pre-approved.
    """
    manager = User(email="mgr_sugg@craftyart.com", full_name="Suggestion Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    db_session.add(manager)
    db_session.commit()
    headers = get_auth_headers(manager)

    # 1. Preview suggestions for India 2026
    preview_res = client.get("/api/festivals/suggestions?country_code=IN&year=2026", headers=headers)
    assert preview_res.status_code == 200
    suggestions = preview_res.json()
    assert len(suggestions) >= 6
    diwali_sugg = next(s for s in suggestions if s["slug"] == "diwali")
    assert diwali_sugg["name"] == "Diwali"
    assert diwali_sugg["year"] == 2026
    assert diwali_sugg["start_date"] == "2026-11-08"
    assert diwali_sugg["approval_status"] == "PENDING"  # Must NOT be pre-approved

    # 2. Preview suggestions for US 2026 (Verify Thanksgiving 4th Thursday in Nov)
    us_preview = client.get("/api/festivals/suggestions?country_code=US&year=2026", headers=headers)
    assert us_preview.status_code == 200
    tg = next(s for s in us_preview.json() if s["slug"] == "thanksgiving-us")
    assert tg["start_date"] == "2026-11-26"  # 4th Thursday of Nov 2026
    assert tg["calculation_type"] == "RULE_BASED_GREGORIAN"

    # 3. Preview suggestions for UK 2026 (Verify Easter via Computus: April 5, 2026)
    uk_preview = client.get("/api/festivals/suggestions?country_code=GB&year=2026", headers=headers)
    assert uk_preview.status_code == 200
    easter = next(s for s in uk_preview.json() if s["slug"] == "easter")
    assert "2026-04" in easter["start_date"]

    # 4. Preview suggestions for Canada (Verify distinct Canadian Thanksgiving: 2nd Mon in Oct)
    ca_preview = client.get("/api/festivals/suggestions?country_code=CA&year=2026", headers=headers)
    assert ca_preview.status_code == 200
    ca_tg = next(s for s in ca_preview.json() if s["slug"] == "thanksgiving-ca")
    assert ca_tg["start_date"] == "2026-10-12"  # 2nd Monday of Oct 2026

    # 5. Apply selected suggestions into database
    apply_payload = {
        "country_code": "IN",
        "year": 2026,
        "selected_slugs": ["diwali", "holi"]
    }
    apply_res = client.post("/api/festivals/suggestions/apply", json=apply_payload, headers=headers)
    assert apply_res.status_code == 200
    assert apply_res.json()["created_festivals"] == 2
    assert apply_res.json()["created_year_dates"] == 2

    # Query DB to ensure approval_status is strictly PENDING
    fest_diwali = db_session.query(Festival).filter(Festival.slug == "diwali").first()
    assert fest_diwali is not None
    assert len(fest_diwali.year_dates) == 1
    assert fest_diwali.year_dates[0].approval_status == FestivalApprovalStatus.PENDING

def test_manager_approval_workflow_and_team_leader_block(client: TestClient, db_session):
    """
    CRITICAL PERMISSION TEST:
    Only Managers can approve/reject festival dates.
    Team Leaders attempting to approve must receive HTTP 403.
    """
    manager = User(email="mgr_auth@craftyart.com", full_name="Manager Auth", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    leader = User(email="leader_auth@craftyart.com", full_name="Leader Auth", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([manager, leader])
    db_session.commit()

    mgr_headers = get_auth_headers(manager)
    lead_headers = get_auth_headers(leader)

    fest = Festival(name="Ganesh Festival", slug="ganesh-fest", country_code="IN", assigned_leader_id=leader.id)
    db_session.add(fest)
    db_session.commit()

    yd = FestivalYearDate(
        festival_id=fest.id,
        year=2026,
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 24),
        date_status=FestivalDateStatus.UNVERIFIED,
        approval_status=FestivalApprovalStatus.PENDING
    )
    db_session.add(yd)
    db_session.commit()

    # 1. Team Leader attempts to approve -> Must be rejected with 403 Forbidden
    lead_res = client.put(f"/api/festivals/{fest.id}/years/2026/approve", json={"approval_status": "APPROVED"}, headers=lead_headers)
    assert lead_res.status_code == 403
    assert "Manager privileges required" in lead_res.text

    # 2. Manager approves -> Must succeed
    mgr_res = client.put(f"/api/festivals/{fest.id}/years/2026/approve", json={"approval_status": "APPROVED", "notes": "Verified by Manager"}, headers=mgr_headers)
    assert mgr_res.status_code == 200
    res_data = mgr_res.json()
    assert res_data["approval_status"] == "APPROVED"
    assert res_data["date_status"] == "CONFIRMED"
    assert res_data["approved_by_user_id"] == manager.id

def test_cross_leader_access_prevention(client: TestClient, db_session):
    """
    CRITICAL PERMISSION TEST:
    A Team Leader must NOT be able to view, edit, or access festivals or landing pages
    assigned to other Team Leaders.
    """
    leader_x = User(email="leader_x@craftyart.com", full_name="Leader X", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    leader_y = User(email="leader_y@craftyart.com", full_name="Leader Y", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([leader_x, leader_y])
    db_session.commit()

    headers_x = get_auth_headers(leader_x)
    headers_y = get_auth_headers(leader_y)

    fest_x = Festival(name="Festival X", slug="fest-x", country_code="IN", assigned_leader_id=leader_x.id)
    fest_y = Festival(name="Festival Y", slug="fest-y", country_code="US", assigned_leader_id=leader_y.id)
    db_session.add_all([fest_x, fest_y])
    db_session.commit()

    # Leader X lists festivals -> Sees Festival X, does NOT see Festival Y
    list_x = client.get("/api/festivals", headers=headers_x)
    assert list_x.status_code == 200
    slugs_x = [f["slug"] for f in list_x.json()]
    assert "fest-x" in slugs_x
    assert "fest-y" not in slugs_x

    # Leader X directly accesses Festival Y -> 403 Forbidden
    detail_y_attempt = client.get(f"/api/festivals/{fest_y.id}", headers=headers_x)
    assert detail_y_attempt.status_code == 403
    assert "Access denied" in detail_y_attempt.json()["detail"]

    # Leader X attempts to edit Festival Y -> 403 Forbidden
    edit_y_attempt = client.put(f"/api/festivals/{fest_y.id}", json={"description": "Hacked description"}, headers=headers_x)
    assert edit_y_attempt.status_code == 403

def test_duplicate_festival_slug_and_year_rejection(client: TestClient, db_session):
    """Verify duplicate festival slug and duplicate year date cannot be created."""
    manager = User(email="mgr_dup@craftyart.com", full_name="Dup Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    db_session.add(manager)
    db_session.commit()
    headers = get_auth_headers(manager)

    # 1. Create first festival
    p1 = {"name": "Unique Festival", "slug": "unique-fest", "country_code": "IN"}
    res1 = client.post("/api/festivals", json=p1, headers=headers)
    assert res1.status_code == 200
    fest_id = res1.json()["id"]

    # Attempt to create duplicate slug -> 400 Bad Request
    res2 = client.post("/api/festivals", json=p1, headers=headers)
    assert res2.status_code == 400
    assert "already exists" in res2.text

    # 2. Add year date
    yd_payload = {"year": 2026, "start_date": "2026-10-10", "end_date": "2026-10-12"}
    res_yd1 = client.post(f"/api/festivals/{fest_id}/years", json=yd_payload, headers=headers)
    assert res_yd1.status_code == 200

    # Attempt to add same year again -> 400 Bad Request
    res_yd2 = client.post(f"/api/festivals/{fest_id}/years", json=yd_payload, headers=headers)
    assert res_yd2.status_code == 400
    assert "already has date records" in res_yd2.text


def test_festival_flat_form_fields_and_unconfigured_year_visibility(client: TestClient, db_session):
    """
    Verifies the fix for the live bug:
    1. Frontend submits flat form fields (initial_year, start_date, end_date, date_status).
    2. Backend schema automatically maps them into initial_year_date.
    3. YearDate is created and festival is immediately visible under the year filter.
    4. An unconfigured festival (no year dates at all) is ALSO returned under year filters so it is never hidden.
    """
    manager = User(email="mgr_livefix@craftyart.com", full_name="Live Fix Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    leader = User(email="lead_livefix@craftyart.com", full_name="Live Fix Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([manager, leader])
    db_session.commit()

    mgr_headers = get_auth_headers(manager)

    # 1. Create with FLAT fields (exactly as frontend form sends)
    flat_payload = {
        "name": "Navratri Mahotsav",
        "country_code": "IN",
        "category_group": "Religious Festival",
        "description": "Nine nights of celebrations",
        "assigned_leader_id": leader.id,
        "initial_year": 2026,
        "start_date": "2026-10-11",
        "end_date": "2026-10-19",
        "date_status": "ESTIMATED"
    }
    create_res = client.post("/api/festivals", json=flat_payload, headers=mgr_headers)
    assert create_res.status_code == 200, create_res.text
    fest_data = create_res.json()
    assert fest_data["name"] == "Navratri Mahotsav"
    assert fest_data["upcoming_edition_year"] == 2026
    assert fest_data["upcoming_start_date"] == "2026-10-11"
    assert fest_data["date_status"] == "ESTIMATED"

    # 2. Query with year=2026: MUST be returned!
    list_year_res = client.get("/api/festivals?year=2026", headers=mgr_headers)
    assert list_year_res.status_code == 200
    slugs_2026 = [f["slug"] for f in list_year_res.json()]
    assert "navratri-mahotsav" in slugs_2026

    # 3. Create a festival WITHOUT any dates (unconfigured)
    nodate_payload = {
        "name": "Empty Dates Festival",
        "country_code": "IN",
        "category_group": "Cultural",
        "assigned_leader_id": leader.id
    }
    create_nodate = client.post("/api/festivals", json=nodate_payload, headers=mgr_headers)
    assert create_nodate.status_code == 200
    assert create_nodate.json()["upcoming_edition_year"] is None

    # Query with year=2026: The unconfigured festival MUST STILL be visible (not hidden)!
    list_after = client.get("/api/festivals?year=2026", headers=mgr_headers)
    assert list_after.status_code == 200
    slugs_after = [f["slug"] for f in list_after.json()]
    assert "empty-dates-festival" in slugs_after

    # Query with no year filter: BOTH must be visible!
    list_all = client.get("/api/festivals", headers=mgr_headers)
    assert list_all.status_code == 200
    slugs_all = [f["slug"] for f in list_all.json()]
    assert "navratri-mahotsav" in slugs_all
    assert "empty-dates-festival" in slugs_all


def test_team_leader_creation_and_immediate_visibility(client: TestClient, db_session):
    """
    Verifies that when a Team Leader creates a festival:
    1. It is automatically assigned strictly to the Team Leader.
    2. It appears immediately in the Team Leader's festival list.
    """
    leader = User(email="tl_create_vis@craftyart.com", full_name="Visible Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add(leader)
    db_session.commit()
    tl_headers = get_auth_headers(leader)

    tl_payload = {
        "name": "Leader Special Fest",
        "country_code": "IN",
        "initial_year": 2026,
        "start_date": "2026-12-01",
        "end_date": "2026-12-05",
        "date_status": "VERIFIED"
    }
    create_res = client.post("/api/festivals", json=tl_payload, headers=tl_headers)
    assert create_res.status_code == 200, create_res.text
    fest_data = create_res.json()
    assert fest_data["assigned_leader_id"] == leader.id

    # Team Leader lists festivals with year=2026
    list_res = client.get("/api/festivals?year=2026", headers=tl_headers)
    assert list_res.status_code == 200
    slugs = [f["slug"] for f in list_res.json()]
    assert "leader-special-fest" in slugs



def test_festival_landing_page_direct_and_bulk_mapping(client: TestClient, db_session):
    """
    Test direct landing page mapping (without subcategory) and bulk landing page mapping:
    - Map directly with subcategory_id=None
    - Bulk map multiple URLs from textarea
    - Detect duplicates (within batch and with already mapped pages)
    - Auto-link with existing CategoryPage if URL matches
    - Calculate task_count, completed_task_count, and seo_status
    """
    manager = User(email="mgr_landing_page@craftyart.com", full_name="Landing Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    leader = User(email="lead_landing_page@craftyart.com", full_name="Landing Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([manager, leader])
    db_session.commit()

    mgr_headers = get_auth_headers(manager)
    tl_headers = get_auth_headers(leader)

    # 1. Create festival assigned to leader
    create_fest_payload = {
        "name": "Diwali Landing Test",
        "country_code": "IN",
        "assigned_leader_id": leader.id
    }
    fest_res = client.post("/api/festivals", json=create_fest_payload, headers=mgr_headers)
    assert fest_res.status_code == 200
    fest_id = fest_res.json()["id"]

    # 2. Direct mapping single URL without subcategory (as Team Leader)
    single_page_payload = {
        "page_url": "https://www.craftyartapp.com/diwali-wishes/templates",
        "notes": "Main diwali templates"
    }
    single_res = client.post(f"/api/festivals/{fest_id}/pages", json=single_page_payload, headers=tl_headers)
    assert single_res.status_code == 200
    page_data = single_res.json()
    assert page_data["page_url"] == "https://www.craftyartapp.com/diwali-wishes/templates"
    assert page_data["subcategory_id"] is None
    assert page_data["task_count"] == 0
    assert page_data["completed_task_count"] == 0
    assert page_data["seo_status"] == "NOT_STARTED"
    single_page_id = page_data["id"]

    # 3. Bulk mapping with:
    # - 1 already mapped (duplicate from above)
    # - 2 new unique URLs
    # - 1 duplicate within the bulk payload
    # - 1 invalid URL format
    bulk_payload = {
        "urls_text": """
            https://www.craftyartapp.com/diwali-wishes/templates
            https://www.craftyartapp.com/diwali-images-and-poster
            https://www.craftyartapp.com/happy-diwali-status-video-download/
            https://www.craftyartapp.com/diwali-images-and-poster
            invalid-url-without-scheme
        """,
        "notes": "Bulk imported"
    }
    bulk_res = client.post(f"/api/festivals/{fest_id}/pages/bulk", json=bulk_payload, headers=tl_headers)
    assert bulk_res.status_code == 200
    bulk_data = bulk_res.json()
    assert bulk_data["total_submitted"] == 5
    assert bulk_data["added_count"] == 2
    assert bulk_data["duplicate_count"] == 2
    assert bulk_data["invalid_count"] == 1
    assert len(bulk_data["added_pages"]) == 2

    # 4. List all festival pages
    list_pages_res = client.get(f"/api/festivals/{fest_id}/pages", headers=tl_headers)
    assert list_pages_res.status_code == 200
    all_pages = list_pages_res.json()
    assert len(all_pages) == 3
    for p in all_pages:
        assert p["festival_id"] == fest_id
        assert p["subcategory_id"] is None
        assert p["assigned_leader_name"] == "Landing Leader"

    # 5. Create a task linked specifically to a landing page
    task_payload = {
        "title": "Optimize Meta Title & H1 for Templates",
        "task_type": "ON_PAGE",
        "priority": "HIGH",
        "status": "IN_PROGRESS",
        "landing_page_id": single_page_id,
        "due_date": "2026-10-30"
    }
    task_res = client.post(f"/api/festivals/{fest_id}/tasks", json=task_payload, headers=tl_headers)
    assert task_res.status_code == 200
    task_data = task_res.json()
    assert task_data["landing_page_id"] == single_page_id
    assert task_data["landing_page_url"] == "https://www.craftyartapp.com/diwali-wishes/templates"

    # 6. Check that page seo_status reflects task in progress
    updated_pages_res = client.get(f"/api/festivals/{fest_id}/pages", headers=tl_headers)
    assert updated_pages_res.status_code == 200
    p1 = next(p for p in updated_pages_res.json() if p["id"] == single_page_id)
    assert p1["task_count"] == 1
    assert p1["completed_task_count"] == 0
    assert p1["seo_status"] == "IN_PROGRESS"

    # 7. Complete the task
    task_id = task_data["id"]
    complete_res = client.put(f"/api/festivals/{fest_id}/tasks/{task_id}", json={"status": "COMPLETED"}, headers=tl_headers)
    assert complete_res.status_code == 200

    # 8. Check that page seo_status is now COMPLETED
    done_pages_res = client.get(f"/api/festivals/{fest_id}/pages", headers=tl_headers)
    p1_done = next(p for p in done_pages_res.json() if p["id"] == single_page_id)
    assert p1_done["task_count"] == 1
    assert p1_done["completed_task_count"] == 1
    assert p1_done["seo_status"] == "COMPLETED"
