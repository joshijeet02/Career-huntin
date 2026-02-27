"""
HealthKit Integration
======================
The most elite coaching clients pay for objective data, not just self-reported feelings.

HealthKit gives the coach ground truth:
  - Did they actually sleep 7 hours, or did they say they did?
  - Is their HRV (heart rate variability) dropping — the earliest sign of overtraining or burnout?
  - Are their steps correlated with their energy score? (They almost always are.)
  - Did they take their mindfulness minutes when they said they did?

When HealthKit data is available, the coach references it specifically and honestly:
  "Your Apple Watch shows HRV dropped from 45ms to 28ms over the last 5 days.
   Your body was signalling stress before you felt it. Let's talk about what happened that week."

Architecture:
  - iOS app reads HealthKit data (with user permission)
  - Sends it to POST /health/data daily (background task, no user friction)
  - Backend stores it in HealthData model
  - Morning Brief, Check-In, and Pattern Recognition all pull this data
  - The coach never says "according to your watch" — it speaks as if it knows

Privacy principle:
  - Health data is stored per user, never aggregated, never used for anything except
    coaching that specific user.
  - If the user revokes HealthKit permission in iOS, the endpoint simply stops receiving data.
    Existing stored data is retained (the coach's memory of the past).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import HealthData, UserProfile


def upsert_health_data(
    db: Session,
    user_id: str,
    data_date: str,
    sleep_hours: float | None = None,
    sleep_quality_score: float | None = None,
    hrv_ms: float | None = None,
    resting_hr: float | None = None,
    steps: int | None = None,
    active_calories: int | None = None,
    mindful_minutes: int | None = None,
) -> dict:
    """
    Accept HealthKit data from iOS. Upserts (updates if exists for same date).
    Generates a coaching note based on the data.
    """
    existing = db.query(HealthData).filter_by(user_id=user_id, data_date=data_date).first()

    coaching_note = _generate_health_coaching_note(
        user_id, db, sleep_hours, sleep_quality_score, hrv_ms, resting_hr, steps, active_calories, mindful_minutes
    )

    if existing:
        if sleep_hours is not None:
            existing.sleep_hours = sleep_hours
        if sleep_quality_score is not None:
            existing.sleep_quality_score = sleep_quality_score
        if hrv_ms is not None:
            existing.hrv_ms = hrv_ms
        if resting_hr is not None:
            existing.resting_hr = resting_hr
        if steps is not None:
            existing.steps = steps
        if active_calories is not None:
            existing.active_calories = active_calories
        if mindful_minutes is not None:
            existing.mindful_minutes = mindful_minutes
        existing.coaching_note = coaching_note
        existing.updated_at = datetime.utcnow()
    else:
        existing = HealthData(
            user_id=user_id,
            data_date=data_date,
            sleep_hours=sleep_hours,
            sleep_quality_score=sleep_quality_score,
            hrv_ms=hrv_ms,
            resting_hr=resting_hr,
            steps=steps,
            active_calories=active_calories,
            mindful_minutes=mindful_minutes,
            coaching_note=coaching_note,
        )
        db.add(existing)

    db.commit()

    return {
        "data_date": data_date,
        "coaching_note": coaching_note,
        "stored": True,
    }


def _generate_health_coaching_note(
    user_id: str,
    db: Session,
    sleep_hours: float | None,
    sleep_quality_score: float | None,
    hrv_ms: float | None,
    resting_hr: float | None,
    steps: int | None,
    active_calories: int | None,
    mindful_minutes: int | None,
) -> str:
    """Generate a context-aware coaching note from objective health data."""
    notes = []

    if sleep_hours is not None:
        if sleep_hours < 6:
            notes.append(
                f"Sleep: {sleep_hours:.1f}h — significantly below the 7-9h required for executive cognitive performance. "
                f"Decision quality and emotional regulation are both impaired after less than 6 hours. "
                f"This is not a discipline issue — it is a physiology issue."
            )
        elif sleep_hours < 7:
            notes.append(f"Sleep: {sleep_hours:.1f}h — below optimal. Protect one extra hour tonight.")
        else:
            notes.append(f"Sleep: {sleep_hours:.1f}h — good. Your body got what it needed.")

    if hrv_ms is not None:
        # Get HRV trend (last 7 days)
        cutoff = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent_hrv = db.query(HealthData).filter(
            HealthData.user_id == user_id,
            HealthData.data_date >= cutoff,
            HealthData.hrv_ms.isnot(None),
        ).all()

        if len(recent_hrv) >= 3:
            avg_hrv = sum(h.hrv_ms for h in recent_hrv if h.hrv_ms) / len(recent_hrv)
            if hrv_ms < avg_hrv * 0.75:
                notes.append(
                    f"HRV alert: {hrv_ms:.0f}ms today vs. {avg_hrv:.0f}ms average this week — a {int((1 - hrv_ms/avg_hrv)*100)}% drop. "
                    f"Your autonomic nervous system is under significant load. "
                    f"This is your body's stress signal, often appearing 24-48 hours before you feel it consciously."
                )
            elif hrv_ms > avg_hrv * 1.2:
                notes.append(
                    f"HRV high: {hrv_ms:.0f}ms — above your recent average ({avg_hrv:.0f}ms). "
                    f"Your body is recovered. This is a good day to push."
                )
        else:
            notes.append(f"HRV: {hrv_ms:.0f}ms logged. Building baseline — 7 days needed for trend analysis.")

    if steps is not None:
        if steps < 5000:
            notes.append(
                f"Steps: {steps:,} — sedentary day. Movement is not optional for leaders. "
                f"A 20-minute walk increases creative problem-solving by up to 81% (Stanford, 2014). "
                f"Schedule a walk before your next important call."
            )
        elif steps >= 10000:
            notes.append(f"Steps: {steps:,} — excellent. Movement and leadership are linked. Keep it up.")

    if mindful_minutes is not None:
        if mindful_minutes >= 10:
            notes.append(f"Mindfulness: {mindful_minutes} min today — the most high-leverage 10 minutes a leader can spend.")
        elif mindful_minutes == 0:
            notes.append("Mindfulness: 0 min today. Your coach notices. 5 minutes before bed counts.")

    return " | ".join(notes) if notes else "Health data received."


def get_health_context_for_coaching(db: Session, user_id: str) -> str:
    """
    Returns a 2-3 line health context string for injection into coaching system prompts.
    Only included when recent HealthKit data is available.
    """
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    h = db.query(HealthData).filter_by(user_id=user_id, data_date=yesterday).first()

    if not h:
        return ""

    parts = []
    if h.sleep_hours:
        parts.append(f"sleep last night: {h.sleep_hours:.1f}h")
    if h.hrv_ms:
        parts.append(f"HRV: {h.hrv_ms:.0f}ms")
    if h.resting_hr:
        parts.append(f"resting HR: {h.resting_hr:.0f}bpm")
    if h.steps:
        parts.append(f"steps yesterday: {h.steps:,}")

    if not parts:
        return ""

    return f"\nOBJECTIVE HEALTH DATA (from HealthKit):\n  " + ", ".join(parts) + ".\n"


def get_recent_health_summary(db: Session, user_id: str, days: int = 7) -> dict:
    """7-day health summary for the monthly report and dashboard."""
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    records = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.data_date >= cutoff,
    ).all()

    if not records:
        return {"available": False, "days": days}

    def safe_avg(vals):
        clean = [v for v in vals if v is not None]
        return round(sum(clean) / len(clean), 1) if clean else None

    return {
        "available": True,
        "days_with_data": len(records),
        "avg_sleep_hours": safe_avg([r.sleep_hours for r in records]),
        "avg_hrv_ms": safe_avg([r.hrv_ms for r in records]),
        "avg_resting_hr": safe_avg([r.resting_hr for r in records]),
        "avg_steps": int(safe_avg([r.steps for r in records]) or 0),
        "total_mindful_minutes": sum(r.mindful_minutes or 0 for r in records),
        "low_sleep_days": sum(1 for r in records if r.sleep_hours and r.sleep_hours < 7),
    }
