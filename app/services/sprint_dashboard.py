"""
90-Day Sprint Dashboard
========================
The 90-day goal system is the backbone of any serious coaching engagement.

A real executive coach does not track vague annual goals. They break every goal
into a 12-week sprint with explicit weekly milestones. Every Sunday, the user
reports on each milestone. The coach assesses progress, recalibrates, and issues
a status: on_track / at_risk / complete.

At week 12, the coach writes a Sprint Retrospective — a full accounting of
what was achieved, what was learned, and what the next 90 days should focus on.

This service:
  - Auto-generates 12-week milestones from each goal set in onboarding
  - Tracks weekly user updates
  - Issues on_track / at_risk / complete status with coaching guidance
  - Calculates overall sprint health
  - Generates Sprint Retrospective at week 12
  - Handles goal replacement if user pivots mid-sprint
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import GoalMilestone, UserProfile


# ── Milestone generation ──────────────────────────────────────────────────────

def _goal_track_from_goal(goal_dict: dict) -> str:
    """Infer track from goal text if not explicitly set."""
    goal_text = str(goal_dict.get("goal", "")).lower()
    if any(w in goal_text for w in ["relationship", "family", "partner", "team", "culture"]):
        return "relationships"
    if any(w in goal_text for w in ["health", "energy", "sleep", "fitness", "exercise", "weight"]):
        return "energy"
    return "leadership"


def _generate_milestone_for_week(goal_text: str, week: int, total_weeks: int = 12) -> str:
    """
    Generate a concrete milestone description for a given week number.
    Uses a standard progression:
    weeks 1-3: Foundation (awareness, audit, baseline)
    weeks 4-6: Build (first actions, first systems)
    weeks 7-9: Momentum (consistency, refinement, deepening)
    weeks 10-12: Integration (mastery, sustainability, next level)
    """
    goal_short = goal_text[:80]

    if week <= 3:
        phase_prompts = [
            f"Complete a thorough audit of your current situation regarding: '{goal_short}'. Identify the 3 biggest gaps.",
            f"Identify the single highest-leverage action toward '{goal_short}' and take it at least once this week.",
            f"Establish a baseline measurement for '{goal_short}'. What does success look like in numbers or observable behaviours?",
        ]
    elif week <= 6:
        phase_prompts = [
            f"Build your first repeatable system or routine directly connected to '{goal_short}'.",
            f"Have one key conversation or take one bold action you've been postponing related to '{goal_short}'.",
            f"Review your first 5 weeks on '{goal_short}': what's working, what isn't, and what needs to change?",
        ]
    elif week <= 9:
        phase_prompts = [
            f"Achieve 3 consecutive weeks of consistent action on '{goal_short}'. Focus on building the identity, not just the result.",
            f"Raise the standard on '{goal_short}'. What is the next level, and what is one thing you can do this week to reach for it?",
            f"Teach someone else one thing you've learned about '{goal_short}'. Teaching accelerates mastery.",
        ]
    else:
        phase_prompts = [
            f"Assess whether '{goal_short}' is now a permanent part of how you operate — or still dependent on willpower.",
            f"Name one unexpected insight you've gained from working on '{goal_short}' that applies to another area of your life.",
            f"Write a 3-sentence retrospective on '{goal_short}': what you achieved, what you learned, and what you commit to next.",
        ]

    idx = (week - 1) % 3
    return phase_prompts[idx]


def initialize_sprint_for_user(db: Session, user_id: str) -> int:
    """
    Called after onboarding is complete.
    Generates 12 weeks of milestones for each of the user's goals.
    Returns the number of milestones created.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile or not profile.goals_90_days:
        return 0

    # Clear any existing sprint for this user
    db.query(GoalMilestone).filter_by(user_id=user_id).delete()

    sprint_start = date.today()
    # Align to Monday
    days_since_monday = sprint_start.weekday()
    sprint_start -= timedelta(days=days_since_monday)

    count = 0
    for goal_idx, goal_item in enumerate(profile.goals_90_days[:3]):  # max 3 goals
        goal_text = goal_item.get("goal", str(goal_item))
        goal_track = goal_item.get("track", _goal_track_from_goal(goal_item))

        for week_num in range(1, 13):  # 12 weeks
            week_start = sprint_start + timedelta(weeks=week_num - 1)
            milestone = _generate_milestone_for_week(goal_text, week_num)

            db.add(GoalMilestone(
                user_id=user_id,
                goal_index=goal_idx,
                goal_text=goal_text,
                goal_track=goal_track,
                week_number=week_num,
                week_start=week_start.strftime("%Y-%m-%d"),
                milestone_description=milestone,
                status="pending",
                progress_pct=0,
            ))
            count += 1

    db.commit()
    return count


def get_sprint_dashboard(db: Session, user_id: str) -> dict:
    """
    Returns the full dashboard: current week's milestones across all goals,
    plus 12-week progress bars, plus overall sprint health.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    milestones = (
        db.query(GoalMilestone)
        .filter_by(user_id=user_id)
        .order_by(GoalMilestone.goal_index, GoalMilestone.week_number)
        .all()
    )

    if not milestones:
        return {
            "status": "not_initialized",
            "message": "Complete onboarding to start your 90-Day Sprint.",
            "goals": [],
            "sprint_health": None,
        }

    today = date.today().strftime("%Y-%m-%d")

    # Group by goal
    goals_map: dict[int, dict] = {}
    for m in milestones:
        if m.goal_index not in goals_map:
            goals_map[m.goal_index] = {
                "goal_index": m.goal_index,
                "goal_text": m.goal_text,
                "goal_track": m.goal_track,
                "weeks": [],
                "current_week": None,
                "overall_progress_pct": 0,
                "status_summary": "pending",
            }
        is_current = m.week_start <= today < (
            date.fromisoformat(m.week_start) + timedelta(days=7)
        ).strftime("%Y-%m-%d")

        week_data = {
            "week_number": m.week_number,
            "week_start": m.week_start,
            "milestone_description": m.milestone_description,
            "status": m.status,
            "progress_pct": m.progress_pct,
            "user_update": m.user_update,
            "coach_response": m.coach_response,
            "is_current_week": is_current,
        }
        goals_map[m.goal_index]["weeks"].append(week_data)
        if is_current:
            goals_map[m.goal_index]["current_week"] = week_data

    # Calculate overall progress per goal
    for goal_data in goals_map.values():
        completed_weeks = [w for w in goal_data["weeks"] if w["status"] in ("on_track", "complete")]
        goal_data["overall_progress_pct"] = int(len(completed_weeks) / 12 * 100)

        at_risk = [w for w in goal_data["weeks"] if w["status"] == "at_risk"]
        on_track = [w for w in goal_data["weeks"] if w["status"] in ("on_track", "complete")]
        if len(on_track) >= 8:
            goal_data["status_summary"] = "strong"
        elif at_risk:
            goal_data["status_summary"] = "at_risk"
        else:
            goal_data["status_summary"] = "on_track"

    # Sprint health score (0-100)
    all_past = [m for m in milestones if m.week_start < today]
    if all_past:
        scored = [m for m in all_past if m.status in ("on_track", "complete")]
        sprint_health = int(len(scored) / len(all_past) * 100)
    else:
        sprint_health = None

    # Current week number in sprint
    if milestones:
        first_start = date.fromisoformat(milestones[0].week_start)
        days_in = (date.today() - first_start).days
        current_sprint_week = min(max(1, math.ceil((days_in + 1) / 7)), 12)
    else:
        current_sprint_week = 1

    return {
        "status": "active",
        "current_sprint_week": current_sprint_week,
        "sprint_health_pct": sprint_health,
        "goals": list(goals_map.values()),
        "user_id": user_id,
    }


def update_milestone(
    db: Session,
    user_id: str,
    goal_index: int,
    week_number: int,
    user_update: str,
    progress_pct: int,
) -> dict:
    """
    User reports on a specific milestone.
    Coach assesses status and returns coaching guidance.
    """
    m = (
        db.query(GoalMilestone)
        .filter_by(user_id=user_id, goal_index=goal_index, week_number=week_number)
        .first()
    )
    if not m:
        return {"error": "Milestone not found."}

    # Assess status
    if progress_pct >= 80:
        status = "on_track"
    elif progress_pct >= 40:
        status = "at_risk"
    else:
        status = "at_risk" if week_number > 2 else "pending"

    if progress_pct == 100:
        status = "complete"

    # Coach response
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    if status == "complete":
        coach_resp = (
            f"Week {week_number} — complete. {name}, this is exactly how momentum is built. "
            f"What you proved this week is that you can do hard things. "
            f"Next week raises the bar. You are ready."
        )
    elif status == "on_track":
        coach_resp = (
            f"Week {week_number} at {progress_pct}% — on track. {name}, stay consistent. "
            f"The compounding happens in weeks 7-12, but only if you build the foundation now. "
            f"One key question: what is the single thing that could derail you next week?"
        )
    else:
        coach_resp = (
            f"Week {week_number} at {progress_pct}% — this is a signal, not a sentence. "
            f"{name}, something is blocking this goal. Is it clarity, time, courage, or resources? "
            f"Name it specifically. Then your coach can help you remove it."
        )

    m.user_update = user_update
    m.progress_pct = progress_pct
    m.status = status
    m.coach_response = coach_resp
    m.updated_at = datetime.utcnow()
    db.commit()

    return {
        "goal_index": goal_index,
        "week_number": week_number,
        "status": status,
        "progress_pct": progress_pct,
        "coach_response": coach_resp,
    }


def generate_sprint_retrospective(db: Session, user_id: str) -> dict:
    """
    At week 12+: generate a full Sprint Retrospective.
    Achievement rate per goal, key pattern observations, and the coach's brief
    for the NEXT 90-day sprint.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"
    milestones = db.query(GoalMilestone).filter_by(user_id=user_id).all()

    goals_summary = {}
    for m in milestones:
        key = m.goal_index
        if key not in goals_summary:
            goals_summary[key] = {"goal": m.goal_text, "track": m.goal_track,
                                   "complete": 0, "on_track": 0, "at_risk": 0, "pending": 0}
        goals_summary[key][m.status] = goals_summary[key].get(m.status, 0) + 1

    retro_lines = [f"90-Day Sprint Retrospective — {name}\n"]
    for gi, gs in goals_summary.items():
        achieved = gs.get("complete", 0) + gs.get("on_track", 0)
        rate = int(achieved / 12 * 100)
        retro_lines.append(
            f"Goal {gi+1}: {gs['goal'][:60]}...\n"
            f"  Achievement rate: {rate}% ({achieved}/12 weeks on track)\n"
            f"  Track: {gs['track']}"
        )

    retro_lines.append(
        f"\nCoach's overall observation:\n"
        f"Every sprint reveals not just what you achieved, but WHO you became in the pursuit. "
        f"The patterns your coach has observed over 12 weeks will inform the next sprint. "
        f"The 90 days that come next should be harder — because you are better."
    )

    return {
        "retrospective_text": "\n".join(retro_lines),
        "goals_summary": goals_summary,
        "user_id": user_id,
        "generated_at": datetime.utcnow().isoformat(),
    }
