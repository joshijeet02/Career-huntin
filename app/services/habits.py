"""
Habit Compounding Service
Tracks keystone habits, streaks, and completion rates.
The coach uses this data to personalise coaching responses over time.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import HabitCompletion, HabitRecord
from app.schemas import HabitCompleteRequest, HabitCreateRequest, HabitOut, HabitsResponse


def create_habit(db: Session, payload: HabitCreateRequest) -> HabitOut:
    habit = HabitRecord(
        user_id=payload.user_id,
        name=payload.name,
        track=payload.track,
        target_frequency=payload.target_frequency,
        active=True,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return HabitOut(id=habit.id, name=habit.name, track=habit.track,
                    target_frequency=habit.target_frequency,
                    current_streak=0, total_completions=0)


def complete_habit(db: Session, payload: HabitCompleteRequest) -> HabitOut:
    habit = db.query(HabitRecord).filter_by(id=payload.habit_id, user_id=payload.user_id).first()
    if not habit:
        raise ValueError(f"Habit {payload.habit_id} not found for user {payload.user_id}")

    today = date.today().strftime("%Y-%m-%d")
    existing = db.query(HabitCompletion).filter_by(
        habit_id=habit.id, user_id=payload.user_id, completion_date=today
    ).first()
    if not existing:
        db.add(HabitCompletion(
            habit_id=habit.id,
            user_id=payload.user_id,
            completion_date=today,
            completed=True,
            note=payload.note,
        ))
        db.commit()

    return _habit_out(db, habit)


def get_habits(db: Session, user_id: str) -> HabitsResponse:
    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()
    habit_outs = [_habit_out(db, h) for h in habits]

    # 7-day completion rate across all habits
    if not habits:
        return HabitsResponse(habits=[], completion_rate_7d=0.0)

    cutoff = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    total_possible = len(habits) * 7
    completed_count = (
        db.query(HabitCompletion)
        .filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.completion_date >= cutoff,
            HabitCompletion.completed == True,
        )
        .count()
    )
    rate = round(completed_count / total_possible, 2) if total_possible > 0 else 0.0
    return HabitsResponse(habits=habit_outs, completion_rate_7d=rate)


def _habit_out(db: Session, habit: HabitRecord) -> HabitOut:
    # Current streak — consecutive days ending today
    today = date.today()
    streak = 0
    for i in range(60):
        check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        done = db.query(HabitCompletion).filter_by(
            habit_id=habit.id, completion_date=check_date, completed=True
        ).first()
        if done:
            streak += 1
        elif i > 0:
            break  # allow today to be incomplete without breaking streak

    total = db.query(HabitCompletion).filter_by(
        habit_id=habit.id, completed=True
    ).count()

    return HabitOut(
        id=habit.id,
        name=habit.name,
        track=habit.track,
        target_frequency=habit.target_frequency,
        current_streak=streak,
        total_completions=total,
    )
