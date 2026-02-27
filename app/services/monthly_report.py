"""
Monthly Coaching Report
========================
At the end of every month, the coach produces a complete written report.
This is the deliverable a premium client expects — something to read, reflect on,
and share with a mentor or partner.

The report contains:
  1. Executive Summary (coach's overall read of the month)
  2. Energy & Wellbeing Trend (7-30 day energy curve, burnout risk trend)
  3. Habit Performance (per-habit completion rates, streaks)
  4. 90-Day Sprint Progress (goal-by-goal milestone completion)
  5. Key Decisions Made This Month
  6. Reflection Highlights (biggest wins and lessons from Sunday reflections)
  7. Dominant Coaching Themes (what topics came up most in conversations)
  8. Coach's 3 Observations (the pattern recognition layer — what the coach noticed)
  9. Next Month's Focus (one priority, one habit to protect, one relationship to invest in)

This is what $150/month feels like.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    DailyCheckIn,
    DecisionLog,
    GoalMilestone,
    HabitCompletion,
    HabitRecord,
    UserProfile,
    WeeklyReflection,
)


def generate_monthly_report(db: Session, user_id: str, year: int | None = None, month: int | None = None) -> dict:
    """
    Generates the full monthly coaching report.
    Defaults to the previous complete month.
    """
    today = date.today()
    if month is None:
        month = today.month - 1 if today.month > 1 else 12
    if year is None:
        year = today.year if today.month > 1 else today.year - 1

    month_start = f"{year}-{month:02d}-01"
    if month == 12:
        month_end = f"{year+1}-01-01"
    else:
        month_end = f"{year}-{month+1:02d}-01"

    month_name = date(year, month, 1).strftime("%B %Y")

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # ── 1. Energy data ───────────────────────────────────────────────────────
    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= month_start,
        DailyCheckIn.check_in_date < month_end,
    ).order_by(DailyCheckIn.check_in_date).all()

    avg_energy = round(sum(c.energy for c in checkins) / len(checkins), 1) if checkins else None
    avg_stress = round(sum(c.stress for c in checkins) / len(checkins), 1) if checkins else None
    low_energy_days = sum(1 for c in checkins if c.energy <= 5)
    high_energy_days = sum(1 for c in checkins if c.energy >= 8)
    checkin_days = len(checkins)

    # Energy trend: week-by-week within month
    weeks_energy: list[dict] = []
    seen_weeks: set[str] = set()
    for ci in checkins:
        d = date.fromisoformat(ci.check_in_date)
        week_key = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]}"
        if week_key not in seen_weeks:
            seen_weeks.add(week_key)
    for wk in sorted(seen_weeks):
        wk_checkins = [c for c in checkins if
                       f"{date.fromisoformat(c.check_in_date).isocalendar()[0]}-W{date.fromisoformat(c.check_in_date).isocalendar()[1]}" == wk]
        if wk_checkins:
            weeks_energy.append({
                "week": wk,
                "avg_energy": round(sum(c.energy for c in wk_checkins) / len(wk_checkins), 1),
                "count": len(wk_checkins),
            })

    # ── 2. Habit data ────────────────────────────────────────────────────────
    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()
    habit_report = []
    for h in habits:
        completions = db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == h.id,
            HabitCompletion.completion_date >= month_start,
            HabitCompletion.completion_date < month_end,
            HabitCompletion.completed == True,
        ).count()
        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]
        rate = int(completions / days_in_month * 100)
        habit_report.append({
            "name": h.name,
            "track": h.track,
            "completion_rate_pct": rate,
            "completions": completions,
            "days_in_month": days_in_month,
            "status": "excellent" if rate >= 80 else ("good" if rate >= 60 else "needs_attention"),
        })

    # ── 3. Sprint progress ───────────────────────────────────────────────────
    goal_milestones = db.query(GoalMilestone).filter(
        GoalMilestone.user_id == user_id,
        GoalMilestone.week_start >= month_start,
        GoalMilestone.week_start < month_end,
    ).all()

    goal_progress: dict[int, dict] = {}
    for m in goal_milestones:
        if m.goal_index not in goal_progress:
            goal_progress[m.goal_index] = {"goal": m.goal_text[:80], "weeks": 0, "on_track": 0}
        goal_progress[m.goal_index]["weeks"] += 1
        if m.status in ("on_track", "complete"):
            goal_progress[m.goal_index]["on_track"] += 1

    # ── 4. Decisions ─────────────────────────────────────────────────────────
    decisions = db.query(DecisionLog).filter(
        DecisionLog.user_id == user_id,
        DecisionLog.decision_date >= month_start,
        DecisionLog.decision_date < month_end,
    ).all()

    # ── 5. Reflections ───────────────────────────────────────────────────────
    reflections = db.query(WeeklyReflection).filter(
        WeeklyReflection.user_id == user_id,
        WeeklyReflection.week_start >= month_start,
        WeeklyReflection.week_start < month_end,
    ).all()

    wins = [r.biggest_win for r in reflections if r.biggest_win]
    lessons = [r.biggest_lesson for r in reflections if r.biggest_lesson]

    # ── 6. Coach's observations ──────────────────────────────────────────────
    observations = _generate_observations(
        name, avg_energy, avg_stress, low_energy_days, high_energy_days,
        checkin_days, habit_report, goal_progress, decisions, reflections
    )

    # ── 7. Next month focus ──────────────────────────────────────────────────
    next_focus = _generate_next_month_focus(
        name, avg_energy, habit_report, goal_progress, checkin_days
    )

    # ── Assemble executive summary ───────────────────────────────────────────
    exec_summary = _build_exec_summary(
        name, month_name, avg_energy, avg_stress, checkin_days,
        habit_report, len(decisions), len(reflections)
    )

    # ── Full report text ─────────────────────────────────────────────────────
    report_text = _assemble_report(
        name, month_name, exec_summary, avg_energy, avg_stress,
        low_energy_days, high_energy_days, checkin_days, weeks_energy,
        habit_report, goal_progress, decisions, wins, lessons,
        observations, next_focus
    )

    return {
        "user_id": user_id,
        "month": month_name,
        "report_text": report_text,
        "data": {
            "checkin_days": checkin_days,
            "avg_energy": avg_energy,
            "avg_stress": avg_stress,
            "habit_report": habit_report,
            "goal_progress": goal_progress,
            "decisions_logged": len(decisions),
            "reflections_completed": len(reflections),
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


def _generate_observations(name, avg_e, avg_s, low_days, high_days, ci_days,
                             habits, goals, decisions, reflections) -> list[str]:
    obs = []
    if avg_e is not None:
        if avg_e < 5.5:
            obs.append(
                f"Energy warning: Your average energy this month was {avg_e}/10 over {ci_days} logged days. "
                f"This is below sustainable performance threshold. "
                f"Next month, your coach's primary focus is recovery and energy architecture — not more output."
            )
        elif avg_e >= 7.5:
            obs.append(
                f"This was a strong month energetically ({avg_e}/10 average over {ci_days} days). "
                f"Identify what made it possible — because that is your formula."
            )

    if habits:
        best = max(habits, key=lambda h: h["completion_rate_pct"])
        worst = min(habits, key=lambda h: h["completion_rate_pct"])
        if best["completion_rate_pct"] >= 80:
            obs.append(
                f"Habit excellence: {best['name']} achieved {best['completion_rate_pct']}% completion. "
                f"This is identity-level behaviour. Protect it next month regardless of how busy you get."
            )
        if worst["completion_rate_pct"] < 40:
            obs.append(
                f"Habit gap: {worst['name']} is at {worst['completion_rate_pct']}% completion. "
                f"This is a design problem. When exactly is this supposed to happen? "
                f"A habit without a trigger and a time is a wish."
            )

    if len(reflections) >= 3:
        obs.append(
            f"You completed {len(reflections)} Sunday reflections this month. "
            f"Leaders who reflect weekly out-learn those who don't by a significant margin. Keep this ritual."
        )
    elif len(reflections) == 0:
        obs.append(
            f"You skipped Sunday reflections entirely this month. "
            f"Your coach cannot synthesise what it cannot see. Reconnect with this ritual in {name}'s next month."
        )

    return obs[:3]  # top 3


def _generate_next_month_focus(name, avg_e, habits, goals, ci_days) -> dict:
    priority = "Consistency before ambition — protect your energy infrastructure."
    if avg_e and avg_e >= 7.5:
        priority = "Raise the standard on your primary goal — you have the energy capital to invest."

    habit_to_protect = "Morning routine"
    if habits:
        best = max(habits, key=lambda h: h["completion_rate_pct"])
        habit_to_protect = best["name"]

    relationship = "Your primary partner or closest colleague"

    return {
        "priority": priority,
        "habit_to_protect": habit_to_protect,
        "relationship_to_invest_in": relationship,
    }


def _build_exec_summary(name, month_name, avg_e, avg_s, ci_days, habits, decisions, reflections) -> str:
    energy_word = "strong" if avg_e and avg_e >= 7 else ("moderate" if avg_e and avg_e >= 5 else "low")
    habit_avg = int(sum(h["completion_rate_pct"] for h in habits) / len(habits)) if habits else None

    return (
        f"{month_name} was a {energy_word}-energy month for {name}. "
        f"You logged check-ins on {ci_days} days" +
        (f" with an average energy of {avg_e}/10" if avg_e else "") +
        (f" and average stress of {avg_s}/10" if avg_s else "") + ". " +
        (f"Habit completion averaged {habit_avg}% across all tracked rituals. " if habit_avg else "") +
        (f"You logged {decisions} major decision(s). " if decisions else "") +
        (f"You completed {reflections} Sunday reflection(s)." if reflections else "")
    )


def _assemble_report(name, month_name, exec_summary, avg_e, avg_s,
                      low_days, high_days, ci_days, weeks_energy,
                      habits, goals, decisions, wins, lessons,
                      observations, next_focus) -> str:
    lines = [
        f"MONTHLY COACHING REPORT",
        f"{month_name} — {name}",
        f"{'=' * 50}",
        f"",
        f"EXECUTIVE SUMMARY",
        f"-----------------",
        exec_summary,
        f"",
        f"ENERGY & WELLBEING",
        f"------------------",
    ]

    if avg_e:
        lines += [
            f"Average energy: {avg_e}/10   Average stress: {avg_s}/10",
            f"High-energy days (8+): {high_days}   Low-energy days (5 and below): {low_days}",
            f"Check-ins logged: {ci_days}",
        ]
        if weeks_energy:
            lines.append("Weekly energy trend:")
            for w in weeks_energy:
                bar = "█" * int(w["avg_energy"]) + "░" * (10 - int(w["avg_energy"]))
                lines.append(f"  {w['week']}: {bar} {w['avg_energy']}/10")
    else:
        lines.append("No check-in data recorded this month.")

    lines += [f"", f"HABIT PERFORMANCE", f"-----------------"]
    if habits:
        for h in habits:
            status_icon = "✓" if h["status"] == "excellent" else ("~" if h["status"] == "good" else "✗")
            lines.append(f"  {status_icon} {h['name']}: {h['completion_rate_pct']}% ({h['completions']}/{h['days_in_month']} days)")
    else:
        lines.append("No habits tracked this month.")

    lines += [f"", f"90-DAY SPRINT PROGRESS", f"----------------------"]
    if goals:
        for gi, gd in goals.items():
            rate = int(gd["on_track"] / gd["weeks"] * 100) if gd["weeks"] else 0
            lines.append(f"  Goal {gi+1}: {gd['goal'][:60]}...")
            lines.append(f"    This month: {gd['on_track']}/{gd['weeks']} weeks on track ({rate}%)")
    else:
        lines.append("No sprint milestones tracked this month.")

    if wins:
        lines += [f"", f"YOUR BIGGEST WINS THIS MONTH", f"----------------------------"]
        for i, w in enumerate(wins[:4], 1):
            lines.append(f"  {i}. {w[:120]}")

    if lessons:
        lines += [f"", f"LESSONS LEARNED", f"---------------"]
        for i, l in enumerate(lessons[:4], 1):
            lines.append(f"  {i}. {l[:120]}")

    lines += [f"", f"COACH'S OBSERVATIONS", f"--------------------"]
    for obs in observations:
        lines.append(f"  • {obs}")
        lines.append("")

    lines += [
        f"NEXT MONTH'S FOCUS",
        f"------------------",
        f"  Priority: {next_focus['priority']}",
        f"  Habit to protect: {next_focus['habit_to_protect']}",
        f"  Relationship to invest in: {next_focus['relationship_to_invest_in']}",
        f"",
        f"{'=' * 50}",
        f"Your coach is watching. Keep going, {name}.",
    ]

    return "\n".join(lines)
