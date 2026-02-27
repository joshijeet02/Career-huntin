"""
30/60/90-Day Profile Re-calibration
=====================================
"The coaching relationship is not a static interview at day one.
 It is a living document that deepens every week."

The onboarding interview captures who the user is on day one.
But people change. Goals get achieved or abandoned. New stressors emerge.
Values crystallise or shift. The challenges that felt acute in week one
may be resolved by week four — and replaced by something more interesting.

A real coaching relationship accounts for this. The coach re-interviews
the client at structured milestones, updating the profile they carry
into every conversation.

Milestone 30 days:
  Focus: What has changed? Initial goals — any progress, any pivots?
  Energy and wellbeing — how has the first month felt?
  What has surprised you about yourself?

Milestone 60 days:
  Focus: Relationship check-in. How are the key relationships?
  What has the coach helped most with? Where is there still friction?
  Are the 90-day goals still the right goals?

Milestone 90 days:
  Focus: Full re-interview. New goals for the next 90 days.
  Updated biggest challenge. Refined values.
  What kind of leader do you want to be in the next 90 days?

After each re-calibration, the UserProfile is updated directly —
so every subsequent coaching response reflects the updated context.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import DailyCheckIn, RecalibrationSession, UserProfile


# ── Milestone questions ───────────────────────────────────────────────────────

_QUESTIONS_30 = [
    {
        "id": "progress_on_goals",
        "question": (
            "When we started, you told me your 90-day goals. "
            "One month has passed. Pick the goal that feels most alive right now "
            "and tell me: where are you with it, honestly?"
        ),
    },
    {
        "id": "biggest_surprise",
        "question": (
            "What has surprised you most about yourself in the past month? "
            "Not what you expected — what actually showed up."
        ),
    },
    {
        "id": "energy_reflection",
        "question": (
            "Your energy data tells one story. Your experience tells another. "
            "How have you genuinely been feeling this past month — "
            "not what you tell people, what you actually know?"
        ),
    },
    {
        "id": "what_needs_to_change",
        "question": (
            "If you could change one thing about how your days are structured "
            "or how you're showing up — one thing — what would it be?"
        ),
    },
    {
        "id": "updated_challenge",
        "question": (
            "At the start, you named your biggest challenge. "
            "Is it still the same, or has something else surfaced as more urgent?"
        ),
    },
]

_QUESTIONS_60 = [
    {
        "id": "relationship_health",
        "question": (
            "Let's talk about the people who matter most to you — "
            "professionally and personally. "
            "Which relationship feels healthiest right now? "
            "Which one needs the most attention?"
        ),
    },
    {
        "id": "goals_check",
        "question": (
            "We are at the halfway point of your 90-day sprint. "
            "Your original goals — are they still the right goals? "
            "Or has life shown you something different?"
        ),
    },
    {
        "id": "coach_feedback",
        "question": (
            "Be direct with me: where has the coaching been most useful to you? "
            "Where has it missed the mark?"
        ),
    },
    {
        "id": "leadership_edge",
        "question": (
            "What is the edge of your leadership capability right now — "
            "the place where you're being stretched most? "
            "What does growing through that edge look like?"
        ),
    },
    {
        "id": "values_check",
        "question": (
            "Your values at onboarding: are you living by them? "
            "Is there a gap between what you said matters most and "
            "where your actual time and energy go?"
        ),
    },
]

_QUESTIONS_90 = [
    {
        "id": "90_day_audit",
        "question": (
            "Ninety days. Your coach wants an honest audit: "
            "what actually changed? Not what you hoped would change — "
            "what tangibly, verifiably, changed?"
        ),
    },
    {
        "id": "new_goals",
        "question": (
            "The next 90 days are a blank canvas. "
            "What are the one to three things — if you accomplished them — "
            "that would make this the most meaningful quarter of your professional life so far?"
        ),
    },
    {
        "id": "updated_challenge",
        "question": (
            "What is your biggest challenge right now — the thing keeping you up, "
            "the friction that won't resolve? "
            "Be specific. Not 'balance' — what specifically is out of balance?"
        ),
    },
    {
        "id": "leader_identity",
        "question": (
            "Who do you want to be as a leader in the next 90 days? "
            "Not what you want to achieve — who do you want to become? "
            "Describe the person, not the results."
        ),
    },
    {
        "id": "key_relationships_update",
        "question": (
            "Update your relationship map. Who are the three to five people "
            "who will matter most to your success and wellbeing "
            "in the next 90 days? "
            "For each, what is your intention for that relationship?"
        ),
    },
    {
        "id": "coaching_style_update",
        "question": (
            "How has your relationship with coaching evolved? "
            "What does your ideal coaching experience look like for the next 90 days — "
            "harder, gentler, more tactical, more philosophical?"
        ),
    },
]


def get_questions_for_milestone(milestone_days: int) -> list[dict]:
    if milestone_days == 30:
        return _QUESTIONS_30
    elif milestone_days == 60:
        return _QUESTIONS_60
    elif milestone_days == 90:
        return _QUESTIONS_90
    return _QUESTIONS_30


# ── Milestone check ───────────────────────────────────────────────────────────

def check_recalibration_due(db: Session, user_id: str) -> dict:
    """
    Check if a recalibration milestone is due.
    Returns the next milestone (30, 60, or 90) if it hasn't been completed yet.
    Returns None if all milestones done or onboarding not complete.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile or not profile.onboarding_complete:
        return {"due": False}

    # Days since onboarding completed
    days_since_onboarding = (date.today() - profile.created_at.date()).days

    # Check which milestones have been done
    done_milestones = {
        r.milestone_days
        for r in db.query(RecalibrationSession).filter_by(user_id=user_id).all()
    }

    for milestone in [30, 60, 90]:
        if days_since_onboarding >= milestone and milestone not in done_milestones:
            return {
                "due": True,
                "milestone_days": milestone,
                "days_since_onboarding": days_since_onboarding,
                "questions": get_questions_for_milestone(milestone),
                "coach_intro": _get_milestone_intro(profile, milestone, days_since_onboarding),
            }

    return {"due": False, "days_since_onboarding": days_since_onboarding}


def _get_milestone_intro(profile: UserProfile, milestone: int, actual_days: int) -> str:
    name = profile.full_name.split()[0] if profile.full_name else "friend"

    if milestone == 30:
        return (
            f"{name}, a month has passed since we began. "
            f"Your coach has been watching the data — your energy, your habits, your check-ins. "
            f"But data is not the full picture. "
            f"It is time to sit down and talk about what is actually happening. "
            f"I am going to ask you five questions. "
            f"Take your time. There is no right answer — only an honest one."
        )
    elif milestone == 60:
        return (
            f"Sixty days, {name}. We are at the halfway point. "
            f"In the past two months your coach has seen you in your highs, your lows, "
            f"your momentum and your resistance. "
            f"Now it is time to recalibrate — to look at what is still serving you "
            f"and what needs to shift for the back half of the sprint. "
            f"Five questions. Be honest."
        )
    elif milestone == 90:
        return (
            f"Ninety days, {name}. "
            f"This is not a check-in. This is a reckoning. "
            f"When we started, you told me what you wanted to achieve and who you wanted to become. "
            f"Today your coach wants to know: what actually happened? "
            f"Not the polished version — the real version. "
            f"And then we are going to build the next 90 days from what you have learned. "
            f"Six questions. This will take 20 minutes and they will be worth it."
        )
    return f"{name}, let's recalibrate."


# ── Process recalibration answers ─────────────────────────────────────────────

def process_recalibration_answer(
    db: Session,
    user_id: str,
    milestone_days: int,
    question_id: str,
    answer: str,
) -> dict:
    """
    Accept one answer at a time for the re-calibration interview.
    Returns the next question, or synthesis if all done.
    """
    questions = get_questions_for_milestone(milestone_days)
    question_ids = [q["id"] for q in questions]

    if question_id not in question_ids:
        return {"error": f"Unknown question_id: {question_id}"}

    # Load or create the session record
    session = db.query(RecalibrationSession).filter_by(
        user_id=user_id, milestone_days=milestone_days
    ).first()

    if not session:
        session = RecalibrationSession(
            user_id=user_id,
            milestone_days=milestone_days,
            session_date=date.today().strftime("%Y-%m-%d"),
            questions_asked=question_ids,
            answers_raw={},
        )
        db.add(session)

    # Save answer
    answers = dict(session.answers_raw or {})
    answers[question_id] = answer
    session.answers_raw = answers
    db.commit()

    # Find next unanswered question
    answered_ids = set(answers.keys())
    next_q = None
    for q in questions:
        if q["id"] not in answered_ids:
            next_q = q
            break

    if next_q:
        return {
            "complete": False,
            "question_id": next_q["id"],
            "question": next_q["question"],
            "answered": len(answered_ids),
            "total": len(questions),
        }
    else:
        # All answered — synthesize and update profile
        synthesis, profile_changes = _synthesize_and_update_profile(
            db, user_id, milestone_days, answers
        )
        session.coach_synthesis = synthesis
        session.profile_changes = profile_changes
        db.commit()

        return {
            "complete": True,
            "milestone_days": milestone_days,
            "coach_synthesis": synthesis,
            "profile_updated": True,
            "profile_changes_summary": list(profile_changes.keys()),
        }


def _synthesize_and_update_profile(
    db: Session, user_id: str, milestone_days: int, answers: dict
) -> tuple[str, dict]:
    """
    After all answers received, update UserProfile and generate synthesis.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return "Profile not found.", {}

    name = profile.full_name.split()[0] if profile.full_name else "friend"
    changes: dict = {}

    # Update profile fields based on answers
    if milestone_days == 90:
        # Full re-interview — update goals, challenge, coaching style
        if "new_goals" in answers and answers["new_goals"].strip():
            # Parse goals from free text (simplified — coach uses raw text)
            raw_goals = answers["new_goals"]
            # Split by common separators
            import re
            goal_lines = [
                g.strip().lstrip("1234567890.-) ").strip()
                for g in re.split(r"[\n,;]|(?:\d+[\.\)])", raw_goals)
                if len(g.strip()) > 10
            ]
            if goal_lines:
                profile.goals_90_days = goal_lines[:3]
                changes["goals_90_days"] = goal_lines[:3]

        if "updated_challenge" in answers:
            profile.biggest_challenge = answers["updated_challenge"]
            changes["biggest_challenge"] = answers["updated_challenge"]

        if "coaching_style_update" in answers:
            answer_lower = answers["coaching_style_update"].lower()
            if any(w in answer_lower for w in ["harder", "tougher", "more direct", "push"]):
                profile.coaching_style_preference = "direct"
                changes["coaching_style_preference"] = "direct"
            elif any(w in answer_lower for w in ["gentler", "softer", "supportive", "warm"]):
                profile.coaching_style_preference = "supportive"
                changes["coaching_style_preference"] = "supportive"

    elif milestone_days in (30, 60):
        if "updated_challenge" in answers:
            profile.biggest_challenge = answers["updated_challenge"]
            changes["biggest_challenge"] = answers["updated_challenge"]

    profile.profile_version += 1
    profile.last_profile_update = datetime.utcnow()
    db.commit()

    # Generate synthesis
    lines = []

    if milestone_days == 30:
        lines.append(
            f"{name}, your coach has read everything you've shared. "
            f"Here is what I am carrying forward into the next 30 days."
        )
        if "biggest_surprise" in answers:
            lines.append(
                f"The most important thing you told me: what surprised you. "
                f"That surprise is worth examining — it is usually where the growth is."
            )
        if "what_needs_to_change" in answers:
            lines.append(
                f"You named what needs to change. That is the work of the next 30 days. "
                f"Your coach will hold you to it."
            )

    elif milestone_days == 60:
        lines.append(
            f"Sixty days in, {name}. Here is what your coach now knows about you "
            f"that wasn't visible at day one."
        )
        if "relationship_health" in answers:
            lines.append(
                f"You named the relationship that needs attention. "
                f"Your coach will prioritise this in the next 30 days."
            )

    elif milestone_days == 90:
        lines.append(
            f"Ninety days, {name}. Your profile has been updated with your new goals, "
            f"your updated challenge, and your refined coaching preferences. "
            f"The next sprint begins now."
        )
        if changes.get("goals_90_days"):
            goals_str = "\n".join(f"  {i+1}. {g}" for i, g in enumerate(changes["goals_90_days"]))
            lines.append(f"Your next 90-day goals:\n{goals_str}")
        lines.append(
            f"Your coach has updated every context that flows into our daily work together. "
            f"The coaching you receive from this point will reflect who you are now — "
            f"not who you were on day one."
        )

    return "\n\n".join(lines), changes
