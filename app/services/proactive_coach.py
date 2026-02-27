"""
Proactive Coach Service
========================
This is the answer to the question: "If I hired Robin Sharma today, what would he ACTUALLY do?"

A real executive coach does not sit and wait for you to call.
He installs systems. He builds rituals. He enforces accountability.
He notices patterns you cannot see about yourself.
He shows up before you ask — with exactly what you need.

This service powers:
  1. Morning Intelligence Brief  — personalised daily brief before the day starts
  2. Evening Power Review        — 3 questions the coach asks you at end of day
  3. Weekly Accountability Call  — structured Friday/Sunday review with commitments
  4. Pattern Recognition Engine  — what the coach notices about you over time
  5. Relationship Repair Prompt  — proactive nudges when a key relationship goes quiet
  6. Decision Journal Trigger    — coach initiates a pre-mortem when a big decision is detected
  7. Reading List + Insight Push — coach sends you one insight from what they've been studying

All outputs are designed to be delivered proactively — not when the user asks,
but on schedule, or triggered by data the coach sees.
"""
from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    DailyCheckIn,
    HabitCompletion,
    HabitRecord,
    KnowledgeItem,
    UserProfile,
    WeeklyReflection,
)
from app.services.knowledge import retrieve_for_context


# ── 1. MORNING INTELLIGENCE BRIEF ────────────────────────────────────────────

def generate_morning_brief(db: Session, user_id: str) -> dict:
    """
    Generates a personalised 5-point morning brief.
    Pulls from: yesterday's check-in, 7-day energy trend, habits,
    pending commitments from last reflection, and recent knowledge items.

    This is the "Robin Sharma calls you at 7am" moment.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"
    today = date.today()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    brief_points = []

    # --- Point 1: Yesterday's energy reading ---
    yesterday_ci = db.query(DailyCheckIn).filter_by(
        user_id=user_id, check_in_date=yesterday
    ).first()

    if yesterday_ci:
        energy = yesterday_ci.energy
        if energy >= 8:
            brief_points.append(
                f"Your energy yesterday was {energy}/10. You're on a strong run. "
                f"Today: use that momentum for your most important deep-work task first."
            )
        elif energy >= 6:
            brief_points.append(
                f"Your energy yesterday was {energy}/10 — solid. "
                f"Today: protect one uninterrupted 90-minute block before 12pm."
            )
        else:
            brief_points.append(
                f"Your energy yesterday was {energy}/10. Your body needs recovery, not more grinding. "
                f"Today's priority: protect one thing that restores you before noon."
            )
    else:
        brief_points.append(
            f"{name}, start today with a 30-second check-in. "
            f"Your coach cannot guide you without knowing where you are."
        )

    # --- Point 2: 7-day burnout signal ---
    cutoff = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    recent_checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= cutoff,
    ).all()

    if recent_checkins and len(recent_checkins) >= 3:
        avg_energy = sum(c.energy for c in recent_checkins) / len(recent_checkins)
        low_count = sum(1 for c in recent_checkins if c.energy <= 5)
        if low_count >= 3:
            brief_points.append(
                f"Pattern flag: {low_count} of your last {len(recent_checkins)} days were low energy. "
                f"This is not a bad day — this is a signal. What is draining you systemically?"
            )

    # --- Point 3: Last commitment check ---
    last_reflection = (
        db.query(WeeklyReflection)
        .filter_by(user_id=user_id)
        .order_by(WeeklyReflection.week_start.desc())
        .first()
    )
    if last_reflection and last_reflection.one_commitment_next_week:
        days_since = (today - date.fromisoformat(last_reflection.week_start)).days
        if days_since <= 7:
            brief_points.append(
                f"Your commitment from Sunday: \"{last_reflection.one_commitment_next_week}\". "
                f"You are on day {days_since} of 7. What specific action are you taking on this TODAY?"
            )

    # --- Point 4: Habit momentum ---
    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()
    if habits:
        cutoff_habit = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        completions = db.query(HabitCompletion).filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.completion_date >= cutoff_habit,
            HabitCompletion.completed == True,
        ).count()
        total_possible = len(habits) * 3
        rate = completions / total_possible if total_possible else 0

        if rate >= 0.8:
            brief_points.append(
                f"Habit momentum: {int(rate*100)}% completion over the last 3 days. "
                f"This is compounding. Don't let a busy morning break the chain."
            )
        elif rate < 0.5:
            brief_points.append(
                f"Habit alert: only {int(rate*100)}% completion over the last 3 days. "
                f"Identify the one habit you will lock in before noon today."
            )

    # --- Point 5: Coach's insight of the day ---
    knowledge_items = retrieve_for_context(db, track=None, user_tags=[], limit=1)
    if knowledge_items:
        item = knowledge_items[0]
        brief_points.append(
            f"Your coach has been studying: \"{item.title}\". "
            f"Key insight: {item.takeaway}"
        )
    else:
        # Fallback wisdom
        WISDOM = [
            "The most important decision you make each day is how you spend the first 60 minutes after waking. Protect them.",
            "Clarity precedes mastery. Before you open your inbox — name the one thing that, if completed today, would make everything else easier.",
            "The quality of your mornings determines the quality of your days. The quality of your days determines the quality of your life.",
            "A great leader manages their energy, not just their time. Protect your best hours for your most important work.",
            "Accountability is not discipline imposed from outside. It is integrity expressed from inside.",
        ]
        brief_points.append(random.choice(WISDOM))

    # Build the full brief
    today_str = today.strftime("%A, %B %d")
    brief_text = f"Good morning, {name}. Here is your brief for {today_str}.\n\n"
    for i, point in enumerate(brief_points, 1):
        brief_text += f"{i}. {point}\n\n"
    brief_text += (
        f"Your coach is watching. Make today count, {name}."
    )

    return {
        "brief_text": brief_text,
        "points": brief_points,
        "generated_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
    }


# ── 2. EVENING POWER REVIEW ───────────────────────────────────────────────────

_EVENING_QUESTIONS = [
    "What is the single most important thing you accomplished today?",
    "What is the one thing you wish you had done differently?",
    "Who did you show up for today — and was it enough?",
]

def generate_evening_review_questions(profile: UserProfile | None) -> dict:
    """
    The 3 questions a great coach asks at end of day.
    Short, targeted, non-negotiable.
    """
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"
    return {
        "intro": (
            f"{name}, the day is nearly done. "
            f"Three questions — honest answers only. This is not a performance review. "
            f"It is the last act of a leader who takes their growth seriously."
        ),
        "questions": _EVENING_QUESTIONS,
        "closing_note": (
            "Write the answers down. Not on your phone. On paper. "
            "The act of writing makes it real. Your coach will read this tomorrow morning."
        ),
    }


def process_evening_review(
    db: Session,
    user_id: str,
    biggest_win: str,
    biggest_regret: str,
    who_showed_up_for: str,
) -> dict:
    """
    Coach responds to the evening review answers with pattern recognition
    and one coaching observation.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # Simple observation engine
    observations = []

    win_lower = biggest_win.lower()
    regret_lower = biggest_regret.lower()
    showed_lower = who_showed_up_for.lower()

    if any(w in win_lower for w in ["meeting", "call", "presentation", "decision"]):
        observations.append(
            "Your biggest win was an external output. "
            "Notice what internal state made that possible — that state is the real asset."
        )
    elif any(w in win_lower for w in ["focus", "deep", "wrote", "built", "created", "finished"]):
        observations.append(
            "You created something today. That is rare. Protect the conditions that made it possible."
        )

    if any(w in regret_lower for w in ["distracted", "phone", "email", "wasted", "meeting"]):
        observations.append(
            "Your regret points to attention theft. Tomorrow: "
            "first 90 minutes, phone on airplane mode, one task only."
        )

    if any(w in showed_lower for w in ["myself", "no one", "nobody"]):
        observations.append(
            "You showed up for yourself today. That is not selfish. "
            "A depleted leader cannot serve anyone. Honour that choice."
        )

    obs_text = " ".join(observations) if observations else (
        "Every day that ends with honest reflection is a day that compounds toward mastery."
    )

    return {
        "coach_observation": obs_text,
        "tomorrow_intention": (
            f"{name}, before you sleep — name one thing you will do differently tomorrow. "
            f"Not a list. One thing. Write it now."
        ),
        "logged_at": datetime.utcnow().isoformat(),
    }


# ── 3. PATTERN RECOGNITION ENGINE ────────────────────────────────────────────

def generate_coach_notebook_entry(db: Session, user_id: str) -> dict:
    """
    The coach's private notebook about the user.
    Run weekly. Synthesises check-ins, habits, reflections, and conversations
    into 3-5 pattern observations.

    This is the feature that makes users say "it knows me."
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"
    today = date.today()

    patterns = []

    # Pattern 1: Energy by day of week
    two_weeks_ago = (today - timedelta(days=14)).strftime("%Y-%m-%d")
    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= two_weeks_ago,
    ).all()

    if len(checkins) >= 7:
        by_day: dict[int, list[float]] = {}
        for ci in checkins:
            d = date.fromisoformat(ci.check_in_date)
            by_day.setdefault(d.weekday(), []).append(ci.energy)

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        low_days = [(day_names[wd], sum(e)/len(e)) for wd, e in by_day.items() if sum(e)/len(e) < 5.5]
        high_days = [(day_names[wd], sum(e)/len(e)) for wd, e in by_day.items() if sum(e)/len(e) >= 7.5]

        if low_days:
            day_str = " and ".join(d[0] for d in low_days[:2])
            patterns.append(
                f"You tend to lose energy on {day_str}. Your average energy on those days "
                f"is below 5.5/10. What is scheduled on those days that is draining you?"
            )
        if high_days:
            day_str = high_days[0][0]
            patterns.append(
                f"Your energy peaks on {day_str}. Protect that day for your most important work."
            )

    # Pattern 2: Dominant stressor keyword frequency
    mood_notes = [ci.mood_note for ci in checkins if ci.mood_note]
    if mood_notes:
        all_text = " ".join(mood_notes).lower()
        stressor_words = {
            "board": "board pressure",
            "meeting": "meeting overload",
            "sleep": "sleep disruption",
            "team": "team friction",
            "decision": "decision fatigue",
            "family": "family stress",
            "wife": "relationship strain at home",
            "partner": "relationship strain at home",
        }
        found = [(label, all_text.count(kw)) for kw, label in stressor_words.items() if all_text.count(kw) >= 2]
        if found:
            found.sort(key=lambda x: -x[1])
            top = found[0]
            patterns.append(
                f"You have mentioned {top[0]} in {top[1]} of your recent check-ins. "
                f"This is the dominant stressor in your life right now. Your coach is watching this closely."
            )

    # Pattern 3: Habit completion patterns
    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()
    if habits:
        habit_completions: dict[str, int] = {}
        cutoff = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        for h in habits:
            count = db.query(HabitCompletion).filter(
                HabitCompletion.habit_id == h.id,
                HabitCompletion.completion_date >= cutoff,
                HabitCompletion.completed == True,
            ).count()
            habit_completions[h.name] = count

        perfect = [name_h for name_h, cnt in habit_completions.items() if cnt >= 12]
        struggling = [name_h for name_h, cnt in habit_completions.items() if cnt <= 4]

        if perfect:
            patterns.append(
                f"Your {perfect[0]} habit has near-perfect completion over 14 days. "
                f"This is identity-level consistency. It is becoming who you are."
            )
        if struggling:
            patterns.append(
                f"Your {struggling[0]} habit is completing at under 30% over 14 days. "
                f"This is not a motivation problem — it is a design problem. "
                f"When and where is this supposed to happen? Let's make it easier."
            )

    # Pattern 4: Reflection commitment follow-through
    reflections = (
        db.query(WeeklyReflection)
        .filter_by(user_id=user_id)
        .order_by(WeeklyReflection.week_start.desc())
        .limit(4)
        .all()
    )
    if len(reflections) >= 2:
        commitments = [r.one_commitment_next_week for r in reflections if r.one_commitment_next_week]
        if commitments:
            patterns.append(
                f"Over the last {len(commitments)} weeks, your commitments have been: "
                f"\"{commitments[0]}\". Your coach will ask you about this directly. "
                f"Are you following through, or is this becoming a ritual without substance?"
            )

    if not patterns:
        patterns.append(
            f"{name}, you have not yet given your coach enough data to see patterns. "
            f"Daily check-ins for 10 consecutive days will unlock this feature fully."
        )

    entry_text = f"Coach's Notebook — {today.strftime('%B %d, %Y')}\n\n"
    entry_text += "\n\n".join(f"• {p}" for p in patterns)

    return {
        "entry_text": entry_text,
        "patterns": patterns,
        "generated_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
    }


# ── 4. RELATIONSHIP REPAIR PROMPT ────────────────────────────────────────────

def check_relationship_nudges(db: Session, user_id: str) -> list[dict]:
    """
    Checks how long ago key relationships were mentioned in coaching conversations.
    If a relationship named in onboarding hasn't appeared in 10+ days, the coach nudges.

    This is the feature that makes users emotional: "It remembered to ask about my wife."
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile or not profile.key_relationships:
        return []

    nudges = []
    today = date.today()
    cutoff = (today - timedelta(days=10)).strftime("%Y-%m-%d")

    # Check check-in mood notes for relationship mentions
    recent_checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= cutoff,
    ).all()

    mentioned_this_week: set[str] = set()
    for ci in recent_checkins:
        if ci.mood_note:
            lower = ci.mood_note.lower()
            for rel in (profile.key_relationships or []):
                rel_lower = rel.lower()
                if rel_lower in lower or rel_lower.split()[0].lower() in lower:
                    mentioned_this_week.add(rel)

    name = profile.full_name.split()[0] if profile.full_name else "friend"
    for rel in (profile.key_relationships or []):
        if rel not in mentioned_this_week:
            nudges.append({
                "relationship": rel,
                "nudge": (
                    f"{name}, you haven't mentioned {rel} in the last 10 days. "
                    f"How are things with them? Sometimes the most important relationship "
                    f"gets the least intentional attention. Is that true here?"
                ),
                "priority": "high" if any(w in rel.lower() for w in ["wife", "husband", "partner", "spouse"]) else "medium",
            })

    return nudges


# ── 5. PROACTIVE READING ASSIGNMENT ──────────────────────────────────────────

def get_weekly_reading_assignment(db: Session, user_id: str) -> dict:
    """
    Every week, the coach assigns one thing to read, watch, or reflect on.
    Pulled from the knowledge base, matched to the user's dominant track.

    Robin Sharma always assigned reading. Always.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # Determine dominant track from profile goals or recent stressors
    track = "leadership"
    if profile and profile.goals_90_days:
        goals_text = " ".join(profile.goals_90_days).lower()
        if any(w in goals_text for w in ["relationship", "family", "team", "people"]):
            track = "relationships"
        elif any(w in goals_text for w in ["focus", "energy", "health", "recovery"]):
            track = "energy"

    items = retrieve_for_context(db, track=track, user_tags=[], limit=3)
    if not items:
        return {
            "assignment": (
                f"{name}, this week your reading assignment from your coach: "
                f"\"The 5AM Club\" by Robin Sharma. Focus only on the chapter on the Victory Hour. "
                f"Implement one element. Report back on Sunday."
            ),
            "track": track,
        }

    item = items[0]
    return {
        "assignment": (
            f"{name}, this week your coach is assigning: \"{item.title}\".\n\n"
            f"Key insight: {item.takeaway}\n\n"
            f"Your application: {item.application}\n\n"
            f"Assignment: By Sunday, identify one way this changes how you approach "
            f"your biggest challenge this week. Then tell your coach what you discovered."
        ),
        "source_url": item.source_url,
        "track": track,
        "knowledge_item_id": item.id,
    }
