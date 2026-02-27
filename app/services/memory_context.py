"""
Memory-Aware Coach Context
===========================
"A coach who forgets between sessions is not a coach. They are a form."

The core problem with AI coaching: every conversation starts blank.
The user tells the coach their name. Their challenge. Their goals.
Every time.

This module solves that. It assembles a rich context string — drawn from
the database — that is injected into every coaching conversation. The model
receives this context as a system-level briefing before the user speaks.

What the context carries:
  - Who they are (profile, role, org, current challenge, goals, values)
  - Where they are (days since onboarding, milestone progress)
  - How they have been (recent energy, recent check-ins, any notable pattern)
  - What they have committed to (open commitments, any overdue)
  - What the coach knows about them (First Read synthesis)
  - What the coach should avoid (things explicitly named as friction)

The result: the coach opens every conversation knowing the person.
Not generically. Specifically.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Commitment,
    DailyCheckIn,
    FirstRead,
    HabitCompletion,
    HabitRecord,
    RecalibrationSession,
    UserProfile,
)


# ── Sub-assemblers ────────────────────────────────────────────────────────────

def _profile_block(profile: UserProfile, days_since_onboarding: int) -> str:
    name = profile.full_name or "the user"
    lines = [f"WHO: {name}"]

    if profile.role:
        lines.append(f"Role: {profile.role}")
    if profile.organisation:
        lines.append(f"Organisation: {profile.organisation}")
    if profile.industry:
        lines.append(f"Industry: {profile.industry}")
    if profile.biggest_challenge:
        lines.append(f"Current challenge: {profile.biggest_challenge}")

    if profile.goals_90_days:
        goals_str = "; ".join(profile.goals_90_days[:3])
        lines.append(f"90-day goals: {goals_str}")

    if profile.core_values:
        vals_str = ", ".join(profile.core_values[:4])
        lines.append(f"Core values: {vals_str}")

    if profile.coaching_style_preference:
        style_map = {
            "direct": "direct and challenging",
            "supportive": "warm and supportive",
            "structured": "structured and methodical",
        }
        style = style_map.get(profile.coaching_style_preference, profile.coaching_style_preference)
        lines.append(f"Coaching style preference: {style}")

    lines.append(f"Days since onboarding: {days_since_onboarding}")
    lines.append(f"Profile version: {profile.profile_version}")

    return "\n".join(lines)


def _energy_block(db: Session, user_id: str, days: int = 14) -> str:
    """Recent energy trend — last N days of check-ins."""
    cutoff = date.today() - timedelta(days=days)
    checkins = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date >= cutoff,
        )
        .order_by(DailyCheckIn.checkin_date.desc())
        .limit(14)
        .all()
    )

    if not checkins:
        return "RECENT ENERGY: No check-ins in the last 14 days."

    energies = [c.energy_level for c in checkins if c.energy_level is not None]
    if not energies:
        return "RECENT ENERGY: Check-ins recorded, no energy data."

    avg = round(sum(energies) / len(energies), 1)
    recent_3 = energies[:3]
    recent_avg = round(sum(recent_3) / len(recent_3), 1)

    lines = [f"RECENT ENERGY (last {len(checkins)} check-ins):"]
    lines.append(f"  14-day average: {avg}/10")
    lines.append(f"  Last 3 days average: {recent_avg}/10")

    # Trend direction
    if len(energies) >= 6:
        first_half = energies[len(energies)//2:]
        second_half = energies[:len(energies)//2]
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        delta = second_avg - first_avg

        if delta > 0.5:
            trend = "trending upward"
        elif delta < -0.5:
            trend = "trending downward — worth noting"
        else:
            trend = "holding steady"
        lines.append(f"  Trend: {trend}")

    # Last check-in mood/note
    latest = checkins[0]
    if latest.mood_note:
        note_preview = latest.mood_note[:120].rstrip()
        lines.append(f"  Last note: \"{note_preview}\"")

    return "\n".join(lines)


def _habits_block(db: Session, user_id: str) -> str:
    """Active habits and recent 7-day completion rate."""
    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()
    if not habits:
        return "HABITS: No active habits tracked."

    cutoff = date.today() - timedelta(days=7)
    completions = (
        db.query(HabitCompletion)
        .filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.completion_date >= cutoff,
        )
        .all()
    )

    habit_counts: dict[int, int] = {}
    for c in completions:
        habit_counts[c.habit_id] = habit_counts.get(c.habit_id, 0) + 1

    lines = [f"HABITS (last 7 days):"]
    for h in habits:
        count = habit_counts.get(h.id, 0)
        bar = "█" * count + "░" * (7 - count)
        pct = round((count / 7) * 100)
        lines.append(f"  {h.name}: {bar} {count}/7 ({pct}%)")

    return "\n".join(lines)


def _commitments_block(db: Session, user_id: str) -> str:
    """Open and recently missed commitments."""
    open_commitments = (
        db.query(Commitment)
        .filter_by(user_id=user_id, status="open")
        .order_by(Commitment.due_date)
        .all()
    )

    recently_missed = (
        db.query(Commitment)
        .filter(
            Commitment.user_id == user_id,
            Commitment.status == "missed",
            Commitment.checked_at >= datetime.utcnow() - timedelta(days=7),
        )
        .all()
    )

    if not open_commitments and not recently_missed:
        return "COMMITMENTS: None open or recently missed."

    lines = ["COMMITMENTS:"]

    today = date.today()
    overdue = [c for c in open_commitments if c.due_date and c.due_date < today]
    due_today = [c for c in open_commitments if c.due_date == today]
    upcoming = [c for c in open_commitments if c.due_date and c.due_date > today]

    if overdue:
        lines.append(f"  OVERDUE ({len(overdue)}):")
        for c in overdue[:3]:
            days_late = (today - c.due_date).days
            lines.append(f"    — \"{c.commitment_text[:80]}\" ({days_late}d overdue)")

    if due_today:
        lines.append(f"  Due today ({len(due_today)}):")
        for c in due_today[:2]:
            lines.append(f"    — \"{c.commitment_text[:80]}\"")

    if upcoming:
        lines.append(f"  Upcoming ({len(upcoming)} total)")

    if recently_missed:
        lines.append(f"  Recently missed ({len(recently_missed)}):")
        for c in recently_missed[:2]:
            lines.append(f"    — \"{c.commitment_text[:80]}\"")

    return "\n".join(lines)


def _first_read_block(db: Session, user_id: str) -> str:
    """Key findings from the First Read synthesis."""
    fr = db.query(FirstRead).filter_by(user_id=user_id).first()
    if not fr:
        return ""

    lines = ["COACH'S FIRST READ (personality synthesis):"]

    if fr.undervalued_strength:
        lines.append(f"  Undervalued strength: {fr.undervalued_strength[:200].rstrip()}")

    if fr.blind_spot:
        lines.append(f"  Blind spot to watch: {fr.blind_spot[:200].rstrip()}")

    if fr.relationship_pattern:
        lines.append(f"  Relationship pattern: {fr.relationship_pattern[:200].rstrip()}")

    if fr.one_sentence:
        lines.append(f"  One-sentence portrait: {fr.one_sentence}")

    return "\n".join(lines)


def _milestone_block(db: Session, user_id: str, days_since_onboarding: int) -> str:
    """Recalibration milestone status."""
    done_milestones = {
        r.milestone_days
        for r in db.query(RecalibrationSession).filter_by(user_id=user_id).all()
    }

    lines = []
    next_milestone = None
    for m in [30, 60, 90]:
        if m not in done_milestones and days_since_onboarding < m:
            next_milestone = m
            break

    completed_str = (
        ", ".join(f"{m}-day" for m in sorted(done_milestones)) if done_milestones else "none yet"
    )

    lines.append(f"MILESTONE PROGRESS:")
    lines.append(f"  Recalibrations completed: {completed_str}")
    if next_milestone:
        days_to_next = next_milestone - days_since_onboarding
        lines.append(f"  Next milestone: {next_milestone}-day (in {days_to_next} days)")

    return "\n".join(lines)


def _stressors_and_context_block(profile: UserProfile) -> str:
    """Current known stressors and life context."""
    lines = []

    if profile.current_stressors:
        stressors = profile.current_stressors[:3]
        lines.append(f"CURRENT STRESSORS: {'; '.join(stressors)}")

    if profile.key_relationships:
        rels = []
        for name, rel_type in list(profile.key_relationships.items())[:3]:
            rels.append(f"{name} ({rel_type})")
        lines.append(f"KEY RELATIONSHIPS: {', '.join(rels)}")

    if profile.work_environment:
        lines.append(f"Work environment: {profile.work_environment}")

    return "\n".join(lines) if lines else ""


# ── Main assembler ────────────────────────────────────────────────────────────

def build_coach_memory_context(
    db: Session,
    user_id: str,
    include_first_read: bool = True,
    include_habits: bool = True,
    include_commitments: bool = True,
    include_milestones: bool = True,
) -> str:
    """
    Build the full memory context string for injection into the coaching system prompt.

    This is called before every coaching conversation.
    It is designed to be injected as the system prompt prefix.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return ""

    days_since = (date.today() - profile.created_at.date()).days

    blocks = []

    # Preamble
    blocks.append(
        "═" * 50 + "\n"
        "COACH MEMORY BRIEFING — READ BEFORE RESPONDING\n"
        "═" * 50
    )

    # Core profile
    blocks.append(_profile_block(profile, days_since))

    # Energy and mood
    blocks.append(_energy_block(db, user_id))

    # Habits
    if include_habits:
        blocks.append(_habits_block(db, user_id))

    # Commitments
    if include_commitments:
        blocks.append(_commitments_block(db, user_id))

    # First Read synthesis
    if include_first_read:
        fr_block = _first_read_block(db, user_id)
        if fr_block:
            blocks.append(fr_block)

    # Stressors and relationships
    context_block = _stressors_and_context_block(profile)
    if context_block:
        blocks.append(context_block)

    # Milestone progress
    if include_milestones:
        blocks.append(_milestone_block(db, user_id, days_since))

    # Coaching directive
    blocks.append(
        "─" * 50 + "\n"
        "COACHING DIRECTIVE:\n"
        "You have read the above. You know this person. Do not ask them to re-explain "
        "their situation, their goals, or their challenge. Reference what you know naturally, "
        "as a coach who has been working with them would. Be specific. Not generic.\n"
        "If they have overdue commitments, acknowledge them. "
        "If their energy has been low, name it. "
        "If they are approaching a milestone, mention it.\n"
        "Your job is to make them feel genuinely known.\n"
        "═" * 50
    )

    return "\n\n".join(blocks)


def get_context_summary(db: Session, user_id: str) -> dict:
    """
    Return a lightweight summary of what the memory context contains.
    Used by the API to show the user what the coach knows.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return {"error": "Profile not found"}

    days_since = (date.today() - profile.created_at.date()).days

    # Recent check-ins count
    cutoff = date.today() - timedelta(days=14)
    recent_checkins = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date >= cutoff,
        )
        .count()
    )

    # Open commitments
    open_commitments = (
        db.query(Commitment).filter_by(user_id=user_id, status="open").count()
    )

    # Active habits
    active_habits = (
        db.query(HabitRecord).filter_by(user_id=user_id, active=True).count()
    )

    # First Read exists
    has_first_read = (
        db.query(FirstRead).filter_by(user_id=user_id).count() > 0
    )

    # Milestones done
    done_milestones = [
        r.milestone_days
        for r in db.query(RecalibrationSession).filter_by(user_id=user_id).all()
    ]

    return {
        "user_name": profile.full_name,
        "days_since_onboarding": days_since,
        "profile_version": profile.profile_version,
        "recent_checkins_14d": recent_checkins,
        "open_commitments": open_commitments,
        "active_habits": active_habits,
        "has_first_read": has_first_read,
        "milestones_completed": sorted(done_milestones),
        "memory_richness": _memory_richness_label(
            days_since, recent_checkins, active_habits, has_first_read
        ),
    }


def _memory_richness_label(
    days: int, checkins: int, habits: int, has_fr: bool
) -> str:
    score = 0
    if days >= 7:
        score += 1
    if days >= 30:
        score += 1
    if checkins >= 5:
        score += 1
    if checkins >= 10:
        score += 1
    if habits >= 2:
        score += 1
    if has_fr:
        score += 2

    if score >= 6:
        return "deep"
    elif score >= 4:
        return "established"
    elif score >= 2:
        return "developing"
    else:
        return "early"
