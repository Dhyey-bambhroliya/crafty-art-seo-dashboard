from datetime import date, timedelta
import pytest
from backend.app.models.models import (
    User, UserRole, Category, CategoryPage, DailyPageMetrics, Alert
)
from backend.app.services.alert_service import evaluate_page_alerts

def test_alert_generation_and_deduplication(db_session):
    db = db_session

    # Create Manager and Leader
    mgr = User(email="mgr@craftyart.com", full_name="Manager", hashed_password="pw", role=UserRole.MANAGER)
    db.add(mgr)
    leader = User(email="leader@craftyart.com", full_name="Leader", hashed_password="pw", role=UserRole.TEAM_LEADER)
    db.add(leader)
    db.commit()

    # Create Category & Page
    cat = Category(name="Test Cat", assigned_leader_id=leader.id, status="ACTIVE")
    db.add(cat)
    db.commit()

    page_url = "https://craftyartapp.com/declining-page"
    page = CategoryPage(category_id=cat.id, full_url=page_url, normalized_url=page_url, status="ACTIVE")
    db.add(page)
    db.commit()

    # Insert 56 days of metrics for page with a 25% click decline (CRITICAL)
    latest_date = date.today() - timedelta(days=2)
    start_date = latest_date - timedelta(days=55)

    curr_date = start_date
    while curr_date <= latest_date:
        # First 28 days = previous period (100 clicks/day)
        # Second 28 days = current period (75 clicks/day) -> -25% decline
        is_curr = curr_date > (latest_date - timedelta(days=28))
        clicks = 75 if is_curr else 100
        impressions = 1500 if is_curr else 2000

        db.add(DailyPageMetrics(
            page_url=page_url,
            normalized_url=page_url,
            date=curr_date,
            clicks=clicks,
            impressions=impressions,
            ctr=5.0,
            position=4.0
        ))
        curr_date += timedelta(days=1)
    db.commit()

    # 1. Evaluate alerts
    created = evaluate_page_alerts(db, evaluation_date=latest_date)
    assert created > 0

    alerts = db.query(Alert).filter(Alert.normalized_url == page_url).all()
    # Must have generated CLICK_DECLINE_CRITICAL (since -25% <= -20%)
    alert_types = [a.alert_type for a in alerts]
    assert "CLICK_DECLINE_CRITICAL" in alert_types

    # 2. Running evaluate again must NOT duplicate active pending alerts
    created_second_run = evaluate_page_alerts(db, evaluation_date=latest_date)
    assert created_second_run == 0
    total_alerts = db.query(Alert).filter(Alert.normalized_url == page_url).count()
    assert total_alerts == len(alerts)
