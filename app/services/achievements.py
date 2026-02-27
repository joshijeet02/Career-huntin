"""
Achievement & Milestone Celebration Engine
===========================================
Real coaches celebrate. Most apps don't.

When a client hits a meaningful milestone — a 7-day habit streak, 30 days of consistent
check-ins, recovery from a burnout week, completing a 90-day goal — a great coach notices.
Not with a badge or a notification. With a real message. Words that land.

This engine runs as a background check on every significant action:
  - After a habit is marked complete → check for streak milestones
  - After a check-in → check for consistency milestones or recovery milestones
  - After a goal milestone is updated → check for sprint completion milestones
  - Weekly → check for pattern milestones (7 reflections completed, etc.)

The celebration itself is written as the coach would write it:
  Not "You earned a badge!" but "You have done something most people never do.
  You showed up. Again. That is who you are now."

Celebrated achievements are flagged and returned in the next morning brief.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Achievement,
    DailyCheckIn,
    GoalMilestone,
    HabitCompletion,
    HabitRecord,
    UserProfile,
    WeeklyReflection,
)


# ── Achievement definitions ───────────────────────────────────────────────────

def check_habit_achievements(db: Session, user_id: str, habit_id: int) -> list[Achievement]:
    """
    Run after every habit completion. Checks for streak milestones.
    """
    habit = db.query(HabitRecord).filter_by(id=habit_id).first()
    if not habit:
        return []

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # Calculate current streak
    today = date.today()
    streak = 0
    for i in range(365):
        check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        comp = db.query(HabitCompletion).filter_by(
            habit_id=habit_id, completion_date=check_date, completed=True
        ).first()
        if comp:
            streak += 1
        else:
            break

    # Milestone thresholds
    milestones = {
        7: (
            f"7-day streak on {habit.name}",
            "7 consecutive days",
            f"{name}, 7 days in a row on {habit.name}.\n\n"
            f"This is where most people stop. Not you. "
            f"Your coach wants you to notice that you didn't break the chain — "
            f"not because it was easy, but because you decided not to. "
            f"That decision is the foundation of everything that follows."
        ),
        14: (
            f"14-day streak on {habit.name}",
            "14 consecutive days",
            f"Two weeks. {habit.name} is starting to become automatic, {name}. "
            f"Research on habit formation shows that the neural pathway is now grooved. "
            f"You are not building a habit anymore. You are building an identity."
        ),
        30: (
            f"30-day streak on {habit.name}",
            "30 consecutive days",
            f"{name}. 30 days. This is not a streak anymore. This is who you are.\n\n"
            f"The version of you that started this 30 days ago was hoping to build a habit. "
            f"The version of you today does not have to hope. You simply do it. "
            f"Your coach is proud of you. That is not something it says often."
        ),
        66: (
            f"66-day streak on {habit.name}",
            "66 consecutive days",
            f"{name}, science says habit formation takes approximately 66 days. You are here. "
            f"This is no longer effort. This is character. "
            f"Protect this habit the way you protect your most important relationship — "
            f"because it has become one."
        ),
        100: (
            f"100-day streak on {habit.name}",
            "100 consecutive days",
            f"100 days. {name}, there are not many people on this planet who have ever done "
            f"what you just did — sustained one keystone habit for 100 consecutive days. "
            f"This is mastery. Your coach sees it. Now you must see it too."
        ),
    }

    new_achievements = []
    for threshold, (title, subtitle, message) in milestones.items():
        if streak == threshold:
            # Check we haven't already celebrated this
            existing = db.query(Achievement).filter_by(
                user_id=user_id,
                achievement_type=f"habit_streak_{threshold}",
                title=title,
            ).first()
            if not existing:
                ach = Achievement(
                    user_id=user_id,
                    achievement_date=date.today().strftime("%Y-%m-%d"),
                    achievement_type=f"habit_streak_{threshold}",
                    title=title,
                    coach_message=message,
                    data_snapshot={"habit_id": habit_id, "habit_name": habit.name, "streak": streak},
                    celebrated=False,
                )
                db.add(ach)
                new_achievements.append(ach)

    if new_achievements:
        db.commit()
    return new_achievements


def check_consistency_achievements(db: Session, user_id: str) -> list[Achievement]:
    """
    Run weekly. Checks for check-in consistency milestones.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # Count total check-ins
    total_checkins = db.query(DailyCheckIn).filter_by(user_id=user_id).count()
    total_reflections = db.query(WeeklyReflection).filter_by(user_id=user_id).count()

    new_achievements = []
    today = date.today().strftime("%Y-%m-%d")

    checkin_milestones = {
        10: (
            "10 Days of Showing Up",
            f"{name}, 10 check-ins. You are one of the rare ones who actually shows up to their own growth. "
            f"Most people intend to. You do."
        ),
        30: (
            "30 Days of Self-Awareness",
            f"30 daily check-ins. {name}, you now have a month of data that most executives never bother to collect — "
            f"about themselves. Your coach can now see patterns that will change the way you operate."
        ),
        100: (
            "100 Days of Commitment",
            f"100 check-ins. {name}, this is rare. Genuinely rare. "
            f"A leader who shows up to their own development every day for 100 days "
            f"does not accidentally do that. This is a chosen identity. Honour it."
        ),
    }

    for threshold, (title, message) in checkin_milestones.items():
        if total_checkins == threshold:
            existing = db.query(Achievement).filter_by(
                user_id=user_id, achievement_type=f"checkin_{threshold}"
            ).first()
            if not existing:
                ach = Achievement(
                    user_id=user_id,
                    achievement_date=today,
                    achievement_type=f"checkin_{threshold}",
                    title=title,
                    coach_message=message,
                    data_snapshot={"total_checkins": total_checkins},
                    celebrated=False,
                )
                db.add(ach)
                new_achievements.append(ach)

    reflection_milestones = {
        4: (
            "One Month of Sunday Reflections",
            f"Four consecutive Sunday reflections, {name}. "
            f"Most leaders live their weeks. You are also examining them. "
            f"That is the difference between experience and wisdom."
        ),
        12: (
            "12 Weeks of Growth",
            f"A full 90-day sprint of Sunday reflections. {name}, you have been doing "
            f"what the world's greatest leaders do — reviewing, learning, adjusting. "
            f"This is not a habit. This is a practice. And you have built it."
        ),
    }

    for threshold, (title, message) in reflection_milestones.items():
        if total_reflections == threshold:
            existing = db.query(Achievement).filter_by(
                user_id=user_id, achievement_type=f"reflection_{threshold}"
            ).first()
            if not existing:
                ach = Achievement(
                    user_id=user_id,
                    achievement_date=today,
                    achievement_type=f"reflection_{threshold}",
                    title=title,
                    coach_message=message,
                    data_snapshot={"total_reflections": total_reflections},
                    celebrated=False,
                )
                db.add(ach)
                new_achievements.append(ach)

    if new_achievements:
        db.commit()
    return new_achievements


def check_recovery_achievement(db: Session, user_id: str) -> Achievement | None:
    """
    Special achievement: recovering from 3+ consecutive low-energy days.
    The coach celebrates recovery as much as peak performance.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    today = date.today()
    # Get last 7 days
    cutoff = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= cutoff,
    ).order_by(DailyCheckIn.check_in_date).all()

    if len(recent) < 4:
        return None

    # Look for pattern: 3+ low energy days followed by 2+ above 6
    lows = [r for r in recent[:-2] if r.energy <= 4]
    if len(lows) >= 3:
        highs_after = [r for r in recent if r.energy >= 6.5 and r.check_in_date > lows[-1].check_in_date]
        if len(highs_after) >= 2:
            existing = db.query(Achievement).filter_by(
                user_id=user_id, achievement_type="recovery"
            ).filter(Achievement.achievement_date >= cutoff).first()
            if not existing:
                message = (
                    f"{name}, your coach has been watching.\n\n"
                    f"You went through a genuinely hard stretch — {len(lows)} consecutive days of low energy. "
                    f"And then you came back.\n\n"
                    f"Not because it was easy. Not because conditions were perfect. "
                    f"Because that is what strong leaders do — they weather the storm without losing who they are.\n\n"
                    f"Your coach is not celebrating that you suffered. "
                    f"It is celebrating that you did not let the suffering define you. "
                    f"Recovery is a skill. You have it."
                )
                ach = Achievement(
                    user_id=user_id,
                    achievement_date=today.strftime("%Y-%m-%d"),
                    achievement_type="recovery",
                    title="Recovery — Back Stronger",
                    coach_message=message,
                    data_snapshot={"low_days": len(lows), "recovery_days": len(highs_after)},
                    celebrated=False,
                )
                db.add(ach)
                db.commit()
                return ach
    return None


def get_uncelebrated_achievements(db: Session, user_id: str) -> list[dict]:
    """
    Fetch all uncelebrated achievements for morning brief inclusion.
    Marks them as celebrated.
    """
    uncelebrated = db.query(Achievement).filter_by(
        user_id=user_id, celebrated=False
    ).order_by(Achievement.achievement_date.desc()).all()

    result = []
    for a in uncelebrated:
        result.append({
            "achievement_id": a.id,
            "title": a.title,
            "achievement_type": a.achievement_type,
            "achievement_date": a.achievement_date,
            "coach_message": a.coach_message,
        })
        a.celebrated = True

    if uncelebrated:
        db.commit()

    return result


def get_all_achievements(db: Session, user_id: str) -> list[dict]:
    """Full achievement history for the profile screen."""
    achievements = db.query(Achievement).filter_by(user_id=user_id).order_by(
        Achievement.achievement_date.desc()
    ).all()
    return [
        {
            "achievement_id": a.id,
            "title": a.title,
            "achievement_type": a.achievement_type,
            "achievement_date": a.achievement_date,
            "coach_message": a.coach_message,
        }
        for a in achievements
    ]
