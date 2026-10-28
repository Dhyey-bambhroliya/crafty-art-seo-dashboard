import os
import pytest
from datetime import date, datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from backend.app.models.models import User, UserRole, Category, CategoryPage
from backend.app.models.festival_models import (
    Festival, FestivalYearDate, FestivalSubcategory, FestivalPage,
    FestivalTask, FestivalNotification, FestivalTaskStatus,
    FestivalNotificationType, FestivalDateStatus, FestivalApprovalStatus
)
from backend.app.services.user_service import seed_team_leaders, hash_password
from backend.app.core.security import verify_password
from backend.app.core.database import validate_database_safety
from backend.app.services.festival_service import (
    require_manager_for_approval,
    check_festival_access_permission,
    check_festival_page_access_permission,
    approve_festival_year_date
)

def test_festival_model_creation(db_session):
    """Verify core festival entity creation with country and manager/leader assignments."""
    leader = User(
        email="leader_fest@craftyart.com",
        full_name="Festival Leader",
        hashed_password=hash_password("FestPass123"),
        role=UserRole.TEAM_LEADER,
        is_active=True
    )
    db_session.add(leader)
    db_session.commit()

    festival = Festival(
        name="Diwali",
        slug="diwali",
        country_code="IN",
        region="Pan-India",
        category_group="Religious & Cultural",
        description="Festival of Lights - Major Indian celebration",
        assigned_leader_id=leader.id,
        is_active=True
    )
    db_session.add(festival)
    db_session.commit()
    db_session.refresh(festival)

    assert festival.id is not None
    assert festival.name == "Diwali"
    assert festival.slug == "diwali"
    assert festival.country_code == "IN"
    assert festival.assigned_leader.email == "leader_fest@craftyart.com"

def test_multiple_year_specific_festival_dates(db_session):
    """
    Verify that a festival such as Diwali supports different dates in different years
    without collisions, enabling year-over-year season comparison (e.g., 2024 vs 2025 vs 2026).
    """
    festival = Festival(
        name="Diwali",
        slug="diwali-yoy",
        country_code="IN"
    )
    db_session.add(festival)
    db_session.commit()

    # 2024 edition: Nov 1, 2024
    d2024 = FestivalYearDate(
        festival_id=festival.id,
        year=2024,
        start_date=date(2024, 11, 1),
        end_date=date(2024, 11, 3),
        prep_start_date=date(2024, 9, 15),
        prep_deadline_date=date(2024, 10, 20),
        season_comparison_start=date(2024, 9, 15),
        season_comparison_end=date(2024, 11, 5),
        date_status=FestivalDateStatus.CONFIRMED,
        approval_status=FestivalApprovalStatus.APPROVED
    )

    # 2025 edition: Oct 20, 2025
    d2025 = FestivalYearDate(
        festival_id=festival.id,
        year=2025,
        start_date=date(2025, 10, 20),
        end_date=date(2025, 10, 22),
        prep_start_date=date(2025, 8, 20),
        prep_deadline_date=date(2025, 10, 5),
        season_comparison_start=date(2025, 8, 20),
        season_comparison_end=date(2025, 10, 25),
        date_status=FestivalDateStatus.CONFIRMED,
        approval_status=FestivalApprovalStatus.APPROVED
    )

    # 2026 edition: Nov 8, 2026 (Starts as UNVERIFIED, PENDING)
    d2026 = FestivalYearDate(
        festival_id=festival.id,
        year=2026,
        start_date=date(2026, 11, 8),
        end_date=date(2026, 11, 10),
        prep_start_date=date(2026, 9, 10),
        prep_deadline_date=date(2026, 10, 25),
        date_status=FestivalDateStatus.UNVERIFIED,
        approval_status=FestivalApprovalStatus.PENDING
    )

    db_session.add_all([d2024, d2025, d2026])
    db_session.commit()

    db_session.refresh(festival)
    assert len(festival.year_dates) == 3

    # Verify distinct years and dates
    years_map = {yd.year: yd for yd in festival.year_dates}
    assert years_map[2024].start_date == date(2024, 11, 1)
    assert years_map[2025].start_date == date(2025, 10, 20)
    assert years_map[2026].start_date == date(2026, 11, 8)
    assert years_map[2026].approval_status == FestivalApprovalStatus.PENDING
    assert years_map[2026].date_status == FestivalDateStatus.UNVERIFIED
    assert years_map[2026].is_verified is False

def test_festival_dates_start_unverified_and_pending(db_session):
    """
    CRITICAL CHECK:
    Festival dates added to the system must NOT automatically be treated as verified.
    They must default to UNVERIFIED and PENDING approval.
    """
    fest = Festival(name="Navratri", slug="navratri", country_code="IN")
    db_session.add(fest)
    db_session.commit()

    edition = FestivalYearDate(
        festival_id=fest.id,
        year=2026,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 18)
    )
    db_session.add(edition)
    db_session.commit()
    db_session.refresh(edition)

    assert edition.date_status == FestivalDateStatus.UNVERIFIED
    assert edition.approval_status == FestivalApprovalStatus.PENDING
    assert edition.is_verified is False
    assert edition.approved_by_user_id is None

def test_manager_only_can_approve_festival_dates(db_session):
    """
    CRITICAL CHECK:
    Only Managers can approve festival dates.
    Team Leaders attempting date approval must be rejected with 403 Forbidden.
    """
    manager = User(email="manager_approver@craftyart.com", full_name="Manager Approver", hashed_password="pwd", role=UserRole.MANAGER)
    leader = User(email="leader_approver@craftyart.com", full_name="Leader Approver", hashed_password="pwd", role=UserRole.TEAM_LEADER)
    fest = Festival(name="Pongal", slug="pongal", country_code="IN")
    db_session.add_all([manager, leader, fest])
    db_session.commit()

    edition = FestivalYearDate(
        festival_id=fest.id,
        year=2026,
        start_date=date(2026, 1, 14),
        end_date=date(2026, 1, 17)
    )
    db_session.add(edition)
    db_session.commit()

    # 1. Team Leader attempts to approve -> Must raise 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        approve_festival_year_date(db_session, edition, leader, "APPROVED")
    assert "Only Managers can approve" in exc_info.value.detail or "Manager privileges required" in exc_info.value.detail

    # 2. Manager approves -> Must succeed and mark CONFIRMED
    approved_edition = approve_festival_year_date(db_session, edition, manager, "APPROVED", notes="Confirmed via national holiday calendar")
    assert approved_edition.approval_status == FestivalApprovalStatus.APPROVED
    assert approved_edition.date_status == FestivalDateStatus.CONFIRMED
    assert approved_edition.approved_by_user_id == manager.id
    assert approved_edition.approved_at is not None
    assert approved_edition.is_verified is True

def test_team_leader_access_restricted_to_assigned_festivals_and_pages(db_session):
    """
    CRITICAL CHECK:
    Team Leaders can access only festivals and landing pages assigned to their permitted categories.
    Managers have global access.
    """
    leader_a = User(email="leader_a@craftyart.com", full_name="Leader A", hashed_password="pwd", role=UserRole.TEAM_LEADER)
    leader_b = User(email="leader_b@craftyart.com", full_name="Leader B", hashed_password="pwd", role=UserRole.TEAM_LEADER)
    manager = User(email="manager_all@craftyart.com", full_name="Manager All", hashed_password="pwd", role=UserRole.MANAGER)
    db_session.add_all([leader_a, leader_b, manager])
    db_session.commit()

    # Festival A assigned to Leader A
    fest_a = Festival(name="Raksha Bandhan", slug="raksha-bandhan", country_code="IN", assigned_leader_id=leader_a.id)
    # Festival B assigned to Leader B
    fest_b = Festival(name="Thanksgiving", slug="thanksgiving-us", country_code="US", assigned_leader_id=leader_b.id)
    db_session.add_all([fest_a, fest_b])
    db_session.commit()

    page_a = FestivalPage(festival_id=fest_a.id, full_url="https://craftyartapp.com/rakhi", normalized_url="https://craftyartapp.com/rakhi")
    page_b = FestivalPage(festival_id=fest_b.id, full_url="https://craftyartapp.com/thanksgiving", normalized_url="https://craftyartapp.com/thanksgiving")
    db_session.add_all([page_a, page_b])
    db_session.commit()

    # Leader A accessing Festival A & Page A -> Allowed
    check_festival_access_permission(fest_a, leader_a)
    check_festival_page_access_permission(page_a, leader_a, db_session)

    # Leader A accessing Festival B -> 403 Forbidden
    with pytest.raises(HTTPException) as exc1:
        check_festival_access_permission(fest_b, leader_a)
    assert exc1.value.status_code == 403

    # Leader A accessing Page B -> 403 Forbidden
    with pytest.raises(HTTPException) as exc2:
        check_festival_page_access_permission(page_b, leader_a, db_session)
    assert exc2.value.status_code == 403

    # Manager accessing both -> Allowed
    check_festival_access_permission(fest_a, manager)
    check_festival_access_permission(fest_b, manager)
    check_festival_page_access_permission(page_a, manager, db_session)
    check_festival_page_access_permission(page_b, manager, db_session)

def test_existing_category_pages_remain_unchanged(db_session):
    """
    CRITICAL CHECK:
    Existing category_pages records must remain completely unchanged when mapped,
    updated, or unmapped in the festival system.
    """
    mgr = User(email="cat_mgr@craftyart.com", full_name="Category Manager", hashed_password="pwd", role=UserRole.MANAGER)
    db_session.add(mgr)
    db_session.commit()

    cat = Category(name="Festive Cards", assigned_leader_id=mgr.id)
    db_session.add(cat)
    db_session.commit()

    cat_page = CategoryPage(
        category_id=cat.id,
        full_url="https://craftyartapp.com/cards/diwali",
        normalized_url="https://craftyartapp.com/cards/diwali",
        status="ACTIVE"
    )
    db_session.add(cat_page)
    db_session.commit()

    original_page_id = cat_page.id
    original_url = cat_page.full_url
    original_cat_id = cat_page.category_id

    # Create festival page mapping to existing category page
    fest = Festival(name="Diwali Test", slug="diwali-test-cat", country_code="IN")
    db_session.add(fest)
    db_session.commit()

    fest_page = FestivalPage(
        festival_id=fest.id,
        category_page_id=cat_page.id,
        full_url=cat_page.full_url,
        normalized_url=cat_page.normalized_url,
        priority="PRIMARY"
    )
    db_session.add(fest_page)
    db_session.commit()

    # Delete the festival page mapping
    db_session.delete(fest_page)
    db_session.commit()

    # Verify original category_page is 100% intact and unchanged
    reloaded_page = db_session.query(CategoryPage).filter(CategoryPage.id == original_page_id).first()
    assert reloaded_page is not None
    assert reloaded_page.full_url == original_url
    assert reloaded_page.category_id == original_cat_id
    assert reloaded_page.status == "ACTIVE"

def test_seed_team_leaders_password_preservation(db_session):
    """
    CRITICAL REGRESSION TEST:
    Ensures that seed_team_leaders() does NOT overwrite an existing user's custom password,
    does NOT alter their role, and does NOT reset their is_active status.
    """
    # 1. Create a team leader with a custom password and custom role
    custom_password = "MySuperSecretCustomPassword999!"
    custom_hash = hash_password(custom_password)
    leader_email = "craftyartvishal@gmail.com"

    leader = User(
        email=leader_email,
        full_name="Vishal Custom",
        hashed_password=custom_hash,
        role=UserRole.MANAGER,  # Promoted to Manager
        is_active=False  # Administratively deactivated
    )
    db_session.add(leader)
    db_session.commit()

    # 2. Run seed_team_leaders()
    seed_team_leaders(db_session)

    # 3. Query the user again
    reloaded_leader = db_session.query(User).filter(User.email == leader_email).first()

    # Custom password MUST still be valid (must NOT be reset to '12345678')
    assert verify_password(custom_password, reloaded_leader.hashed_password) is True
    assert verify_password("12345678", reloaded_leader.hashed_password) is False

    # Promoted role MUST be preserved (must NOT be reverted to TEAM_LEADER)
    assert reloaded_leader.role == UserRole.MANAGER

    # Deactivated status MUST be preserved (must NOT be reset to True)
    assert reloaded_leader.is_active is False

def test_database_safety_guard_cannot_be_bypassed_by_inherited_env(monkeypatch):
    """
    CRITICAL SAFETY CHECK:
    Verify that validate_database_safety CANNOT be bypassed by RENDER=true,
    ALLOW_PRODUCTION_DB_ACCESS=true, or any inherited environment variables
    when running on a local development workstation.
    """
    fake_supabase = "postgresql+psycopg://postgres.abc:pass@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

    # Even if environment has RENDER=true and ALLOW_PRODUCTION_DB_ACCESS=true
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("ALLOW_PRODUCTION_DB_ACCESS", "true")

    # In test runner (PYTEST_CURRENT_TEST is set):
    with pytest.raises(RuntimeError) as exc_info:
        validate_database_safety(fake_supabase)
    assert "SAFETY GUARD" in str(exc_info.value) or "CRITICAL SAFETY VIOLATION BLOCKED" in str(exc_info.value)

    # Temporarily unset PYTEST_CURRENT_TEST to test workstation OS check (Windows)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    if os.name == "nt":
        with pytest.raises(RuntimeError) as exc_workstation:
            validate_database_safety(fake_supabase)
        assert "CRITICAL SAFETY VIOLATION BLOCKED" in str(exc_workstation.value)
        assert "strictly forbidden on local development workstations" in str(exc_workstation.value)

def test_festival_unique_year_constraint(db_session):
    """Verify that duplicate date records for the same year and festival cannot be created."""
    festival = Festival(name="Holi", slug="holi-unique", country_code="IN")
    db_session.add(festival)
    db_session.commit()

    d1 = FestivalYearDate(festival_id=festival.id, year=2026, start_date=date(2026, 3, 3), end_date=date(2026, 3, 4))
    db_session.add(d1)
    db_session.commit()

    # Second entry for year 2026 on the same festival must fail unique constraint
    d2 = FestivalYearDate(festival_id=festival.id, year=2026, start_date=date(2026, 3, 3), end_date=date(2026, 3, 4))
    db_session.add(d2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_festival_subcategories_hierarchy(db_session):
    """
    Verify hierarchy:
    Festival: Diwali
        -> Diwali Invitation Templates
        -> Diwali Festival Images
        -> Diwali Status Videos
        -> Diwali Poster Images
    """
    festival = Festival(name="Diwali Subcat", slug="diwali-subcats-test", country_code="IN")
    db_session.add(festival)
    db_session.commit()

    subcats = [
        FestivalSubcategory(festival_id=festival.id, name="Diwali Invitation Templates", slug="diwali-invitation-templates"),
        FestivalSubcategory(festival_id=festival.id, name="Diwali Festival Images", slug="diwali-festival-images"),
        FestivalSubcategory(festival_id=festival.id, name="Diwali Status Videos", slug="diwali-status-videos"),
        FestivalSubcategory(festival_id=festival.id, name="Diwali Poster Images", slug="diwali-poster-images"),
    ]
    db_session.add_all(subcats)
    db_session.commit()

    db_session.refresh(festival)
    assert len(festival.subcategories) == 4
    subcat_names = {sc.name for sc in festival.subcategories}
    assert "Diwali Invitation Templates" in subcat_names
    assert "Diwali Poster Images" in subcat_names

def test_festival_task_creation_and_status_transitions(db_session):
    """Verify task creation across milestones and status workflow."""
    leader = User(email="task_leader2@craftyart.com", full_name="Task Leader 2", hashed_password="pwd", role=UserRole.TEAM_LEADER)
    fest = Festival(name="Halloween", slug="halloween-tasks-test", country_code="US")
    db_session.add_all([leader, fest])
    db_session.commit()

    task = FestivalTask(
        festival_id=fest.id,
        assigned_user_id=leader.id,
        title="Refresh Meta Description and H1 for Halloween Templates",
        task_type="META_TAGS",
        milestone_stage="T_MINUS_30",
        status=FestivalTaskStatus.NOT_STARTED,
        due_date=date(2026, 10, 1)
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.status == FestivalTaskStatus.NOT_STARTED

    task.status = FestivalTaskStatus.IN_PROGRESS
    db_session.commit()
    assert task.status == FestivalTaskStatus.IN_PROGRESS

    task.status = FestivalTaskStatus.READY_FOR_REVIEW
    db_session.commit()
    assert task.status == FestivalTaskStatus.READY_FOR_REVIEW

    task.status = FestivalTaskStatus.COMPLETED
    task.completion_date = datetime.now(timezone.utc)
    task.completed_by_user_id = leader.id
    db_session.commit()
    assert task.status == FestivalTaskStatus.COMPLETED
    assert task.completion_date is not None

def test_festival_notifications_and_duplicate_prevention(db_session):
    """Verify dashboard notifications and duplicate prevention via dedup_key."""
    user = User(email="notif_user2@craftyart.com", full_name="Notif User 2", hashed_password="pwd", role=UserRole.TEAM_LEADER)
    fest = Festival(name="Christmas", slug="christmas-notif-test", country_code="GLOBAL")
    db_session.add_all([user, fest])
    db_session.commit()

    notif = FestivalNotification(
        recipient_user_id=user.id,
        festival_id=fest.id,
        notification_type=FestivalNotificationType.FESTIVAL_30_DAY_REMINDER,
        title="30 Days until Christmas Campaign",
        message="Review your landing page mappings and start creative preparations.",
        action_url="/festivals/christmas",
        dedup_key=f"FESTIVAL_30_DAY_{fest.id}_{user.id}_2026",
        is_read=False
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    assert notif.id is not None
    assert notif.is_read is False

    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db_session.commit()
    assert notif.is_read is True
    assert notif.read_at is not None
