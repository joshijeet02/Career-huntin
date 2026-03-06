"""
Commitment Tracker
==================
This is the feature that turns advice into coaching.

The difference between a great coach and a great book is accountability.
A book gives you the framework. A coach remembers what you said you'd do
and asks you about it — every single time — without judgment, but without
letting you off the hook either.

Every commitment the user makes, anywhere in the app, gets tracked here:
  - Evening review: "My one commitment for next week is..."
  - Weekly reflection: "One commitment for next week"
  - Conflict prep: "I will have this conversation by [date]"
  - Decision log: "My next action step is..."
  - Direct conversation: "Coach, I commit to..."

The lifecycle:
  open → due date arrives → coach asks → user responds → kept / missed / partial / deferred

What happens for each outcome:
  kept    → coach celebrates + logs to achievement engine
  missed  → coach asks one non-judgmental question: "What got in the way?"
  partial → coach asks: "What's the one next step to finish it?"
  deferred → coach agrees and sets new due date, notes the pattern

Pattern recognition (after 5+ commitments):
  "You consistently keep commitments made on Monday mornings.
   You have a pattern of deferring commitments made on Friday evenings.
   Your coach recommends making commitments only when your energy is above 7."

The coach does NOT shame missed commitments. Research on behavior change
(Prochaska's Transtheoretical Model, Deci & Ryan's Self-Determination Theory)
shows that shame contracts motivation. The coach is firm and consistent,
but never punitive.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Commitment, DailyCheckIn, UserProfile


# ── Create commitment ─────────────────────────────────────────────────────────

def create_commitment(
    db: Session,
    user_id: str,
    commitment_text: str,
    due_date: str,                  # YYYY-MM-DD
    source: str = "direct",
    source_id: int | None = None,
    parent_goal_id: int | None = None,
    parent_milestone_id: int | None = None,
) -> dict:
    """
    Create a new commitment. Returns the commitment with a coach acknowledgement.
    Due date should be specific — "by end of this week" is not a commitment, Friday is.
    """
    c = Commitment(
        user_id=user_id,
        commitment_text=commitment_text,
        due_date=due_date,
        source=source,
        source_id=source_id,
        status="open",
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    # Coach acknowledgement
    days_until_due = (
        datetime.strptime(due_date, "%Y-%m-%d").date() - date.today()
    ).days

    if days_until_due <= 0:
        time_frame = "today"
    elif days_until_due == 1:
        time_frame = "tomorrow"
    elif days_until_due <= 7:
        time_frame = f"by {datetime.strptime(due_date, '%Y-%m-%d').strftime('%A')}"
    else:
        time_frame = f"by {datetime.strptime(due_date, '%Y-%m-%d').strftime('%B %d')}"

    coach_ack = (
        f"Logged. {time_frame.capitalize()}: {commitment_text}\n\n"
        f"Your coach will check in on this. Not to hold it over you — "
        f"but because that's what a real commitment means."
    )

    return {
        "commitment_id": c.id,
        "commitment_text": c.commitment_text,
        "due_date": c.due_date,
        "status": c.status,
        "source": c.source,
        "parent_goal_id": c.parent_goal_id,
        "parent_milestone_id": c.parent_milestone_id,
        "coach_acknowledgement": coach_ack,
    }


# ── Check in on a commitment ──────────────────────────────────────────────────

def check_commitment(
    db: Session,
    user_id: str,
    commitment_id: int,
    status: str,                    # kept / missed / partial / deferred
    user_note: str = "",
    deferred_to: str = "",          # YYYY-MM-DD if deferring
) -> dict:
    """
    User reports back on a commitment.
    Coach responds based on outcome.
    Kept commitments are forwarded to the achievement engine.
    """
    c = db.query(Commitment).filter_by(id=commitment_id, user_id=user_id).first()
    if not c:
        return {"error": "Commitment not found"}

    if status not in ("kept", "missed", "partial", "deferred"):
        return {"error": f"Invalid status: {status}"}

    c.status = status
    c.user_completion_note = user_note
    c.checked_at = datetime.utcnow().isoformat()
    if status == "deferred" and deferred_to:
        c.deferred_to = deferred_to

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # Coach response
    coach_response = _generate_coach_response(name, c, status, user_note, deferred_to)
    c.coach_followup_message = coach_response

    db.commit()

    return {
        "commitment_id": c.id,
        "commitment_text": c.commitment_text,
        "status": c.status,
        "coach_response": coach_response,
        "pattern_note": _check_for_pattern(db, user_id),
    }


def _generate_coach_response(
    name: str, c: Commitment, status: str, note: str, deferred_to: str
) -> str:
    overdue_days = max(0, (date.today() - datetime.strptime(c.due_date, "%Y-%m-%d").date()).days)

    if status == "kept":
        if overdue_days == 0:
            return (
                f"Done. On time. This is what integrity looks like — "
                f"doing what you said you'd do, by when you said you'd do it. "
                f"Most people underestimate how rare this actually is. "
                f"Your coach is keeping score."
            )
        else:
            return (
                f"It took {overdue_days} extra {'day' if overdue_days == 1 else 'days'}, "
                f"but you got there. That counts. "
                f"Note the pattern though — what delayed it? "
                f"Understanding that is more valuable than the completion."
            )

    elif status == "missed":
        if not note:
            return (
                f"Your coach isn't going to lecture you. "
                f"But missing a commitment you made to yourself means something happened. "
                f"One question: what got in the way? "
                f"Not for judgment — for intelligence. "
                f"The obstacle is always the lesson."
            )
        else:
            # Analyse the note for common patterns
            note_lower = note.lower()
            if any(w in note_lower for w in ["busy", "time", "didn't have time", "no time"]):
                return (
                    f"'Busy' is not a reason — it's a description. "
                    f"Your coach has heard this many times. "
                    f"The question under the question is: did this commitment rank high enough "
                    f"in your true priorities to defend its time? "
                    f"If yes — what would you do differently next time to protect it? "
                    f"If no — that's important data too. Not every commitment needs to be kept. "
                    f"But it does need to be consciously released, not just let slide."
                )
            elif any(w in note_lower for w in ["scared", "afraid", "nervous", "wasn't ready", "not ready"]):
                return (
                    f"Your coach respects this answer. Fear is a signal, not a stop sign. "
                    f"The commitment still matters. "
                    f"What would make you ready? "
                    f"Name one concrete thing, and let's set a new date around that."
                )
            else:
                return (
                    f"Noted. {name}, your coach's job is not to judge — it's to help you understand "
                    f"your own patterns. "
                    f"This commitment: do you still want it? "
                    f"If yes, let's reset with a new date and a clearer path. "
                    f"If not, consciously release it. Either answer is valid. "
                    f"Drift is not."
                )

    elif status == "partial":
        return (
            f"Partial is real progress. Do not dismiss it. "
            f"The question is: what is the specific next step to finish? "
            f"Not 'I'll try to' — the next concrete action, and a date. "
            f"Your coach will reset this commitment with the new scope."
        )

    elif status == "deferred":
        new_date_str = ""
        if deferred_to:
            try:
                new_date_str = datetime.strptime(deferred_to, "%Y-%m-%d").strftime("%B %d")
            except ValueError:
                pass
        return (
            f"Deferred to {new_date_str or deferred_to}. "
            f"That's fine — life is not linear. "
            f"Your coach only asks one thing: is the new date a real commitment or a soft landing? "
            f"If it's real, your coach will be there on {new_date_str or deferred_to}. "
            f"If something has genuinely changed, say so now and we'll close this out cleanly."
        )

    return "Noted."


# ── Pattern recognition ───────────────────────────────────────────────────────

def _check_for_pattern(db: Session, user_id: str) -> str | None:
    """
    After 5+ completed/missed commitments, look for patterns.
    Returns a pattern observation string, or None if insufficient data.
    """
    checked = db.query(Commitment).filter(
        Commitment.user_id == user_id,
        Commitment.status.in_(["kept", "missed", "partial", "deferred"]),
    ).order_by(Commitment.created_at.desc()).limit(20).all()

    if len(checked) < 5:
        return None

    kept = [c for c in checked if c.status == "kept"]
    missed = [c for c in checked if c.status == "missed"]
    deferred = [c for c in checked if c.status == "deferred"]

    kept_rate = len(kept) / len(checked)

    if kept_rate >= 0.85:
        return (
            f"Pattern: You keep {int(kept_rate * 100)}% of your commitments. "
            f"That is exceptional. Most people operate at 40-60%. "
            f"This is one of your most important assets as a leader — protect it."
        )
    elif kept_rate <= 0.40:
        # Check if there's a source pattern
        source_counts: dict[str, dict] = {}
        for c in checked:
            src = c.source
            source_counts.setdefault(src, {"total": 0, "kept": 0})
            source_counts[src]["total"] += 1
            if c.status == "kept":
                source_counts[src]["kept"] += 1

        worst_source = min(
            source_counts,
            key=lambda s: source_counts[s]["kept"] / max(source_counts[s]["total"], 1),
        )
        return (
            f"Pattern: Your commitment completion rate is {int(kept_rate * 100)}% — "
            f"lower than your coach would like to see. "
            f"Commitments made during '{worst_source}' have the lowest follow-through. "
            f"Your coach's hypothesis: you may be committing in reactive moments "
            f"rather than from deliberate intention. "
            f"Try making fewer commitments, but making each one from a place of genuine choice."
        )
    elif len(deferred) >= 3:
        return (
            f"Pattern: You've deferred {len(deferred)} commitments recently. "
            f"Deferral is not failure — but repeated deferral on the same types of commitments "
            f"is information. Your coach is watching for what keeps getting pushed."
        )

    return None


# ── Fetch overdue and due-today commitments ───────────────────────────────────

def get_open_commitments(db: Session, user_id: str) -> dict:
    """
    Returns all open commitments categorised as: due_today, overdue, upcoming.
    Called by morning brief to surface accountability.
    """
    today = date.today().strftime("%Y-%m-%d")
    week_ahead = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

    all_open = db.query(Commitment).filter_by(
        user_id=user_id, status="open"
    ).order_by(Commitment.due_date).all()

    overdue = [c for c in all_open if c.due_date < today]
    due_today = [c for c in all_open if c.due_date == today]
    upcoming = [c for c in all_open if today < c.due_date <= week_ahead]

    def _fmt(c: Commitment) -> dict:
        return {
            "id": c.id,
            "commitment_text": c.commitment_text,
            "due_date": c.due_date,
            "source": c.source,
            "days_overdue": max(
                0,
                (date.today() - datetime.strptime(c.due_date, "%Y-%m-%d").date()).days,
            ),
        }

    # Build morning accountability brief
    coach_note = _build_accountability_brief(due_today, overdue)

    return {
        "overdue": [_fmt(c) for c in overdue],
        "due_today": [_fmt(c) for c in due_today],
        "upcoming_7_days": [_fmt(c) for c in upcoming],
        "total_open": len(all_open),
        "coach_accountability_note": coach_note,
    }


def _build_accountability_brief(due_today: list, overdue: list) -> str:
    if not due_today and not overdue:
        return ""

    lines = []

    if overdue:
        if len(overdue) == 1:
            lines.append(
                f"OVERDUE COMMITMENT: \"{overdue[0].commitment_text}\" "
                f"was due {overdue[0].due_date}. "
                f"Your coach is not letting this slide. "
                f"Before anything else today: what is your plan for this?"
            )
        else:
            items = "\n".join(f"  • {c.commitment_text} (due {c.due_date})" for c in overdue[:3])
            lines.append(
                f"OVERDUE COMMITMENTS ({len(overdue)}):\n{items}\n\n"
                f"These have been open longer than you said they would be. "
                f"Your coach will not pretend they don't exist. "
                f"Pick the most important one. Handle it today."
            )

    if due_today:
        if len(due_today) == 1:
            lines.append(
                f"DUE TODAY: \"{due_today[0].commitment_text}\"\n"
                f"You said you'd do this today. Your coach is watching."
            )
        else:
            items = "\n".join(f"  • {c.commitment_text}" for c in due_today[:3])
            lines.append(
                f"DUE TODAY ({len(due_today)} commitments):\n{items}"
            )

    return "\n\n".join(lines)


# ── Commitment history ────────────────────────────────────────────────────────

def get_commitment_history(db: Session, user_id: str, limit: int = 20) -> dict:
    """Full commitment history with stats — for the accountability dashboard."""
    all_commitments = db.query(Commitment).filter_by(
        user_id=user_id
    ).order_by(Commitment.due_date.desc()).limit(limit).all()

    kept = sum(1 for c in all_commitments if c.status == "kept")
    missed = sum(1 for c in all_commitments if c.status == "missed")
    open_count = sum(1 for c in all_commitments if c.status == "open")
    deferred = sum(1 for c in all_commitments if c.status == "deferred")
    total_closed = kept + missed + sum(1 for c in all_commitments if c.status == "partial")

    completion_rate = round((kept / total_closed * 100) if total_closed > 0 else 0, 1)

    return {
        "total": len(all_commitments),
        "open": open_count,
        "kept": kept,
        "missed": missed,
        "deferred": deferred,
        "completion_rate_pct": completion_rate,
        "pattern_note": _check_for_pattern(db, user_id),
        "commitments": [
            {
                "id": c.id,
                "commitment_text": c.commitment_text,
                "due_date": c.due_date,
                "status": c.status,
                "source": c.source,
                "user_completion_note": c.user_completion_note,
                "coach_followup_message": c.coach_followup_message,
            }
            for c in all_commitments
        ],
    }
