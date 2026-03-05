"""
Daily Check-In Service — powers the Burnout Sentinel.
A 30-second check-in (energy, stress, sleep) that:
  - tracks trends over time
  - updates the user's rolling energy baseline
  - fires an alert + coaching response when risk is high
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import DailyCheckIn, UserProfile
from app.schemas import DailyCheckInRequest, DailyCheckInResponse
from app.services.achievements import (
    check_consistency_achievements,
    check_recovery_achievement,
)


_LOW_ENERGY_THRESHOLD = 5.0
_HIGH_STRESS_THRESHOLD = 7.5
_ALERT_CONSECUTIVE_DAYS = 3


def _assess_burnout_risk(energy: float, stress: float, consecutive_low: int) -> str:
    if consecutive_low >= _ALERT_CONSECUTIVE_DAYS or (energy <= 3 and stress >= 8):
        return "high"
    if consecutive_low >= 2 or (energy <= _LOW_ENERGY_THRESHOLD and stress >= _HIGH_STRESS_THRESHOLD):
        return "moderate"
    return "low"


def _coach_response_for_checkin(
    energy: float, stress: float, risk: str, consecutive_low: int, name: str
) -> tuple[str, str | None]:
    """Returns (coach_message, alert_or_None)."""
    first = name.split()[0] if name else "friend"

    if risk == "high":
        msg = (
            f"Center: {first}, your body is sending a clear signal — this is not sustainable.\n"
            f"Reframe: Recovery is not laziness. It is the fuel for everything you care about.\n"
            "Actions:\n"
            "  1. Cancel or defer one commitment today that isn't mission-critical.\n"
            "  2. Take a 20-minute walk outside — no phone.\n"
            "  3. Sleep before 10pm tonight. Non-negotiable.\n"
            f"Accountability question: What is the one thing you will protect today to begin recovering?\n"
            "Evidence spotlight: WHO ICD-11 classifies burnout as a syndrome of unmanaged chronic stress — early intervention changes the trajectory."
        )
        alert = (
            f"Your energy has been low for {consecutive_low} consecutive days. "
            "Your coach has flagged this as a high burnout risk. Please prioritise recovery today."
        )
        return msg, alert

    if risk == "moderate":
        msg = (
            f"Center: {first}, you're running below your best — and you know it.\n"
            "Reframe: One day of intentional recovery returns more than three days of grinding through it.\n"
            "Actions:\n"
            "  1. Identify your highest-leverage task and protect 45 uninterrupted minutes for it.\n"
            "  2. Decline one low-priority request today.\n"
            "  3. End your work by 7pm and do something restorative tonight.\n"
            "Accountability question: What will you say no to today?\n"
            "Evidence spotlight: Peer coaching research shows that small recovery interventions prevent full burnout episodes."
        )
        return msg, None

    # Low risk — positive reinforcement
    msg = (
        f"Center: {first}, you're in a strong place today.\n"
        "Reframe: High energy days are when the most important work gets done — use it wisely.\n"
        "Actions:\n"
        "  1. Tackle your most important goal first — before meetings start.\n"
        "  2. Check in with one key relationship with a specific appreciation.\n"
        "  3. Plan one thing tonight that will keep tomorrow's energy equally high.\n"
        "Accountability question: What is the single highest-value action you will complete before noon?\n"
        "Evidence spotlight: Stable context and good energy are the two strongest predictors of habit completion."
    )
    return msg, None


def process_checkin(db: Session, payload: DailyCheckInRequest) -> DailyCheckInResponse:
    today = date.today().strftime("%Y-%m-%d")

    # Upsert today's check-in
    existing = (
        db.query(DailyCheckIn)
        .filter_by(user_id=payload.user_id, check_in_date=today)
        .first()
    )

    # Count consecutive low-energy days (looking back 7 days)
    cutoff = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == payload.user_id,
            DailyCheckIn.check_in_date >= cutoff,
            DailyCheckIn.check_in_date < today,
        )
        .order_by(DailyCheckIn.check_in_date.desc())
        .all()
    )
    consecutive_low = 0
    for r in recent:
        if r.energy <= _LOW_ENERGY_THRESHOLD:
            consecutive_low += 1
        else:
            break
    if payload.energy <= _LOW_ENERGY_THRESHOLD:
        consecutive_low += 1

    risk = _assess_burnout_risk(payload.energy, payload.stress, consecutive_low)

    # Get user name
    profile = db.query(UserProfile).filter_by(user_id=payload.user_id).first()
    name = profile.full_name if profile else ""
    coach_msg, alert = _coach_response_for_checkin(
        payload.energy, payload.stress, risk, consecutive_low, name
    )

    if existing:
        existing.energy = payload.energy
        existing.stress = payload.stress
        existing.sleep_quality = payload.sleep_quality
        existing.mood_note = payload.mood_note
        existing.coach_response = coach_msg
        existing.updated_at = datetime.utcnow()
    else:
        ci = DailyCheckIn(
            user_id=payload.user_id,
            check_in_date=today,
            energy=payload.energy,
            stress=payload.stress,
            sleep_quality=payload.sleep_quality,
            mood_note=payload.mood_note,
            coach_response=coach_msg,
        )
        db.add(ci)

    # Update rolling baseline on user profile
    if profile:
        # Weighted average: 80% old baseline, 20% today
        profile.energy_baseline = round(profile.energy_baseline * 0.8 + payload.energy * 0.2, 2)
        profile.burnout_risk = risk
        if payload.energy <= _LOW_ENERGY_THRESHOLD:
            profile.consecutive_low_energy_days = consecutive_low
        else:
            profile.consecutive_low_energy_days = 0

    db.commit()

    # Gamification hooks
    check_consistency_achievements(db, payload.user_id)
    check_recovery_achievement(db, payload.user_id)

    return DailyCheckInResponse(
        check_in_date=today,
        burnout_risk=risk,
        consecutive_low_energy_days=consecutive_low,
        coach_response=coach_msg,
        alert=alert,
    )
