"""
Push notification service.

Sends Web Push notifications using VAPID keys stored in environment variables.
Supports morning coaching nudge and evening reflection reminder.

Schedule (external cron calls these endpoints daily):
  POST /push/send-morning  — 8 AM user's local time
  POST /push/send-evening  — 7 PM user's local time
"""

import json
import logging
import os
from datetime import datetime, timezone

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.models import PushSubscription

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS = {"sub": "mailto:joshijeet02@gmail.com"}

MORNING_MESSAGES = [
    ("Good morning ☀️", "Your coach is ready. What will you make of today?"),
    ("Morning check-in 🧘", "Take 30 seconds to set your energy for the day."),
    ("Rise and lead 🎯", "Your sprint goals are waiting. Let's make progress."),
    ("Good morning 💪", "Yesterday's wins fuel today's momentum. Check in."),
    ("New day, fresh start 🌅", "Your coach has a morning brief ready for you."),
    ("Morning, leader 🔥", "Your habits, your energy, your day — check in now."),
    ("Ready for today? ⚡", "A quick check-in keeps your coach calibrated."),
]

EVENING_MESSAGES = [
    ("End of day reflection 🌙", "How did you show up today? Your coach is listening."),
    ("Evening check-in 💭", "Name one win before the day is done."),
    ("Wind down 🌙", "A 30-second reflection now saves you hours of regret later."),
    ("Day review 📊", "What moved the needle today? Log it before you forget."),
    ("Evening nudge 🌙", "Your coach wants to know: what happened today?"),
]


def _get_message(messages: list, date: str) -> tuple[str, str]:
    """Pick a message deterministically by date so it varies day-to-day."""
    idx = int(date.replace("-", "")) % len(messages)
    return messages[idx]


def send_push_to_subscription(
    sub: PushSubscription, title: str, body: str, url: str = "/"
) -> bool:
    """Send a single push notification. Returns True on success."""
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID_PRIVATE_KEY not set — push not sent")
        return False

    subscription_info = {
        "endpoint": sub.endpoint,
        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
    }
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        return True
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else "?"
        logger.warning("Push failed (HTTP %s) for endpoint %s: %s", status, sub.endpoint[:40], e)
        # 410 Gone = subscription expired; caller should delete it
        if e.response is not None and e.response.status_code in (404, 410):
            return None  # signal: delete this subscription
        return False


def send_morning_notifications(db: Session) -> dict:
    """
    Send morning nudge to all subscribers who haven't received one today.
    Called by POST /push/send-morning (external cron).
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title, body = _get_message(MORNING_MESSAGES, today)

    subs = db.query(PushSubscription).filter(
        PushSubscription.last_morning_sent != today
    ).all()

    sent, failed, expired = 0, 0, 0
    for sub in subs:
        result = send_push_to_subscription(sub, title, body, url="/")
        if result is True:
            sub.last_morning_sent = today
            sent += 1
        elif result is None:
            # Expired subscription — remove it
            db.delete(sub)
            expired += 1
        else:
            failed += 1

    db.commit()
    logger.info("Morning notifications: sent=%d failed=%d expired=%d", sent, failed, expired)
    return {"sent": sent, "failed": failed, "expired_removed": expired, "date": today}


def send_evening_notifications(db: Session) -> dict:
    """
    Send evening reflection reminder to all subscribers who haven't received one today.
    Called by POST /push/send-evening (external cron).
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title, body = _get_message(EVENING_MESSAGES, today)

    subs = db.query(PushSubscription).filter(
        PushSubscription.last_evening_sent != today
    ).all()

    sent, failed, expired = 0, 0, 0
    for sub in subs:
        result = send_push_to_subscription(sub, title, body, url="/")
        if result is True:
            sub.last_evening_sent = today
            sent += 1
        elif result is None:
            db.delete(sub)
            expired += 1
        else:
            failed += 1

    db.commit()
    logger.info("Evening notifications: sent=%d failed=%d expired=%d", sent, failed, expired)
    return {"sent": sent, "failed": failed, "expired_removed": expired, "date": today}


def save_subscription(db: Session, user_id: str, endpoint: str, p256dh: str, auth: str, user_agent: str = "") -> PushSubscription:
    """Upsert a push subscription (update if endpoint exists, create otherwise)."""
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint
    ).first()

    if existing:
        existing.user_id = user_id
        existing.p256dh = p256dh
        existing.auth = auth
        existing.user_agent = user_agent
        db.commit()
        return existing

    sub = PushSubscription(
        user_id=user_id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def delete_subscription(db: Session, endpoint: str) -> bool:
    """Remove a subscription (user unsubscribed)."""
    sub = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint
    ).first()
    if sub:
        db.delete(sub)
        db.commit()
        return True
    return False


def get_subscription_count(db: Session, user_id: str) -> int:
    return db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).count()
