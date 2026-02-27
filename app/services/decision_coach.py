"""
Decision Pre-Mortem + Decision Log
====================================
Before every significant decision, a great coach runs a pre-mortem.
"Imagine it's 12 months from now and this decision failed catastrophically. What happened?"

This is not pessimism. It is structured foresight.
It forces the leader to surface assumptions, identify risks they are unconsciously ignoring,
and separate gut intuition from rationalised bias.

The Decision Log stores every decision with its reasoning.
30 days later, the coach reviews it: what actually happened, and what does the pattern say
about how this person makes decisions under pressure?

Over time, this becomes the most valuable coaching artifact in the system.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import DecisionLog, UserProfile


_PREMORTEM_QUESTIONS = [
    "What is the decision you are making?",
    "What are the 2-3 options you are choosing between?",
    "Imagine it is 12 months from now and this decision turned out to be wrong. What went wrong?",
    "What does your gut say — separate from your analysis?",
    "Who else will be significantly affected by this decision, and have you thought about their perspective?",
]


def start_decision_premortem(db: Session, user_id: str) -> dict:
    """Returns the pre-mortem question sequence."""
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"
    return {
        "intro": (
            f"{name}, before you decide — your coach has 5 questions. "
            f"A decision made without a pre-mortem is a decision made half-blind. "
            f"This takes 10 minutes. It has saved careers."
        ),
        "questions": _PREMORTEM_QUESTIONS,
    }


def log_decision(
    db: Session,
    user_id: str,
    decision_title: str,
    decision_description: str,
    options_considered: list[str],
    premortem_failure_modes: list[str],
    gut_says: str,
) -> dict:
    """
    Saves the decision with a coach recommendation.
    Automatically schedules a 30-day review.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    today = date.today().strftime("%Y-%m-%d")
    review_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")

    # Build coach recommendation
    failure_str = "; ".join(premortem_failure_modes[:3])
    options_str = ", ".join(f'"{o}"' for o in options_considered[:3])

    coach_rec = (
        f"Decision registered: \"{decision_title}\"\n\n"
        f"Your pre-mortem identified these failure modes: {failure_str}.\n\n"
        f"Coach's guidance:\n"
        f"  1. Before you finalise — share this decision with one person whose judgment you respect "
        f"     and who has no stake in the outcome. What do they see that you don't?\n"
        f"  2. The fact that your gut says \"{gut_says[:80]}\" matters. "
        f"     Your gut is your pattern recognition engine. If it conflicts with your analysis, "
        f"     find out why before you decide.\n"
        f"  3. Set a decision deadline: give yourself 48 hours maximum from now. "
        f"     Delayed decisions are their own kind of decision.\n\n"
        f"Your coach will review this decision with you on {review_date}. "
        f"Write down what you actually decided and why — before you forget the real reason."
    )

    entry = DecisionLog(
        user_id=user_id,
        decision_date=today,
        decision_title=decision_title,
        decision_description=decision_description,
        options_considered=options_considered,
        premortem_failure_modes=premortem_failure_modes,
        gut_says=gut_says,
        coach_recommendation=coach_rec,
        final_decision="",
        review_date=review_date,
        reviewed=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "decision_id": entry.id,
        "coach_recommendation": coach_rec,
        "review_date": review_date,
        "message": f"Decision logged. Your coach will revisit this with you on {review_date}.",
    }


def record_final_decision(db: Session, decision_id: int, user_id: str, final_decision: str) -> dict:
    """User records what they actually decided."""
    entry = db.query(DecisionLog).filter_by(id=decision_id, user_id=user_id).first()
    if not entry:
        return {"error": "Decision not found."}
    entry.final_decision = final_decision
    db.commit()
    return {"message": "Final decision recorded. Your coach will review outcomes on " + entry.review_date}


def run_decision_review(db: Session, decision_id: int, user_id: str, actual_outcome: str) -> dict:
    """
    30-day review: what actually happened vs. what was feared.
    The coach writes an observation about the decision quality — not the outcome.
    (Good decisions can have bad outcomes. Bad decisions can get lucky. The coach knows the difference.)
    """
    entry = db.query(DecisionLog).filter_by(id=decision_id, user_id=user_id).first()
    if not entry:
        return {"error": "Decision not found."}

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    observation = (
        f"30-Day Decision Review: \"{entry.decision_title}\"\n\n"
        f"What you feared: {'; '.join(entry.premortem_failure_modes[:2]) if entry.premortem_failure_modes else 'not specified'}\n"
        f"What actually happened: {actual_outcome[:300]}\n\n"
        f"Coach's observation:\n"
        f"  The quality of a decision is not the same as the quality of the outcome. "
        f"  Your coach is evaluating whether you gathered the right information, "
        f"  considered the right stakeholders, and made the decision from a place of clarity — not fear.\n\n"
        f"  {name}, what does this outcome reveal about your pre-mortem accuracy? "
        f"  Did your fears materialise? Did something you didn't anticipate emerge? "
        f"  The answer tells you something important about your current blindspots."
    )

    entry.actual_outcome = actual_outcome
    entry.coach_review_observation = observation
    entry.reviewed = True
    db.commit()

    return {
        "coach_review_observation": observation,
        "decision_id": decision_id,
        "reviewed_at": datetime.utcnow().isoformat(),
    }


def list_pending_reviews(db: Session, user_id: str) -> list[dict]:
    """Decisions that are past their review date and haven't been reviewed yet."""
    today = date.today().strftime("%Y-%m-%d")
    pending = (
        db.query(DecisionLog)
        .filter(
            DecisionLog.user_id == user_id,
            DecisionLog.reviewed == False,
            DecisionLog.review_date <= today,
            DecisionLog.final_decision != "",
        )
        .all()
    )
    return [
        {
            "decision_id": d.id,
            "decision_title": d.decision_title,
            "decision_date": d.decision_date,
            "review_date": d.review_date,
            "days_overdue": (date.today() - date.fromisoformat(d.review_date)).days,
        }
        for d in pending
    ]


def get_decision_pattern_analysis(db: Session, user_id: str) -> dict:
    """
    After 5+ logged decisions, the coach identifies patterns:
    - Does this person over-analyse and decide late?
    - Do their fears match what actually happens?
    - Are they making the same type of decisions repeatedly?
    """
    all_decisions = db.query(DecisionLog).filter_by(user_id=user_id).all()
    reviewed = [d for d in all_decisions if d.reviewed]

    if len(all_decisions) < 3:
        return {
            "message": "Log at least 3 decisions for your coach to identify patterns in how you decide.",
            "decisions_logged": len(all_decisions),
        }

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    avg_options = sum(len(d.options_considered) for d in all_decisions) / len(all_decisions)
    avg_fears = sum(len(d.premortem_failure_modes) for d in all_decisions) / len(all_decisions)

    pattern_text = f"Coach's Decision Pattern Analysis — {name}\n\n"
    pattern_text += f"Decisions logged: {len(all_decisions)} | Reviewed: {len(reviewed)}\n\n"

    if avg_options < 2:
        pattern_text += (
            "Pattern: You tend to bring decisions to your coach when you already have one option in mind. "
            "This may indicate you are seeking validation rather than genuine exploration. "
            "Your coach's challenge: the next time you bring a decision, ensure you have genuinely considered at least 3 options.\n\n"
        )

    if avg_fears < 2:
        pattern_text += (
            "Pattern: Your pre-mortems tend to be thin — fewer than 2 failure modes on average. "
            "This suggests optimism bias. The decisions you will regret most are the ones where you "
            "didn't ask 'what could go wrong?' with enough seriousness.\n\n"
        )

    if reviewed:
        gut_confirmed = sum(
            1 for d in reviewed
            if d.gut_says.lower() in (d.actual_outcome or "").lower()
        )
        if gut_confirmed / len(reviewed) > 0.6:
            pattern_text += (
                "Pattern: Your gut has been right more often than your analysis. "
                f"In {gut_confirmed} of {len(reviewed)} reviewed decisions, your intuition aligned with actual outcomes. "
                "Trust it more.\n\n"
            )

    return {"pattern_analysis": pattern_text, "decisions_logged": len(all_decisions)}
