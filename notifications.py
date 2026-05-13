from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Notification, User
from auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def serialize_notification(n: Notification) -> dict:
    return {
        "id":         n.id,
        "kind":       n.kind,
        "is_read":    n.is_read,
        "created_at": n.created_at.isoformat(),
        "tweet_id":   n.tweet_id,
        "actor": {
            "id":           n.actor.id,
            "username":     n.actor.username,
            "display_name": n.actor.display_name,
            "avatar_url":   n.actor.avatar_url,
        } if n.actor else None,
    }


def create_notification(
    db:           Session,
    recipient_id: int,
    actor_id:     int,
    kind:         str,
    tweet_id:     int = None
):
    # Don't notify yourself
    if recipient_id == actor_id:
        return

    notif = Notification(
        recipient_id = recipient_id,
        actor_id     = actor_id,
        kind         = kind,
        tweet_id     = tweet_id,
    )
    db.add(notif)
    db.commit()
    return notif


# --- Get my notifications ----====--

@router.get("/")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notifs = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [serialize_notification(n) for n in notifs]


# --- Get unread count ----====------

@router.get("/unread")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    count = db.query(Notification).filter(
        Notification.recipient_id == current_user.id,
        Notification.is_read      == False
    ).count()
    return {"unread": count}


# --- Mark all as read ----====------

@router.post("/read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Notification).filter(
        Notification.recipient_id == current_user.id,
        Notification.is_read      == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


# --- Mark one as read ----====------

@router.post("/{notif_id}/read")
def mark_one_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(
        Notification.id           == notif_id,
        Notification.recipient_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"message": "Marked as read"}