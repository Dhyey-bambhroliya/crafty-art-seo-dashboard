from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal, get_db
from backend.app.models.models import User, UserRole, GSCProperty, DailyPageMetrics
from backend.app.models.festival_models import (
    Festival, FestivalYearDate, FestivalSubcategory, FestivalPage,
    DailyPageCountryMetrics, FestivalDateStatus, FestivalApprovalStatus
)
from backend.app.core.security import hash_password, create_access_token

@pytest.fixture
def auth_headers(db_session: Session):
    # Setup test users
    mgr = db_session.query(User).filter(User.email == "analytics_mgr@craftyart.com").first()
    if not mgr:
        mgr = User(
            email="analytics_mgr@craftyart.com",
            hashed_password=hash_password("ManagerPass123!"),
            role=UserRole.MANAGER,
            full_name="Analytics Manager",
            is_active=True
        )
        db_session.add(mgr)
        db_session.commit()
        db_session.refresh(mgr)

    tl1 = db_session.query(User).filter(User.email == "tl_assigned@craftyart.com").first()
    if not tl1:
        tl1 = User(
            email="tl_assigned@craftyart.com",
            hashed_password=hash_password("LeaderPass123!"),
            role=UserRole.TEAM_LEADER,
            full_name="Assigned Leader",
            is_active=True
        )
        db_session.add(tl1)
        db_session.commit()
        db_session.refresh(tl1)

    tl2 = db_session.query(User).filter(User.email == "tl_other@craftyart.com").first()
    if not tl2:
        tl2 = User(
            email="tl_other@craftyart.com",
            hashed_password=hash_password("LeaderPass123!"),
            role=UserRole.TEAM_LEADER,
            full_name="Other Leader",
            is_active=True
        )
        db_session.add(tl2)
        db_session.commit()
        db_session.refresh(tl2)

    prop = db_session.query(GSCProperty).first()
    if not prop:
        prop = GSCProperty(
            site_url="https://craftyartapp.com",
            is_active=True
        )
        db_session.add(prop)
        db_session.commit()
        db_session.refresh(prop)

    mgr_token = create_access_token(subject=str(mgr.id), role=mgr.role)
    tl1_token = create_access_token(subject=str(tl1.id), role=tl1.role)
    tl2_token = create_access_token(subject=str(tl2.id), role=tl2.role)

    return {
        "mgr": {"Authorization": f"Bearer {mgr_token}"},
        "tl1": {"Authorization": f"Bearer {tl1_token}"},
        "tl2": {"Authorization": f"Bearer {tl2_token}"},
        "mgr_user": mgr,
        "tl1_user": tl1,
        "tl2_user": tl2,
        "property": prop
    }

def test_relative_day_alignment_and_festival_yoy_comparison(client: TestClient, db_session: Session, auth_headers):
    """
    Test Diwali 2025 (Oct 20) vs Diwali 2026 (Nov 8).
    Different calendar dates must be aligned by relative days (e.g. Day -5 vs Day -5).
    """
    mgr_headers = auth_headers["mgr"]
    tl1_user = auth_headers["tl1_user"]
    prop = auth_headers["property"]

    # 1. Create Diwali festival assigned to tl1
    fest = db_session.query(Festival).filter(Festival.slug == "diwali-yoy-test").first()
    if not fest:
        fest = Festival(
            name="Diwali YoY Test",
            slug="diwali-yoy-test",
            country_code="IN",
            region="National",
            assigned_leader_id=tl1_user.id
        )
        db_session.add(fest)
        db_session.commit()
        db_session.refresh(fest)

    # 2. Add 2025 and 2026 editions (different dates!)
    # 2025 Diwali: Oct 20, 2025
    yd_2025 = db_session.query(FestivalYearDate).filter(FestivalYearDate.festival_id == fest.id, FestivalYearDate.year == 2025).first()
    if not yd_2025:
        yd_2025 = FestivalYearDate(
            festival_id=fest.id,
            year=2025,
            start_date=date(2025, 10, 20),
            end_date=date(2025, 10, 22),
            date_status=FestivalDateStatus.CONFIRMED,
            approval_status=FestivalApprovalStatus.APPROVED
        )
        db_session.add(yd_2025)

    # 2026 Diwali: Nov 8, 2026
    yd_2026 = db_session.query(FestivalYearDate).filter(FestivalYearDate.festival_id == fest.id, FestivalYearDate.year == 2026).first()
    if not yd_2026:
        yd_2026 = FestivalYearDate(
            festival_id=fest.id,
            year=2026,
            start_date=date(2026, 11, 8),
            end_date=date(2026, 11, 10),
            date_status=FestivalDateStatus.CONFIRMED,
            approval_status=FestivalApprovalStatus.APPROVED
        )
        db_session.add(yd_2026)
    db_session.commit()

    # 3. Map landing pages
    url1 = "https://craftyartapp.com/diwali-invitation-templates"
    url2 = "https://craftyartapp.com/diwali-festival-images"
    for u in [url1, url2]:
        p = db_session.query(FestivalPage).filter(FestivalPage.festival_id == fest.id, FestivalPage.normalized_url == u).first()
        if not p:
            db_session.add(FestivalPage(
                festival_id=fest.id,
                full_url=u,
                normalized_url=u,
                page_title=u.split("/")[-1].replace("-", " ").title(),
                priority="PRIMARY"
            ))
    db_session.commit()

    # 4. Insert synthetic GSC data aligned on relative days:
    # Say relative Day -5:
    # 2025: Oct 20 - 5 = Oct 15, 2025
    # 2026: Nov 8 - 5 = Nov 3, 2026
    d2025_minus_5 = date(2025, 10, 15)
    d2026_minus_5 = date(2026, 11, 3)

    # Clean existing test metrics for these dates
    db_session.query(DailyPageMetrics).filter(
        DailyPageMetrics.normalized_url.in_([url1, url2]),
        DailyPageMetrics.date.in_([d2025_minus_5, d2026_minus_5])
    ).delete()
    db_session.commit()

    # 2025 metrics: 100 clicks, 1000 imp, pos 4.0
    db_session.add(DailyPageMetrics(
        property_id=prop.id,
        page_url=url1,
        normalized_url=url1,
        date=d2025_minus_5,
        clicks=100,
        impressions=1000,
        position=4.0,
        ctr=10.0,
        is_synthetic=True
    ))
    # 2026 metrics: 150 clicks, 1200 imp, pos 2.0 (improvement!)
    db_session.add(DailyPageMetrics(
        property_id=prop.id,
        page_url=url1,
        normalized_url=url1,
        date=d2026_minus_5,
        clicks=150,
        impressions=1200,
        position=2.0,
        ctr=12.5,
        is_synthetic=True
    ))
    db_session.commit()

    # 5. Query YoY Comparison API
    res = client.get(
        f"/api/festivals/{fest.id}/analytics/comparison?current_year=2026&previous_year=2025&relative_days_before=10&relative_days_after=2",
        headers=mgr_headers
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["festival_id"] == fest.id
    assert data["current_year"] == 2026
    assert data["previous_year"] == 2025
    assert data["current_start_date"] == "2026-11-08"
    assert data["previous_start_date"] == "2025-10-20"

    summary = data["summary"]
    # 150 clicks vs 100 clicks -> +50% growth
    assert summary["current_period"]["clicks"] == 150
    assert summary["previous_period"]["clicks"] == 100
    assert summary["click_growth_pct"] == 50.0
    assert summary["impression_diff"] == 200
    # Position improved from 4.0 to 2.0 (-2.0 diff -> IMPROVED)
    assert summary["position_diff"] == -2.0
    assert summary["position_status"] == "IMPROVED"

    # Verify trends contain the relative alignment
    trends = data["relative_trends"]
    minus_5_pt = next(t for t in trends if t["relative_day"] == -5)
    assert minus_5_pt["current_date"] == "2026-11-03"
    assert minus_5_pt["previous_date"] == "2025-10-15"
    assert minus_5_pt["current_clicks"] == 150
    assert minus_5_pt["previous_clicks"] == 100

def test_duplicate_url_prevention_in_festival_aggregation(client: TestClient, db_session: Session, auth_headers):
    """
    Ensure mapping multiple subcategories or pages with same normalized URL
    does not double-count metrics in festival aggregation.
    """
    mgr_headers = auth_headers["mgr"]
    tl1_user = auth_headers["tl1_user"]
    prop = auth_headers["property"]

    fest = Festival(
        name="Deduplication Test Fest",
        slug="dedup-test-fest",
        country_code="US",
        assigned_leader_id=tl1_user.id
    )
    db_session.add(fest)
    db_session.commit()

    # Try mapping same URL twice via API
    dup_url = "https://craftyartapp.com/halloween-costumes"
    res1 = client.post(
        f"/api/festivals/{fest.id}/pages",
        headers=mgr_headers,
        json={"full_url": dup_url, "priority": "PRIMARY"}
    )
    assert res1.status_code == 200

    # Second attempt must be rejected with 400 Bad Request
    res2 = client.post(
        f"/api/festivals/{fest.id}/pages",
        headers=mgr_headers,
        json={"full_url": dup_url + "/", "priority": "SECONDARY"}
    )
    assert res2.status_code == 400
    assert "already mapped" in res2.json()["detail"]

def test_country_filtering_via_additive_storage(client: TestClient, db_session: Session, auth_headers):
    """
    Test searcher country filtering using additive storage:
    - Independent from festival host country
    - Does not label worldwide as India metrics
    - Distinguishes missing country data
    """
    mgr_headers = auth_headers["mgr"]
    prop = auth_headers["property"]

    fest = Festival(
        name="Country Filter Fest",
        slug="country-filter-fest",
        country_code="IN"
    )
    db_session.add(fest)
    db_session.commit()

    yd = FestivalYearDate(
        festival_id=fest.id,
        year=2026,
        start_date=date(2026, 8, 15),
        end_date=date(2026, 8, 15)
    )
    db_session.add(yd)

    page_url = "https://craftyartapp.com/independence-day-templates"
    page = FestivalPage(
        festival_id=fest.id,
        full_url=page_url,
        normalized_url=page_url,
        priority="PRIMARY"
    )
    db_session.add(page)
    db_session.commit()

    test_date = date(2026, 8, 10)  # Day -5
    # Insert country-specific records
    # IN searchers: 500 clicks
    # US searchers: 50 clicks
    db_session.add(DailyPageCountryMetrics(
        property_id=prop.id,
        page_url=page_url,
        normalized_url=page_url,
        date=test_date,
        country_code="in",
        clicks=500,
        impressions=2000,
        ctr=25.0,
        position=1.5
    ))
    db_session.add(DailyPageCountryMetrics(
        property_id=prop.id,
        page_url=page_url,
        normalized_url=page_url,
        date=test_date,
        country_code="us",
        clicks=50,
        impressions=500,
        ctr=10.0,
        position=5.0
    ))
    db_session.commit()

    # 1. Query for IN searchers
    res_in = client.get(
        f"/api/festivals/{fest.id}/analytics/comparison?current_year=2026&searcher_country=IN&relative_days_before=10&relative_days_after=0",
        headers=mgr_headers
    )
    assert res_in.status_code == 200
    data_in = res_in.json()
    assert data_in["summary"]["searcher_country"] == "IN"
    assert data_in["summary"]["current_period"]["clicks"] == 500

    # 2. Query for US searchers
    res_us = client.get(
        f"/api/festivals/{fest.id}/analytics/comparison?current_year=2026&searcher_country=US&relative_days_before=10&relative_days_after=0",
        headers=mgr_headers
    )
    assert res_us.status_code == 200
    data_us = res_us.json()
    assert data_us["summary"]["searcher_country"] == "US"
    assert data_us["summary"]["current_period"]["clicks"] == 50

    # 3. Query for GB searchers (where no country data exists -> must return DATA_UNAVAILABLE without inventing data!)
    res_gb = client.get(
        f"/api/festivals/{fest.id}/analytics/comparison?current_year=2026&searcher_country=GB&relative_days_before=10&relative_days_after=0",
        headers=mgr_headers
    )
    assert res_gb.status_code == 200
    data_gb = res_gb.json()
    assert data_gb["summary"]["country_data_available"] is False
    assert data_gb["summary"]["season_status"] == "DATA_UNAVAILABLE"
    assert "not available in historical records" in data_gb["summary"]["note"]

def test_incomplete_season_apples_to_apples_handling(client: TestClient, db_session: Session, auth_headers):
    """
    Test incomplete seasons (e.g. today is Day -10 before festival).
    Only equivalent available relative days are aggregated for YoY summary metrics.
    Future dates must be marked unavailable without being treated as 0 clicks.
    """
    mgr_headers = auth_headers["mgr"]
    prop = auth_headers["property"]

    fest = Festival(
        name="Incomplete Season Fest",
        slug="incomplete-season-fest",
        country_code="US"
    )
    db_session.add(fest)
    db_session.commit()

    # Editions:
    # 2025: Dec 25
    # 2026: Dec 25
    yd_2025 = FestivalYearDate(festival_id=fest.id, year=2025, start_date=date(2025, 12, 25), end_date=date(2025, 12, 25))
    yd_2026 = FestivalYearDate(festival_id=fest.id, year=2026, start_date=date(2026, 12, 25), end_date=date(2026, 12, 25))
    db_session.add_all([yd_2025, yd_2026])

    page_url = "https://craftyartapp.com/christmas-cards"
    db_session.add(FestivalPage(festival_id=fest.id, full_url=page_url, normalized_url=page_url))
    db_session.commit()

    # Suppose current GSC data is synced only up to Day -15 (Dec 10, 2026)
    # Day -20: Dec 5, 2025 has 10 clicks; Dec 5, 2026 has 20 clicks
    # Day -15: Dec 10, 2025 has 30 clicks; Dec 10, 2026 has 40 clicks
    # Day -5: Dec 20, 2025 has 100 clicks; Dec 20, 2026 is FUTURE (no data yet)
    db_session.add_all([
        DailyPageMetrics(property_id=prop.id, page_url=page_url, normalized_url=page_url, date=date(2025, 12, 5), clicks=10, impressions=100),
        DailyPageMetrics(property_id=prop.id, page_url=page_url, normalized_url=page_url, date=date(2026, 12, 5), clicks=20, impressions=150),
        DailyPageMetrics(property_id=prop.id, page_url=page_url, normalized_url=page_url, date=date(2025, 12, 10), clicks=30, impressions=300),
        DailyPageMetrics(property_id=prop.id, page_url=page_url, normalized_url=page_url, date=date(2026, 12, 10), clicks=40, impressions=400),
        DailyPageMetrics(property_id=prop.id, page_url=page_url, normalized_url=page_url, date=date(2025, 12, 20), clicks=100, impressions=1000),
    ])
    db_session.commit()

    res = client.get(
        f"/api/festivals/{fest.id}/analytics/comparison?current_year=2026&previous_year=2025&relative_days_before=20&relative_days_after=0",
        headers=mgr_headers
    )
    assert res.status_code == 200
    data = res.json()
    summary = data["summary"]

    assert summary["season_status"] == "SEASON_TO_DATE"
    assert "Season in progress" in summary["note"]

    # In apples-to-apples comparison, only Day -20 and Day -15 are in both seasons!
    # 2026 clicks = 20 + 40 = 60
    # 2025 clicks for equivalent days = 10 + 30 = 40 (Day -5's 100 clicks is excluded from summary!)
    assert summary["current_period"]["clicks"] == 60
    assert summary["previous_period"]["clicks"] == 40
    assert summary["click_growth_pct"] == 50.0

def test_zero_impressions_and_ctr_position_calculations(client: TestClient, db_session: Session, auth_headers):
    """
    Verify zero impressions do not cause division by zero errors,
    and impression-weighted position is accurately calculated.
    """
    mgr_headers = auth_headers["mgr"]
    prop = auth_headers["property"]

    fest = Festival(name="Zero Imp Fest", slug="zero-imp-fest", country_code="IN")
    db_session.add(fest)
    db_session.commit()

    yd = FestivalYearDate(festival_id=fest.id, year=2026, start_date=date(2026, 5, 1), end_date=date(2026, 5, 1))
    db_session.add(yd)

    page1 = "https://craftyartapp.com/zero-traffic-page"
    page2 = "https://craftyartapp.com/high-traffic-page"
    db_session.add_all([
        FestivalPage(festival_id=fest.id, full_url=page1, normalized_url=page1),
        FestivalPage(festival_id=fest.id, full_url=page2, normalized_url=page2)
    ])
    db_session.commit()

    test_date = date(2026, 4, 30)
    # Page 1 has 0 impressions and 0 clicks
    # Page 2 has 200 clicks, 1000 impressions, position 3.0
    db_session.add_all([
        DailyPageMetrics(property_id=prop.id, page_url=page1, normalized_url=page1, date=test_date, clicks=0, impressions=0, position=0.0),
        DailyPageMetrics(property_id=prop.id, page_url=page2, normalized_url=page2, date=test_date, clicks=200, impressions=1000, position=3.0)
    ])
    db_session.commit()

    res = client.get(
        f"/api/festivals/{fest.id}/analytics/comparison?current_year=2026&relative_days_before=5&relative_days_after=0",
        headers=mgr_headers
    )
    assert res.status_code == 200
    data = res.json()
    summary = data["summary"]
    assert summary["current_period"]["clicks"] == 200
    assert summary["current_period"]["impressions"] == 1000
    assert summary["current_period"]["ctr"] == 20.0
    assert summary["current_period"]["position"] == 3.0

    # Check page-level for zero-traffic page
    p1 = next(p for p in data["landing_pages"] if p["normalized_url"] == page1)
    assert p1["current_clicks"] == 0
    assert p1["current_impressions"] == 0
    assert p1["current_ctr"] == 0.0
    assert p1["current_position"] == 0.0

def test_cross_leader_analytics_access_prevention(client: TestClient, db_session: Session, auth_headers):
    """
    Team Leaders cannot view analytics for festivals assigned to another Team Leader.
    Must return HTTP 403 Forbidden.
    """
    tl1_user = auth_headers["tl1_user"]
    tl2_headers = auth_headers["tl2"]  # Other Team Leader

    # Festival assigned to tl1
    fest = Festival(
        name="Private TL1 Festival",
        slug="private-tl1-fest",
        country_code="IN",
        assigned_leader_id=tl1_user.id
    )
    db_session.add(fest)
    db_session.commit()

    yd = FestivalYearDate(festival_id=fest.id, year=2026, start_date=date(2026, 10, 1), end_date=date(2026, 10, 1))
    db_session.add(yd)
    db_session.commit()

    # TL2 attempts to access analytics for TL1's festival
    res = client.get(
        f"/api/festivals/{fest.id}/analytics/comparison?current_year=2026",
        headers=tl2_headers
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # TL2 attempts to access pages analytics
    res2 = client.get(
        f"/api/festivals/{fest.id}/analytics/pages?current_year=2026",
        headers=tl2_headers
    )
    assert res2.status_code == 403
