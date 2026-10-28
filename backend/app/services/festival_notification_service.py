from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status

from backend.app.models.models import User, UserRole, utc_now
from backend.app.models.festival_models import (
    Festival, FestivalYearDate, FestivalTask, FestivalNotification,
    FestivalNotificationType, FestivalTaskStatus, FestivalApprovalStatus,
    FestivalDateStatus
)

def create_festival_notification(
    db: Session,
    festival_id: int,
    notification_type: str,
    title: str,
    message: str,
    recipient_user_id: Optional[int] = None,
    action_url: Optional[str] = None,
    year_date_id: Optional[int] = None,
    task_id: Optional[int] = None,
    dedup_key: Optional[str] = None
) -> Optional[FestivalNotification]:
    """
    Creates a dashboard notification with deduplication.
    Only creates dashboard notifications (no email, SMS, or WhatsApp).
    If dedup_key exists, safely returns existing record without duplicating.
    """
    if dedup_key:
        existing = db.query(FestivalNotification).filter(
            FestivalNotification.dedup_key == dedup_key
        ).first()
        if existing:
            return existing

    notif = FestivalNotification(
        recipient_user_id=recipient_user_id,
        festival_id=festival_id,
        year_date_id=year_date_id,
        task_id=task_id,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        is_read=False,
        dedup_key=dedup_key,
        created_at=utc_now()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

def list_user_notifications(
    db: Session,
    current_user: User,
    is_read: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> List[FestivalNotification]:
    """
    List persistent dashboard notifications for current user with strict recipient isolation.
    Users cannot view notifications addressed to other users.
    Managers can view their notifications as well as broadcast (recipient_user_id IS NULL) notifications.
    """
    query = db.query(FestivalNotification)
    
    if current_user.role == UserRole.MANAGER:
        query = query.filter(
            or_(
                FestivalNotification.recipient_user_id == current_user.id,
                FestivalNotification.recipient_user_id == None
            )
        )
    else:
        query = query.filter(FestivalNotification.recipient_user_id == current_user.id)

    if is_read is not None:
        query = query.filter(FestivalNotification.is_read == is_read)

    return query.order_by(FestivalNotification.created_at.desc()).offset(offset).limit(limit).all()

def get_unread_notification_count(
    db: Session,
    current_user: User
) -> int:
    """Returns the unread notification count for the current user."""
    query = db.query(func.count(FestivalNotification.id)).filter(FestivalNotification.is_read == False)
    if current_user.role == UserRole.MANAGER:
        query = query.filter(
            or_(
                FestivalNotification.recipient_user_id == current_user.id,
                FestivalNotification.recipient_user_id == None
            )
        )
    else:
        query = query.filter(FestivalNotification.recipient_user_id == current_user.id)
    return query.scalar() or 0

def mark_notification_as_read(
    db: Session,
    notification_id: int,
    current_user: User
) -> FestivalNotification:
    """
    Marks a single notification as read.
    Enforces authorization: Users can only mark their own notifications as read.
    """
    notif = db.query(FestivalNotification).filter(FestivalNotification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    # Authorization barrier:
    is_authorized = (
        notif.recipient_user_id == current_user.id or
        (notif.recipient_user_id is None and current_user.role == UserRole.MANAGER)
    )
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to modify this notification."
        )

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = utc_now()
        db.commit()
        db.refresh(notif)
    return notif

def mark_all_notifications_as_read(
    db: Session,
    current_user: User
) -> int:
    """Marks all unread notifications for the current user as read."""
    query = db.query(FestivalNotification).filter(FestivalNotification.is_read == False)
    if current_user.role == UserRole.MANAGER:
        query = query.filter(
            or_(
                FestivalNotification.recipient_user_id == current_user.id,
                FestivalNotification.recipient_user_id == None
            )
        )
    else:
        query = query.filter(FestivalNotification.recipient_user_id == current_user.id)

    unreads = query.all()
    now = utc_now()
    count = 0
    for n in unreads:
        n.is_read = True
        n.read_at = now
        count += 1
    if count > 0:
        db.commit()
    return count

# ----------------- AUTOMATED REMINDER GENERATION -----------------

def generate_festival_milestone_reminders(
    db: Session,
    target_date: Optional[date] = None,
    offsets: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Idempotent reminder generation runner for 30, 15, and 7 days before festivals.
    
    Safety & Business Rules:
    - Only sends reminders for APPROVED festival year dates.
      Unapproved, pending, or rejected dates produce ZERO reminders.
    - Uses dedup_key to prevent duplicate notifications if scheduler runs repeatedly.
    - Creates dashboard-only notifications (never sends email, SMS, or WhatsApp).
    - Can be triggered manually or by an external scheduler runner.
    """
    if target_date is None:
        target_date = date.today()
    if offsets is None:
        offsets = [30, 15, 7]

    # Query only approved editions of active festivals
    approved_year_dates = (
        db.query(FestivalYearDate)
        .join(Festival, FestivalYearDate.festival_id == Festival.id)
        .filter(
            Festival.is_active == True,
            FestivalYearDate.approval_status == FestivalApprovalStatus.APPROVED
        )
        .all()
    )

    # Collect managers for oversight reminders
    managers = db.query(User).filter(User.role == UserRole.MANAGER, User.is_active == True).all()

    created_count = 0
    skipped_existing = 0

    for yd in approved_year_dates:
        fest = yd.festival
        days_until = (yd.start_date - target_date).days

        if days_until in offsets:
            notification_type = getattr(
                FestivalNotificationType,
                f"FESTIVAL_{days_until}_DAY_REMINDER",
                FestivalNotificationType.FESTIVAL_30_DAY_REMINDER
            )

            # Determine recipients: Assigned Leader + Managers
            recipients: List[User] = []
            if fest.assigned_leader_id:
                leader = db.query(User).filter(User.id == fest.assigned_leader_id, User.is_active == True).first()
                if leader:
                    recipients.append(leader)
            
            # Add managers
            for m in managers:
                if m not in recipients:
                    recipients.append(m)

            for user in recipients:
                dedup_key = f"reminder_fest_{fest.id}_yd_{yd.id}_offset_{days_until}_user_{user.id}"
                
                # Check idempotency
                existing = db.query(FestivalNotification).filter(
                    FestivalNotification.dedup_key == dedup_key
                ).first()
                if existing:
                    skipped_existing += 1
                    continue

                title = f"{days_until}-Day Reminder: {fest.name} ({yd.year})"
                message = f"{fest.name} starts in {days_until} days on {yd.start_date.isoformat()}. Complete preparation tasks and verify landing page rankings."
                action_url = f"/festivals/{fest.id}"

                notif = FestivalNotification(
                    recipient_user_id=user.id,
                    festival_id=fest.id,
                    year_date_id=yd.id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    action_url=action_url,
                    is_read=False,
                    dedup_key=dedup_key,
                    created_at=utc_now()
                )
                db.add(notif)
                created_count += 1

    if created_count > 0:
        db.commit()

    return {
        "status": "SUCCESS",
        "target_date": target_date.isoformat(),
        "created_reminders": created_count,
        "skipped_existing": skipped_existing
    }

def generate_overdue_task_reminders(
    db: Session,
    target_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Idempotent reminder generation for overdue festival preparation tasks.
    """
    if target_date is None:
        target_date = date.today()

    overdue_tasks = (
        db.query(FestivalTask)
        .join(Festival, FestivalTask.festival_id == Festival.id)
        .filter(
            Festival.is_active == True,
            FestivalTask.status != FestivalTaskStatus.COMPLETED,
            FestivalTask.due_date != None,
            FestivalTask.due_date < target_date
        )
        .all()
    )

    created_count = 0
    skipped_existing = 0

    for task in overdue_tasks:
        fest = task.festival
        # Recipients: assigned user or festival leader
        recipient_id = task.assigned_user_id or fest.assigned_leader_id
        if not recipient_id:
            continue

        dedup_key = f"task_overdue_{task.id}_due_{task.due_date.isoformat()}_user_{recipient_id}"
        existing = db.query(FestivalNotification).filter(
            FestivalNotification.dedup_key == dedup_key
        ).first()
        if existing:
            skipped_existing += 1
            continue

        title = f"Task Overdue: {task.title}"
        message = f"Task '{task.title}' for festival '{fest.name}' was due on {task.due_date.isoformat()} and is currently {task.status}."
        action_url = f"/festivals/{fest.id}/tasks"

        notif = FestivalNotification(
            recipient_user_id=recipient_id,
            festival_id=fest.id,
            year_date_id=task.festival_year_date_id,
            task_id=task.id,
            notification_type=FestivalNotificationType.FESTIVAL_TASK_OVERDUE,
            title=title,
            message=message,
            action_url=action_url,
            is_read=False,
            dedup_key=dedup_key,
            created_at=utc_now()
        )
        db.add(notif)
        created_count += 1

    if created_count > 0:
        db.commit()

    return {
        "status": "SUCCESS",
        "target_date": target_date.isoformat(),
        "created_overdue_reminders": created_count,
        "skipped_existing": skipped_existing
    }
