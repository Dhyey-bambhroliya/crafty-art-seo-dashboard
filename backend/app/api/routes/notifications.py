from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import User
from backend.app.schemas.festival_schemas import (
    FestivalNotificationOut, UnreadCountResponse
)
from backend.app.api.deps import get_current_user
from backend.app.services.festival_notification_service import (
    list_user_notifications,
    get_unread_notification_count,
    mark_notification_as_read,
    mark_all_notifications_as_read
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

def format_notification_out(notif) -> FestivalNotificationOut:
    return FestivalNotificationOut(
        id=notif.id,
        recipient_user_id=notif.recipient_user_id,
        festival_id=notif.festival_id,
        festival_name=notif.festival.name if notif.festival else None,
        notification_type=notif.notification_type,
        title=notif.title,
        message=notif.message,
        action_url=notif.action_url,
        is_read=notif.is_read,
        created_at=notif.created_at,
        read_at=notif.read_at
    )

@router.get("", response_model=List[FestivalNotificationOut])
def get_notifications(
    is_read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List persistent dashboard notifications for current user with recipient-level authorization.
    Users cannot view other users' notifications.
    """
    notifs = list_user_notifications(db, current_user, is_read=is_read, limit=limit, offset=offset)
    return [format_notification_out(n) for n in notifs]

@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the unread notification count for the Notification Bell badge."""
    count = get_unread_notification_count(db, current_user)
    return UnreadCountResponse(unread_count=count)

@router.put("/{notification_id}/read", response_model=FestivalNotificationOut)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a specific notification as read.
    Enforces authorization: Users cannot modify another user's notification.
    """
    notif = mark_notification_as_read(db, notification_id, current_user)
    return format_notification_out(notif)

@router.put("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all unread notifications for current user as read."""
    updated_count = mark_all_notifications_as_read(db, current_user)
    return {"status": "SUCCESS", "marked_read_count": updated_count}
