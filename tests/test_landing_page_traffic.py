import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.app.models.models import User, UserRole, Category, CategoryPage, DailyPageMetrics
from backend.app.core.security import create_access_token, hash_password
from backend.app.services.metric_service import normalize_url, get_landing_page_traffic_metrics

def test_landing_page_traffic_rbac_and_windows(client: TestClient, db_session):
    db = db_session

    # 1. Setup Manager and 2 Team Leaders
    manager = User(
        email="mgr@craftyart.com",
        full_name="Manager Admin",
        hashed_password=hash_password("Pass123"),
        role=UserRole.MANAGER,
        is_active=True
    )
    leader1 = User(
        email="leader1@craftyart.com",
        full_name="Leader One",
        hashed_password=hash_password("Pass123"),
        role=UserRole.TEAM_LEADER,
        is_active=True
    )
    leader2 = User(
        email="leader2@craftyart.com",
        full_name="Leader Two",
        hashed_password=hash_password("Pass123"),
        role=UserRole.TEAM_LEADER,
        is_active=True
    )
    db.add_all([manager, leader1, leader2])
    db.commit()
    db.refresh(manager)
    db.refresh(leader1)
    db.refresh(leader2)

    # 2. Setup Categories & Pages
    cat1 = Category(name="Wedding Invitations", assigned_leader_id=leader1.id, status="ACTIVE")
    cat2 = Category(name="Flyers & Posters", assigned_leader_id=leader2.id, status="ACTIVE")
    db.add_all([cat1, cat2])
    db.commit()
    db.refresh(cat1)
    db.refresh(cat2)

    p1_url = "https://craftyartapp.com/templates/wedding"
    p2_url = "https://craftyartapp.com/templates/flyer"

    p1 = CategoryPage(
        category_id=cat1.id,
        full_url=p1_url,
        normalized_url=normalize_url(p1_url),
        status="ACTIVE"
    )
    p2 = CategoryPage(
        category_id=cat2.id,
        full_url=p2_url,
        normalized_url=normalize_url(p2_url),
        status="ACTIVE"
    )
    db.add_all([p1, p2])
    db.commit()

    # 3. Add metrics spanning dates for p1
    today = date(2026, 10, 24)
    # Latest day (d1)
    m1 = DailyPageMetrics(
        property_id=1,
        page_url=p1_url,
        normalized_url=normalize_url(p1_url),
        date=today,
        clicks=50,
        impressions=500,
        ctr=10.0,
        position=2.0
    )
    # Day 2 in 3d window
    m2 = DailyPageMetrics(
        property_id=1,
        page_url=p1_url,
        normalized_url=normalize_url(p1_url),
        date=today - timedelta(days=1),
        clicks=40,
        impressions=400,
        ctr=10.0,
        position=2.5
    )
    # In 7d window
    m3 = DailyPageMetrics(
        property_id=1,
        page_url=p1_url,
        normalized_url=normalize_url(p1_url),
        date=today - timedelta(days=5),
        clicks=30,
        impressions=300,
        ctr=10.0,
        position=3.0
    )
    # In previous 7d window (days 7 to 13)
    m4 = DailyPageMetrics(
        property_id=1,
        page_url=p1_url,
        normalized_url=normalize_url(p1_url),
        date=today - timedelta(days=10),
        clicks=60,
        impressions=600,
        ctr=10.0,
        position=4.0
    )
    # In previous 28d window (days 28 to 55)
    m5 = DailyPageMetrics(
        property_id=1,
        page_url=p1_url,
        normalized_url=normalize_url(p1_url),
        date=today - timedelta(days=35),
        clicks=100,
        impressions=1000,
        ctr=10.0,
        position=4.5
    )
    db.add_all([m1, m2, m3, m4, m5])
    db.commit()

    # Auth tokens
    mgr_token = create_access_token(subject=manager.id, role=UserRole.MANAGER)
    l1_token = create_access_token(subject=leader1.id, role=UserRole.TEAM_LEADER)
    l2_token = create_access_token(subject=leader2.id, role=UserRole.TEAM_LEADER)

    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}
    l1_headers = {"Authorization": f"Bearer {l1_token}"}
    l2_headers = {"Authorization": f"Bearer {l2_token}"}

    # Test 1: Manager can view all landing pages
    res_mgr = client.get("/api/pages/traffic", headers=mgr_headers)
    assert res_mgr.status_code == 200
    data_mgr = res_mgr.json()
    assert data_mgr["total_items"] == 2
    assert len(data_mgr["items"]) == 2
    assert data_mgr["summary"]["ga4_connected"] is False

    # Test 2: Manager can filter by Team Leader
    res_filt = client.get(f"/api/pages/traffic?leader_id={leader1.id}", headers=mgr_headers)
    assert res_filt.status_code == 200
    assert res_filt.json()["total_items"] == 1
    assert res_filt.json()["items"][0]["assigned_leader_id"] == leader1.id

    # Test 3: Team Leader 1 only sees their own assigned page (p1)
    res_l1 = client.get("/api/pages/traffic", headers=l1_headers)
    assert res_l1.status_code == 200
    data_l1 = res_l1.json()
    assert data_l1["total_items"] == 1
    assert data_l1["items"][0]["full_url"] == p1_url
    assert data_l1["items"][0]["assigned_leader_id"] == leader1.id

    # Test 4: Team Leader 1 attempting to access Leader 2's data is strictly forbidden (HTTP 403)
    res_forbidden = client.get(f"/api/pages/traffic?leader_id={leader2.id}", headers=l1_headers)
    assert res_forbidden.status_code == 403

    # Test 5: Team Leader attempting to access another leader's category is forbidden
    res_cat_forbidden = client.get(f"/api/pages/traffic?category_id={cat2.id}", headers=l1_headers)
    assert res_cat_forbidden.status_code == 403

    # Test 6: Verify Traffic Window values for p1
    item_p1 = [i for i in data_mgr["items"] if i["full_url"] == p1_url][0]
    # Latest day clicks (m1 only = 50)
    assert item_p1["latest_gsc_day_clicks"] == 50
    assert item_p1["ga4_status"] == "GA4 Required"

    # 3-day traffic (m1: 50 + m2: 40 = 90 clicks, 900 impressions)
    assert item_p1["traffic_3d"]["clicks"] == 90
    assert item_p1["traffic_3d"]["impressions"] == 900

    # 7-day traffic (m1: 50 + m2: 40 + m3: 30 = 120 clicks, 1200 impressions)
    assert item_p1["traffic_7d"]["clicks"] == 120
    assert item_p1["traffic_7d"]["impressions"] == 1200

    # 7-day comparison (current 120 vs previous m4: 60 -> diff: +60, +100%)
    assert item_p1["comparison_7d"]["current_clicks"] == 120
    assert item_p1["comparison_7d"]["previous_clicks"] == 60
    assert item_p1["comparison_7d"]["click_diff"] == 60
    assert item_p1["comparison_7d"]["pct_change"] == 100.0
    assert item_p1["comparison_7d"]["status"] == "GROWTH"

    # 28-day comparison (current: m1(50)+m2(40)+m3(30)+m4(60)=180 vs previous m5: 100 -> diff: +80, +80%)
    assert item_p1["comparison_28d"]["current_clicks"] == 180
    assert item_p1["comparison_28d"]["previous_clicks"] == 100
    assert item_p1["comparison_28d"]["click_diff"] == 80
    assert item_p1["comparison_28d"]["pct_change"] == 80.0
    assert item_p1["comparison_28d"]["status"] == "GROWTH"

    # Test 7: Page 2 has zero traffic records - verify it handles zero safely without dividing by zero
    item_p2 = [i for i in data_mgr["items"] if i["full_url"] == p2_url][0]
    assert item_p2["traffic_3d"]["clicks"] == 0
    assert item_p2["traffic_7d"]["clicks"] == 0
    assert item_p2["traffic_28d"]["clicks"] == 0
    assert item_p2["comparison_7d"]["pct_change"] == 0.0
    assert item_p2["comparison_7d"]["status"] == "NEUTRAL"
    assert item_p2["comparison_28d"]["pct_change"] == 0.0
    assert item_p2["comparison_28d"]["status"] == "NEUTRAL"

    # Test 8: Search filtering
    res_search = client.get("/api/pages/traffic?search=wedding", headers=mgr_headers)
    assert res_search.status_code == 200
    assert res_search.json()["total_items"] == 1
    assert "wedding" in res_search.json()["items"][0]["full_url"]

    # Test 9: Sorting
    res_sort = client.get("/api/pages/traffic?sort_by=clicks_28d_desc", headers=mgr_headers)
    assert res_sort.status_code == 200
    items_sorted = res_sort.json()["items"]
    assert items_sorted[0]["traffic_28d"]["clicks"] >= items_sorted[1]["traffic_28d"]["clicks"]
