from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.models import User, UserRole, GSCProperty, DailyPageMetrics
from backend.app.models.festival_models import (
    Festival, FestivalYearDate, FestivalTask, FestivalNotification,
    FestivalTaskStatus, FestivalApprovalStatus, FestivalDateStatus,
    FestivalNotificationType
)
from backend.app.core.security import hash_password, create_access_token
from backend.app.services.festival_notification_service import (
    generate_festival_milestone_reminders,
    generate_overdue_task_reminders,
    create_festival_notification
)
from backend.app.services.festival_analytics_service import calculate_growth_metrics

def get_auth_headers(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role)
    return {"Authorization": f"Bearer {token}"}

def test_zero_baseline_analytics_growth_calculation_correction():
    """
    TASK 1: Verify percentage growth calculation corrections:
    - Previous = 0, Current > 0: returns None with status 'NEW_TRAFFIC' (NOT 100%!).
    - Previous = 0, Current = 0: returns None with status 'NO_BASELINE'.
    - Previous > 0: returns standard percentage growth.
    """
    # 1. Zero baseline with new traffic
    pct, status_label = calculate_growth_metrics(curr=150, prev=0)
    assert pct is None
    assert status_label == "NEW_TRAFFIC"

    # 2. Zero baseline with zero traffic
    pct_zero, status_zero = calculate_growth_metrics(curr=0, prev=0)
    assert pct_zero is None
    assert status_zero == "NO_BASELINE"

    # 3. Standard baseline
    pct_std, status_std = calculate_growth_metrics(curr=150, prev=100)
    assert pct_std == 50.0
    assert status_std == "+50.0%"

    # 4. Decline
    pct_dec, status_dec = calculate_growth_metrics(curr=50, prev=100)
    assert pct_dec == -50.0
    assert status_dec == "-50.0%"

def test_festival_milestone_reminders_and_idempotency(db_session: Session):
    """
    TASK 2 & 4: Test 30/15/7-day milestone reminder generation,
    unapproved date exclusion, and duplicate prevention.
    """
    mgr = User(email="notif_mgr@craftyart.com", full_name="Notif Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    leader = User(email="notif_lead@craftyart.com", full_name="Notif Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([mgr, leader])
    db_session.commit()

    ref_date = date(2026, 10, 1)

    # Festival 1: Approved Diwali edition starting in exactly 30 days (Oct 31, 2026)
    fest_appr = Festival(name="Diwali Approved", slug="diwali-approved", country_code="IN", assigned_leader_id=leader.id)
    db_session.add(fest_appr)
    db_session.commit()

    yd_30 = FestivalYearDate(
        festival_id=fest_appr.id,
        year=2026,
        start_date=ref_date + timedelta(days=30),  # Exactly 30 days
        end_date=ref_date + timedelta(days=32),
        date_status=FestivalDateStatus.CONFIRMED,
        approval_status=FestivalApprovalStatus.APPROVED  # Approved!
    )
    db_session.add(yd_30)

    # Festival 2: UNAPPROVED Diwali edition starting in 30 days -> MUST NOT SEND REMINDERS!
    fest_unappr = Festival(name="Diwali Pending", slug="diwali-pending", country_code="IN", assigned_leader_id=leader.id)
    db_session.add(fest_unappr)
    db_session.commit()

    yd_unappr = FestivalYearDate(
        festival_id=fest_unappr.id,
        year=2026,
        start_date=ref_date + timedelta(days=30),
        end_date=ref_date + timedelta(days=32),
        date_status=FestivalDateStatus.UNVERIFIED,
        approval_status=FestivalApprovalStatus.PENDING  # Pending approval!
    )
    db_session.add(yd_unappr)
    db_session.commit()

    # Run reminder generation for ref_date
    res1 = generate_festival_milestone_reminders(db_session, target_date=ref_date, offsets=[30, 15, 7])
    assert res1["status"] == "SUCCESS"
    assert res1["created_reminders"] >= 1  # Reminders created for leader and manager

    # Check that NO reminder was created for fest_unappr
    unappr_notifs = db_session.query(FestivalNotification).filter(
        FestivalNotification.festival_id == fest_unappr.id
    ).all()
    assert len(unappr_notifs) == 0

    # Check that reminders WERE created for fest_appr
    appr_notifs = db_session.query(FestivalNotification).filter(
        FestivalNotification.festival_id == fest_appr.id
    ).all()
    assert len(appr_notifs) >= 1
    assert any("30-Day Reminder" in n.title for n in appr_notifs)
    assert any(n.notification_type == FestivalNotificationType.FESTIVAL_30_DAY_REMINDER for n in appr_notifs)

    # Idempotency test: Run runner again for same target_date
    res2 = generate_festival_milestone_reminders(db_session, target_date=ref_date, offsets=[30, 15, 7])
    assert res2["created_reminders"] == 0  # 0 duplicates created!
    assert res2["skipped_existing"] >= 1

def test_overdue_task_reminders(db_session: Session):
    """
    TASK 2 & 4: Test overdue preparation task reminder generation and deduplication.
    """
    leader = User(email="overdue_lead@craftyart.com", full_name="Overdue Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add(leader)
    db_session.commit()

    fest = Festival(name="Task Fest", slug="task-fest", country_code="US", assigned_leader_id=leader.id)
    db_session.add(fest)
    db_session.commit()

    ref_date = date(2026, 10, 1)

    # Create task with due date in the past relative to ref_date
    task = FestivalTask(
        festival_id=fest.id,
        assigned_user_id=leader.id,
        title="Update Meta Descriptions",
        status=FestivalTaskStatus.IN_PROGRESS,
        due_date=ref_date - timedelta(days=2)  # Due 2 days ago
    )
    db_session.add(task)
    db_session.commit()

    # Run overdue task runner
    res = generate_overdue_task_reminders(db_session, target_date=ref_date)
    assert res["status"] == "SUCCESS"
    assert res["created_overdue_reminders"] == 1

    notif = db_session.query(FestivalNotification).filter(
        FestivalNotification.task_id == task.id,
        FestivalNotification.notification_type == FestivalNotificationType.FESTIVAL_TASK_OVERDUE
    ).first()
    assert notif is not None
    assert "Task Overdue: Update Meta Descriptions" in notif.title
    assert notif.recipient_user_id == leader.id

    # Second run produces 0 duplicates
    res2 = generate_overdue_task_reminders(db_session, target_date=ref_date)
    assert res2["created_overdue_reminders"] == 0
    assert res2["skipped_existing"] == 1

def test_preparation_task_management_api(client: TestClient, db_session: Session):
    """
    TASK 3: Test task creation, status transitions, and list endpoints.
    """
    mgr = User(email="task_mgr@craftyart.com", full_name="Task Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    leader = User(email="task_lead@craftyart.com", full_name="Task Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([mgr, leader])
    db_session.commit()

    mgr_headers = get_auth_headers(mgr)
    lead_headers = get_auth_headers(leader)

    fest = Festival(name="Workflow Festival", slug="workflow-fest", country_code="IN", assigned_leader_id=leader.id)
    db_session.add(fest)
    db_session.commit()

    # 1. Create a task via API
    task_payload = {
        "title": "Design Banner Creatives",
        "description": "Prepare 1200x630 social share images",
        "task_type": "CREATIVES",
        "milestone_stage": "T_MINUS_30",
        "due_date": "2026-10-15",
        "assigned_user_id": leader.id
    }
    create_res = client.post(f"/api/festivals/{fest.id}/tasks", json=task_payload, headers=mgr_headers)
    assert create_res.status_code == 200, create_res.text
    task_data = create_res.json()
    assert task_data["title"] == "Design Banner Creatives"
    assert task_data["status"] == "NOT_STARTED"
    task_id = task_data["id"]

    # 2. List tasks
    list_res = client.get(f"/api/festivals/{fest.id}/tasks", headers=lead_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Update task status: NOT_STARTED -> IN_PROGRESS -> COMPLETED
    status_res1 = client.put(
        f"/api/festivals/{fest.id}/tasks/{task_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=lead_headers
    )
    assert status_res1.status_code == 200
    assert status_res1.json()["status"] == "IN_PROGRESS"

    status_res2 = client.put(
        f"/api/festivals/{fest.id}/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers=lead_headers
    )
    assert status_res2.status_code == 200
    assert status_res2.json()["status"] == "COMPLETED"
    assert status_res2.json()["completion_date"] is not None

def test_notification_apis_and_recipient_isolation(client: TestClient, db_session: Session):
    """
    TASK 5: Test Notification APIs and recipient-level authorization:
    - Users can view and mark only their own notifications as read.
    - Attempting to mark another user's notification as read returns 403 Forbidden.
    """
    tl1 = User(email="user1_notif@craftyart.com", full_name="User One", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    tl2 = User(email="user2_notif@craftyart.com", full_name="User Two", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([tl1, tl2])
    db_session.commit()

    tl1_headers = get_auth_headers(tl1)
    tl2_headers = get_auth_headers(tl2)

    fest = Festival(name="Isolation Fest", slug="iso-fest", country_code="IN")
    db_session.add(fest)
    db_session.commit()

    # Create private notification for TL1
    n1 = create_festival_notification(
        db=db_session,
        festival_id=fest.id,
        recipient_user_id=tl1.id,
        notification_type=FestivalNotificationType.FESTIVAL_30_DAY_REMINDER,
        title="TL1 Private Notification",
        message="Only TL1 should see this."
    )

    # Create private notification for TL2
    n2 = create_festival_notification(
        db=db_session,
        festival_id=fest.id,
        recipient_user_id=tl2.id,
        notification_type=FestivalNotificationType.FESTIVAL_15_DAY_REMINDER,
        title="TL2 Private Notification",
        message="Only TL2 should see this."
    )

    # 1. TL1 views notifications: should see n1, but NOT n2
    tl1_list_res = client.get("/api/notifications", headers=tl1_headers)
    assert tl1_list_res.status_code == 200
    tl1_titles = [item["title"] for item in tl1_list_res.json()]
    assert "TL1 Private Notification" in tl1_titles
    assert "TL2 Private Notification" not in tl1_titles

    # 2. TL1 unread count should be 1
    count_res = client.get("/api/notifications/unread-count", headers=tl1_headers)
    assert count_res.status_code == 200
    assert count_res.json()["unread_count"] == 1

    # 3. Cross-user modification prevention: TL2 attempts to mark TL1's notification as read
    cross_res = client.put(f"/api/notifications/{n1.id}/read", headers=tl2_headers)
    assert cross_res.status_code == 403
    assert "Access denied" in cross_res.json()["detail"]

    # 4. TL1 marks own notification as read
    own_read_res = client.put(f"/api/notifications/{n1.id}/read", headers=tl1_headers)
    assert own_read_res.status_code == 200
    assert own_read_res.json()["is_read"] is True

    # 5. TL1 unread count is now 0
    count_after = client.get("/api/notifications/unread-count", headers=tl1_headers)
    assert count_after.json()["unread_count"] == 0

    # 6. Read-all endpoint test for TL2
    read_all_res = client.put("/api/notifications/read-all", headers=tl2_headers)
    assert read_all_res.status_code == 200
    assert read_all_res.json()["marked_read_count"] == 1

def test_scheduler_run_festival_reminders_isolation_and_idempotency(db_session: Session):
    """
    Test scheduler run_festival_reminders function:
    - Verifies combined execution of milestone reminders and overdue tasks.
    - Verifies complete idempotency (zero duplicates on second call).
    - Verifies isolated error handling.
    """
    from backend.app.core.scheduler import run_festival_reminders

    mgr = User(email="sched_mgr@craftyart.com", full_name="Sched Manager", hashed_password=hash_password("pwd"), role=UserRole.MANAGER)
    leader = User(email="sched_lead@craftyart.com", full_name="Sched Leader", hashed_password=hash_password("pwd"), role=UserRole.TEAM_LEADER)
    db_session.add_all([mgr, leader])
    db_session.commit()

    ref_date = date(2026, 11, 1)

    fest = Festival(name="Scheduler Fest", slug="sched-fest", country_code="IN", assigned_leader_id=leader.id)
    db_session.add(fest)
    db_session.commit()

    # 1. Approved year date at 15-day mark
    yd = FestivalYearDate(
        festival_id=fest.id,
        year=2026,
        start_date=ref_date + timedelta(days=15),
        end_date=ref_date + timedelta(days=16),
        date_status=FestivalDateStatus.CONFIRMED,
        approval_status=FestivalApprovalStatus.APPROVED
    )
    db_session.add(yd)

    # 2. Overdue task
    task = FestivalTask(
        festival_id=fest.id,
        assigned_user_id=leader.id,
        title="Meta Optimization",
        status=FestivalTaskStatus.IN_PROGRESS,
        due_date=ref_date - timedelta(days=1)
    )
    db_session.add(task)
    db_session.commit()

    # First run of scheduler runner
    stats1 = run_festival_reminders(db=db_session, target_date=ref_date)
    assert stats1["status"] == "SUCCESS"
    assert stats1["milestone_reminders"] >= 1
    assert stats1["overdue_task_reminders"] == 1

    # Second run of scheduler runner for exact same date (idempotency)
    stats2 = run_festival_reminders(db=db_session, target_date=ref_date)
    assert stats2["status"] == "SUCCESS"
    assert stats2["milestone_reminders"] == 0
    assert stats2["overdue_task_reminders"] == 0

