"""
7-Day Trial Closing Report
===========================
"The trial closing report is not a marketing email.
 It is the product's most important feature."

The moment a user reaches the end of their free trial is the highest-leverage
moment in the entire product lifecycle. Most apps send an email. We build the
moment directly into the product — a coach-voiced, data-rich retrospective of
the seven days, delivered in the app itself.

What makes someone pay:
  1. They see themselves clearly reflected back (mirror quality)
  2. They feel the gap — what they'll lose if they leave
  3. They see a specific next step that only the coach can deliver

The Closing Report achieves all three.

Structure:
  Opening      — coach names what it saw in 7 days (not generic)
  The Data     — hard numbers: check-ins, habits, energy arc, commitments
  The Insight  — the single most important thing the coach learned about them
  The Gap      — what is still unresolved, what the next 30 days could do
  The Offer    — one concrete sentence: what the coach will do in month two
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Commitment,
    DailyCheckIn,
    FirstRead,
    HabitCompletion,
    HabitRecord,
    TrialClosingReport,
    UserProfile,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _energy_arc(checkins: list) -> tuple[float, float, float, str]:
    """Return (start_avg, end_avg, overall_avg, direction_label)."""
    if not checkins:
        return 0.0, 0.0, 0.0, "unknown"

    sorted_ci = sorted(checkins, key=lambda c: c.checkin_date)
    energies = [c.energy_level for c in sorted_ci if c.energy_level is not None]

    if not energies:
        return 0.0, 0.0, 0.0, "unknown"

    overall = sum(energies) / len(energies)

    # First half vs second half
    mid = max(1, len(energies) // 2)
    start_avg = sum(energies[:mid]) / mid
    end_avg = sum(energies[mid:]) / max(1, len(energies) - mid)

    delta = end_avg - start_avg
    if delta > 0.5:
        direction = "rising"
    elif delta < -0.5:
        direction = "declining"
    else:
        direction = "steady"

    return round(start_avg, 1), round(end_avg, 1), round(overall, 1), direction


def _habit_summary(db: Session, user_id: str, start: date, end: date) -> dict:
    """Completions, rate, best habit by name."""
    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()
    habit_map = {h.id: h.name for h in habits}
    total_habits = len(habits)

    if total_habits == 0:
        return {"total_habits": 0, "completions": 0, "completion_rate": 0, "best_habit": None}

    completions = (
        db.query(HabitCompletion)
        .filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.completion_date >= start,
            HabitCompletion.completion_date <= end,
        )
        .all()
    )

    total_completions = len(completions)

    # Days in range × habits = possible completions
    days_in_range = (end - start).days + 1
    possible = total_habits * days_in_range
    rate = round((total_completions / possible) * 100) if possible > 0 else 0

    # Best habit: highest completion count
    counts: dict[int, int] = {}
    for c in completions:
        counts[c.habit_id] = counts.get(c.habit_id, 0) + 1
    best_id = max(counts, key=lambda k: counts[k]) if counts else None
    best_habit = habit_map.get(best_id) if best_id else None

    return {
        "total_habits": total_habits,
        "completions": total_completions,
        "completion_rate": rate,
        "best_habit": best_habit,
    }


def _commitment_summary(db: Session, user_id: str, start: date, end: date) -> dict:
    commitments = (
        db.query(Commitment)
        .filter(
            Commitment.user_id == user_id,
            Commitment.created_at >= datetime.combine(start, datetime.min.time()),
            Commitment.created_at <= datetime.combine(end, datetime.max.time()),
        )
        .all()
    )

    total = len(commitments)
    kept = sum(1 for c in commitments if c.status == "kept")
    missed = sum(1 for c in commitments if c.status == "missed")
    open_count = sum(1 for c in commitments if c.status == "open")

    rate = round((kept / total) * 100) if total > 0 else 0
    return {
        "total": total,
        "kept": kept,
        "missed": missed,
        "open": open_count,
        "kept_rate_pct": rate,
    }


# ── Section builders ──────────────────────────────────────────────────────────

def _build_opening(
    profile: UserProfile,
    checkin_count: int,
    habit_data: dict,
    energy: tuple,
    trial_days: int,
) -> str:
    name = profile.full_name.split()[0] if profile.full_name else "friend"
    start_avg, end_avg, overall_avg, direction = energy

    direction_phrase = {
        "rising": "your energy rose across the week",
        "declining": "your energy dipped as the week wore on — which tells its own story",
        "steady": "your energy held steady across the week",
        "unknown": "your energy levels were recorded",
    }.get(direction, "your energy was recorded")

    lines = [
        f"{name}. Seven days.",
        "",
        f"In {trial_days} days, you checked in {checkin_count} time{'s' if checkin_count != 1 else ''}. "
        f"You tracked {habit_data['total_habits']} habit{'s' if habit_data['total_habits'] != 1 else ''}. "
        f"And {direction_phrase}.",
        "",
        "Your coach has been watching. Not the numbers — the patterns behind the numbers. "
        "What follows is what I actually saw.",
    ]
    return "\n".join(lines)


def _build_data_section(
    checkin_count: int,
    habit_data: dict,
    commitment_data: dict,
    energy: tuple,
    trial_days: int,
) -> str:
    start_avg, end_avg, overall_avg, direction = energy
    lines = ["THE NUMBERS"]
    lines.append("─" * 40)

    # Check-in consistency
    possible_checkins = trial_days
    checkin_pct = round((checkin_count / possible_checkins) * 100) if possible_checkins > 0 else 0
    lines.append(
        f"Check-in consistency   {checkin_count}/{possible_checkins} days   "
        f"({checkin_pct}%)"
    )

    # Habit completion
    if habit_data["total_habits"] > 0:
        lines.append(
            f"Habit completion       {habit_data['completions']} completions   "
            f"({habit_data['completion_rate']}% rate)"
        )
        if habit_data["best_habit"]:
            lines.append(f"Strongest habit        {habit_data['best_habit']}")

    # Energy arc
    if overall_avg > 0:
        arc_str = f"{start_avg} → {end_avg}" if start_avg != end_avg else f"{overall_avg} (steady)"
        lines.append(f"Energy arc             {arc_str}   ({direction})")

    # Commitments
    if commitment_data["total"] > 0:
        lines.append(
            f"Commitments made       {commitment_data['total']}   "
            f"kept {commitment_data['kept']}   "
            f"({commitment_data['kept_rate_pct']}% follow-through)"
        )

    lines.append("─" * 40)
    return "\n".join(lines)


def _build_insight_section(
    profile: UserProfile,
    checkins: list,
    habit_data: dict,
    commitment_data: dict,
    energy: tuple,
    first_read: Optional[object],
) -> str:
    name = profile.full_name.split()[0] if profile.full_name else "friend"
    start_avg, end_avg, overall_avg, direction = energy

    lines = ["WHAT YOUR COACH LEARNED"]

    # Pull the most interesting observation we can make
    observations = []

    # From energy direction
    if direction == "rising":
        observations.append(
            f"Your energy improved across the week. That is unusual in a first seven days — "
            f"most people experience friction and fatigue as they establish new habits. "
            f"The fact that yours went the other way suggests you are adding structure, not subtracting it."
    )
    elif direction == "declining":
        observations.append(
            f"Your energy declined as the week progressed. Before you read that as failure — "
            f"don't. The people who track declining energy honestly are the ones who actually change it. "
            f"You named the truth. That is where the work begins."
        )

    # From habit consistency
    if habit_data["completion_rate"] >= 70:
        observations.append(
            f"Your habit completion rate — {habit_data['completion_rate']}% — is in the top tier "
            f"for first-week users. Most people need two to three weeks to achieve this consistency. "
            f"You arrived here on week one."
        )
    elif habit_data["completion_rate"] > 0 and habit_data["completion_rate"] < 40:
        observations.append(
            f"Your habit completion this week was {habit_data['completion_rate']}%. "
            f"Your coach is not concerned. Week one is reconnaissance — you are learning "
            f"which habits actually fit your life and which ones were aspirational. "
            f"That learning is not failure. It is data."
        )

    # From commitment data
    if commitment_data["total"] >= 3 and commitment_data["kept_rate_pct"] >= 80:
        observations.append(
            f"You made {commitment_data['total']} commitments to your coach and kept "
            f"{commitment_data['kept_rate_pct']}% of them. High follow-through in week one "
            f"is the single strongest predictor of 90-day outcomes we have observed."
        )

    # From first read blind spot
    if first_read and first_read.blind_spot:
        blind = first_read.blind_spot[:200].rstrip()
        observations.append(
            f"When I wrote your First Read, I flagged something: {blind}. "
            f"Seven days of data gives that observation more weight, not less."
        )

    # Fallback
    if not observations:
        challenge = profile.biggest_challenge or "the challenge you named at the start"
        observations.append(
            f"Seven days is a short window, but it is enough to see the shape of a person. "
            f"The fact that you are still here — still checking in, still tracking — "
            f"tells your coach something about how you approach {challenge}. "
            f"You do not abandon things quickly. That is worth knowing."
        )

    lines.extend(observations[:2])  # Best two observations
    return "\n\n".join(lines)


def _build_gap_section(profile: UserProfile, checkin_count: int, trial_days: int) -> str:
    name = profile.full_name.split()[0] if profile.full_name else "friend"
    goals = profile.goals_90_days or []
    challenge = profile.biggest_challenge or "the challenge you came here with"

    lines = ["WHAT REMAINS"]

    if goals:
        goal_list = goals[:2]
        goals_str = " and ".join(f'"{g}"' for g in goal_list)
        lines.append(
            f"You told your coach your goals: {goals_str}. "
            f"In seven days, you have not achieved them. That is not a flaw in the plan — "
            f"that is the plan. Ninety days is the unit. Seven is the warmup."
        )
    else:
        lines.append(
            f"The work you came here for — {challenge} — is not resolved in seven days. "
            f"It was never going to be. Seven days is enough to see the shape of the problem. "
            f"The next 90 are where it actually changes."
        )

    lines.append(
        f"\nHere is what the next 30 days can do that these seven could not:\n"
        f"Pattern recognition deepens. Your coach will begin to see which days drain you "
        f"before you feel it yourself. Which commitments you avoid. "
        f"Where your language shifts when something is costing you energy. "
        f"Seven days is a photograph. Thirty days is a film."
    )

    return "\n".join(lines)


def _build_offer_section(profile: UserProfile, energy: tuple, habit_data: dict) -> str:
    name = profile.full_name.split()[0] if profile.full_name else "friend"
    start_avg, end_avg, overall_avg, direction = energy
    role = profile.role or "leader"

    lines = ["THE NEXT CHAPTER"]

    lines.append(
        f"If you continue, here is what your coach will do in month two:"
    )

    specific_offers = []

    if direction in ("declining", "unknown"):
        specific_offers.append(
            "Map the specific triggers that drain your energy and build a recovery protocol "
            "designed for your pattern — not a generic one."
        )
    else:
        specific_offers.append(
            "Build on the energy momentum you established in week one "
            "and identify the specific conditions that sustain it."
        )

    if habit_data["total_habits"] > 0:
        specific_offers.append(
            f"Refine your habit stack — drop what does not fit, deepen what does, "
            f"and add the one or two habits that your data says would have the highest impact."
        )

    challenge = profile.biggest_challenge
    if challenge:
        shortened = challenge[:120].rstrip()
        specific_offers.append(
            f"Hold you accountable to {shortened} — "
            f"not as a concept, but as a specific, measurable shift."
        )

    for offer in specific_offers[:3]:
        lines.append(f"  — {offer}")

    lines.append(
        f"\n{name}, the seven days are done. The question is a simple one: "
        f"is this worth continuing?"
    )
    lines.append(
        "Your coach's answer: the first seven days reveal the person. "
        "The next ninety change them."
    )

    return "\n".join(lines)


# ── Main generator ────────────────────────────────────────────────────────────

def generate_trial_closing_report(
    db: Session,
    user_id: str,
    trial_days: int = 7,
    force_regenerate: bool = False,
) -> dict:
    """
    Generate (or retrieve cached) 7-day trial closing report.

    Returns a dict with:
        full_text, opening, data_section, insight_section,
        gap_section, offer_section, stats, cached
    """
    # Check cache
    if not force_regenerate:
        existing = (
            db.query(TrialClosingReport).filter_by(user_id=user_id).first()
        )
        if existing:
            return {
                "full_text": existing.full_text,
                "trial_day_count": existing.trial_day_count,
                "check_in_count": existing.check_in_count,
                "habit_count": existing.habit_count,
                "open_commitment_count": existing.open_commitment_count,
                "avg_energy": existing.avg_energy,
                "cached": True,
            }

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return {"error": "User profile not found"}

    # Date range
    end_date = date.today()
    start_date = end_date - timedelta(days=trial_days - 1)

    # Gather data
    checkins = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date >= start_date,
            DailyCheckIn.checkin_date <= end_date,
        )
        .all()
    )

    habit_data = _habit_summary(db, user_id, start_date, end_date)
    commitment_data = _commitment_summary(db, user_id, start_date, end_date)
    energy = _energy_arc(checkins)
    first_read = db.query(FirstRead).filter_by(user_id=user_id).first()

    # Build sections
    opening = _build_opening(profile, len(checkins), habit_data, energy, trial_days)
    data_section = _build_data_section(
        len(checkins), habit_data, commitment_data, energy, trial_days
    )
    insight_section = _build_insight_section(
        profile, checkins, habit_data, commitment_data, energy, first_read
    )
    gap_section = _build_gap_section(profile, len(checkins), trial_days)
    offer_section = _build_offer_section(profile, energy, habit_data)

    # Assemble full text
    divider = "\n\n" + "═" * 50 + "\n\n"
    full_text = divider.join([
        opening,
        data_section,
        insight_section,
        gap_section,
        offer_section,
    ])

    # Persist
    _, _, overall_avg, _ = energy
    record = TrialClosingReport(
        user_id=user_id,
        generated_at=datetime.utcnow(),
        trial_day_count=trial_days,
        full_text=full_text,
        check_in_count=len(checkins),
        habit_count=habit_data["total_habits"],
        open_commitment_count=commitment_data["open"],
        avg_energy=overall_avg if overall_avg > 0 else None,
    )

    # Remove old report if regenerating
    old = db.query(TrialClosingReport).filter_by(user_id=user_id).first()
    if old:
        db.delete(old)
        db.flush()

    db.add(record)
    db.commit()

    return {
        "full_text": full_text,
        "sections": {
            "opening": opening,
            "data": data_section,
            "insight": insight_section,
            "gap": gap_section,
            "offer": offer_section,
        },
        "stats": {
            "trial_days": trial_days,
            "check_in_count": len(checkins),
            "habit_count": habit_data["total_habits"],
            "habit_completion_rate": habit_data["completion_rate"],
            "best_habit": habit_data["best_habit"],
            "commitments_made": commitment_data["total"],
            "commitments_kept_rate": commitment_data["kept_rate_pct"],
            "avg_energy": overall_avg,
            "energy_direction": energy[3],
        },
        "cached": False,
    }
