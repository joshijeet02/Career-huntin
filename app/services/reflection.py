"""
Weekly Reflection Ritual Service
Every Sunday (or on demand), the user answers 3 questions.
The coach synthesises the week and extracts one binding commitment for next week.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import DailyCheckIn, HabitCompletion, HabitRecord, UserProfile, WeeklyReflection
from app.schemas import WeeklyReflectionRequest, WeeklyReflectionResponse
from app.services.achievements import check_consistency_achievements


def _monday_of_week(d: date) -> str:
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def _synthesise(
    payload: WeeklyReflectionRequest,
    profile: UserProfile | None,
    avg_energy: float | None,
    habit_rate: float | None,
) -> str:
    name = profile.full_name.split()[0] if profile and profile.full_name else "You"
    energy_line = (
        f"Your average energy this week was {avg_energy:.1f}/10. "
        + ("That's strong — build on it." if avg_energy and avg_energy >= 7 else
           "That's below your best — next week, prioritise recovery.")
    ) if avg_energy else ""
    habit_line = (
        f"Habit completion rate: {int((habit_rate or 0) * 100)}% — "
        + ("excellent consistency." if habit_rate and habit_rate >= 0.75 else
           "room to tighten your daily rituals.")
    ) if habit_rate is not None else ""

    synthesis = (
        f"{name}, here is your week in full:\n\n"
        f"BIGGEST WIN: {payload.biggest_win}\n"
        f"BIGGEST LESSON: {payload.biggest_lesson}\n"
        f"ONE COMMITMENT FOR NEXT WEEK: {payload.one_commitment_next_week}\n\n"
    )
    if energy_line:
        synthesis += f"ENERGY: {energy_line}\n"
    if habit_line:
        synthesis += f"HABITS: {habit_line}\n"
    synthesis += (
        "\nYour coach's challenge: Write your commitment on paper and place it somewhere you will see it tomorrow morning. "
        "Accountability is the bridge between intention and result."
    )
    return synthesis


def save_weekly_reflection(db: Session, payload: WeeklyReflectionRequest) -> WeeklyReflectionResponse:
    week_start = _monday_of_week(date.today())

    # Gather supporting data
    cutoff = week_start
    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == payload.user_id,
        DailyCheckIn.check_in_date >= cutoff,
    ).all()
    avg_energy = (sum(c.energy for c in checkins) / len(checkins)) if checkins else None

    habits = db.query(HabitRecord).filter_by(user_id=payload.user_id, active=True).all()
    if habits:
        total_possible = len(habits) * 7
        completed = db.query(HabitCompletion).filter(
            HabitCompletion.user_id == payload.user_id,
            HabitCompletion.completion_date >= cutoff,
            HabitCompletion.completed == True,
        ).count()
        habit_rate = completed / total_possible if total_possible > 0 else 0.0
    else:
        habit_rate = None

    profile = db.query(UserProfile).filter_by(user_id=payload.user_id).first()
    synthesis = _synthesise(payload, profile, avg_energy, habit_rate)

    existing = db.query(WeeklyReflection).filter_by(
        user_id=payload.user_id, week_start=week_start
    ).first()
    if existing:
        existing.biggest_win = payload.biggest_win
        existing.biggest_lesson = payload.biggest_lesson
        existing.one_commitment_next_week = payload.one_commitment_next_week
        existing.coach_synthesis = synthesis
    else:
        db.add(WeeklyReflection(
            user_id=payload.user_id,
            week_start=week_start,
            biggest_win=payload.biggest_win,
            biggest_lesson=payload.biggest_lesson,
            one_commitment_next_week=payload.one_commitment_next_week,
            coach_synthesis=synthesis,
        ))
    db.commit()

    # Gamification hook
    check_consistency_achievements(db, payload.user_id)

    return WeeklyReflectionResponse(week_start=week_start, coach_synthesis=synthesis)
