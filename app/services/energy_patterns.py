"""
Energy Pattern Intelligence
============================
Your data has been building for weeks. Now the coach reads it back to you
in a way that changes how you design your life.

Most people live as if every hour is equal. The research — and your own data —
says it is not. Your peak cognitive window is 2-4 hours wide, and it repeats
at roughly the same time every day. Miss it on a meeting. Schedule a difficult
decision in a low trough. The cost is invisible until it accumulates.

What this service computes:
  1. Peak Performance Window
     - Best day of week (avg energy by weekday)
     - Best time of day (if check-in time is tracked)
     - Worst day of week
     "Your data: Tuesdays and Wednesdays average 8.1/10.
      Friday afternoons: 5.2/10. You currently schedule most
      client calls on Fridays. That is costing you."

  2. Energy Stability Score (0-100)
     - How much does energy vary day to day?
     - Low variance = consistent, sustainable performer
     - High variance = reactive, environment-dependent
     "Your energy swings 3.4 points on average between consecutive days.
      That level of variance suggests external events are driving your state
      more than internal practices are."

  3. Recovery Intelligence
     - How quickly does energy bounce back after low days?
     - Does sleep quality actually predict next-day energy for this user?
     - Is there a correlation with stress and energy lag?

  4. Habit-Energy Correlation
     - Which habits, when completed, correlate with higher next-day energy?
     "When you complete your morning run, your next-day energy is 1.4 points
      higher on average. When you skip it, it drops 0.8 points.
      That single habit is worth 2.2 points of energy to you."

  5. Calendar-Energy Correlation (if calendar enabled)
     - Meeting-heavy days vs. energy (already partially in calendar_coach.py)
     - Deep-work blocks correlation with energy next day

Data requirement: 14+ check-ins for basic patterns, 30+ for full analysis.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import DailyCheckIn, HabitCompletion, HabitRecord, HealthData, UserProfile


_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Core analysis ─────────────────────────────────────────────────────────────

def analyse_energy_patterns(db: Session, user_id: str, days: int = 60) -> dict:
    """
    Full energy pattern analysis.
    Requires at least 14 check-ins. Returns richer analysis with 30+.
    """
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= cutoff,
    ).order_by(DailyCheckIn.check_in_date).all()

    if len(checkins) < 7:
        return {
            "available": False,
            "check_in_count": len(checkins),
            "minimum_required": 14,
            "message": (
                f"Your coach needs at least 14 check-ins to identify your energy patterns. "
                f"You have {len(checkins)} so far. "
                f"Keep showing up — the data is accumulating."
            ),
        }

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # 1. Day-of-week analysis
    dow_analysis = _day_of_week_analysis(checkins)

    # 2. Energy stability
    stability = _energy_stability_analysis(checkins)

    # 3. Recovery intelligence
    recovery = _recovery_analysis(checkins)

    # 4. Habit-energy correlation
    habit_correlation = _habit_energy_correlation(db, user_id, checkins)

    # 5. Sleep-energy correlation (from HealthKit if available)
    sleep_correlation = _sleep_energy_correlation(db, user_id, checkins)

    # 6. Trend (is energy trending up or down?)
    trend = _energy_trend(checkins)

    # Composite coach insight
    coach_insight = _generate_coach_insight(
        name, dow_analysis, stability, recovery, habit_correlation, sleep_correlation, trend
    )

    return {
        "available": True,
        "check_in_count": len(checkins),
        "days_analysed": days,
        "coach_insight": coach_insight,
        "day_of_week": dow_analysis,
        "stability": stability,
        "recovery": recovery,
        "habit_correlations": habit_correlation,
        "sleep_energy_correlation": sleep_correlation,
        "trend": trend,
    }


# ── Day-of-week analysis ──────────────────────────────────────────────────────

def _day_of_week_analysis(checkins: list[DailyCheckIn]) -> dict:
    by_dow: dict[int, list[float]] = defaultdict(list)
    for c in checkins:
        try:
            d = datetime.strptime(c.check_in_date, "%Y-%m-%d")
            by_dow[d.weekday()].append(c.energy)
        except ValueError:
            pass

    dow_avgs: dict[str, float] = {}
    for dow_int, energies in by_dow.items():
        if energies:
            dow_avgs[_DAY_NAMES[dow_int]] = round(sum(energies) / len(energies), 2)

    if not dow_avgs:
        return {"available": False}

    peak_day = max(dow_avgs, key=dow_avgs.get)
    trough_day = min(dow_avgs, key=dow_avgs.get)
    peak_val = dow_avgs[peak_day]
    trough_val = dow_avgs[trough_day]

    return {
        "available": True,
        "by_day": dow_avgs,
        "peak_day": peak_day,
        "peak_avg_energy": peak_val,
        "trough_day": trough_day,
        "trough_avg_energy": trough_val,
        "gap": round(peak_val - trough_val, 2),
        "coach_note": (
            f"Your highest-energy day: {peak_day} ({peak_val}/10). "
            f"Your lowest: {trough_day} ({trough_val}/10). "
            f"A {round(peak_val - trough_val, 1)}-point gap between your best and worst days. "
            + (
                f"Schedule your most important work — difficult conversations, strategic decisions, "
                f"creative output — on {peak_day}s. "
                f"Use {trough_day}s for administrative tasks, email, and low-stakes meetings."
                if peak_val - trough_val >= 1.0
                else f"Your energy is remarkably consistent across the week. "
                     f"This is a sign of strong self-regulation."
            )
        ),
    }


# ── Energy stability ──────────────────────────────────────────────────────────

def _energy_stability_analysis(checkins: list[DailyCheckIn]) -> dict:
    energies = [c.energy for c in checkins]
    if len(energies) < 5:
        return {"available": False}

    # Day-to-day variance
    consecutive_diffs = [
        abs(energies[i + 1] - energies[i]) for i in range(len(energies) - 1)
    ]
    avg_swing = round(sum(consecutive_diffs) / len(consecutive_diffs), 2)
    avg_energy = round(sum(energies) / len(energies), 2)

    # Stability score: 0 (wildly variable) to 100 (perfectly stable)
    # avg_swing of 0 = 100, avg_swing of 5+ = 0
    stability_score = max(0, round(100 - (avg_swing / 5.0) * 100))

    if avg_swing <= 1.0:
        label = "highly stable"
        note = (
            "Your energy is highly stable day to day. "
            "This is the signature of someone with strong internal anchors — "
            "sleep, rituals, exercise. "
            "Protect whatever you're doing."
        )
    elif avg_swing <= 2.0:
        label = "moderately stable"
        note = (
            f"Your energy swings an average of {avg_swing} points between consecutive days — "
            f"moderate variability. "
            f"The coach's question: what determines the difference between your high and low days? "
            f"If you can name it, you can manage it."
        )
    else:
        label = "reactive"
        note = (
            f"Your energy swings {avg_swing} points on average between consecutive days. "
            f"That level of variability tells your coach that external events — "
            f"meetings, news, other people's moods — are driving your internal state "
            f"more than your own practices are. "
            f"The goal of coaching is to invert that ratio."
        )

    return {
        "available": True,
        "avg_energy": avg_energy,
        "avg_daily_swing": avg_swing,
        "stability_score": stability_score,
        "stability_label": label,
        "coach_note": note,
    }


# ── Recovery analysis ─────────────────────────────────────────────────────────

def _recovery_analysis(checkins: list[DailyCheckIn]) -> dict:
    """
    How quickly does energy bounce back after a low day (< 5)?
    """
    sorted_ci = sorted(checkins, key=lambda c: c.check_in_date)
    recovery_windows: list[int] = []  # days to recover after a low day

    for i, c in enumerate(sorted_ci):
        if c.energy < 5.0 and i + 1 < len(sorted_ci):
            # Count days until energy >= 7
            for j in range(i + 1, min(i + 8, len(sorted_ci))):
                if sorted_ci[j].energy >= 7.0:
                    recovery_windows.append(j - i)
                    break

    if not recovery_windows:
        return {
            "available": False,
            "note": "Insufficient low-energy days to measure recovery patterns.",
        }

    avg_recovery = round(sum(recovery_windows) / len(recovery_windows), 1)

    if avg_recovery <= 1:
        note = (
            f"Your recovery speed is exceptional. After low-energy days, "
            f"you bounce back in {avg_recovery} day on average. "
            f"This is high resilience — a genuine competitive advantage."
        )
    elif avg_recovery <= 2:
        note = (
            f"You recover from low-energy periods in about {avg_recovery} days on average. "
            f"That is healthy. "
            f"The question is whether there are specific practices "
            f"that accelerate your recovery on day 1."
        )
    else:
        note = (
            f"After low-energy periods, you take an average of {avg_recovery} days to return to 7+. "
            f"Your coach recommends building a personal 'recovery protocol' — "
            f"a specific set of actions for the morning after a hard day. "
            f"Without it, recovery is left to chance."
        )

    return {
        "available": True,
        "low_energy_events": len(recovery_windows),
        "avg_recovery_days": avg_recovery,
        "coach_note": note,
    }


# ── Habit-energy correlation ──────────────────────────────────────────────────

def _habit_energy_correlation(
    db: Session, user_id: str, checkins: list[DailyCheckIn]
) -> list[dict]:
    """
    For each active habit, compute the average next-day energy when:
      (a) the habit was completed yesterday
      (b) the habit was not completed yesterday
    Returns correlation insights sorted by impact magnitude.
    """
    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()
    if not habits:
        return []

    # Build date → energy map
    energy_map = {c.check_in_date: c.energy for c in checkins}
    dates_sorted = sorted(energy_map.keys())

    results = []
    for habit in habits:
        completions = db.query(HabitCompletion).filter_by(
            habit_id=habit.id, user_id=user_id, completed=True
        ).all()
        completed_dates = {comp.completion_date for comp in completions}

        energy_after_completion: list[float] = []
        energy_after_miss: list[float] = []

        for i, d in enumerate(dates_sorted[:-1]):
            next_d = dates_sorted[i + 1]
            next_energy = energy_map.get(next_d)
            if next_energy is None:
                continue
            if d in completed_dates:
                energy_after_completion.append(next_energy)
            else:
                energy_after_miss.append(next_energy)

        if len(energy_after_completion) < 3 or len(energy_after_miss) < 3:
            continue

        avg_after_done = round(sum(energy_after_completion) / len(energy_after_completion), 2)
        avg_after_miss = round(sum(energy_after_miss) / len(energy_after_miss), 2)
        impact = round(avg_after_done - avg_after_miss, 2)

        results.append({
            "habit_id": habit.id,
            "habit_name": habit.name,
            "avg_energy_after_completion": avg_after_done,
            "avg_energy_after_miss": avg_after_miss,
            "energy_impact": impact,
            "sample_size_completed": len(energy_after_completion),
            "sample_size_missed": len(energy_after_miss),
            "coach_note": (
                f"When you complete '{habit.name}', your next-day energy averages {avg_after_done}/10. "
                f"When you skip it: {avg_after_miss}/10. "
                f"That's a {abs(impact):.1f}-point {'boost' if impact > 0 else 'drag'}. "
                + (
                    f"This single habit is worth {impact:.1f} energy points to you — "
                    f"every single day you do it."
                    if abs(impact) >= 0.5 else
                    f"Modest but consistent effect."
                )
            ) if abs(impact) >= 0.3 else None,
        })

    # Sort by absolute impact
    results.sort(key=lambda r: abs(r["energy_impact"]), reverse=True)
    return [r for r in results if r.get("coach_note")]


# ── Sleep-energy correlation ──────────────────────────────────────────────────

def _sleep_energy_correlation(
    db: Session, user_id: str, checkins: list[DailyCheckIn]
) -> dict:
    """
    Correlate HealthKit sleep data with next-day energy scores.
    Only available if HealthKit integration is active.
    """
    health_records = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.sleep_hours.isnot(None),
    ).all()

    if len(health_records) < 5:
        return {"available": False}

    energy_map = {c.check_in_date: c.energy for c in checkins}

    paired: list[tuple[float, float]] = []  # (sleep_hours, next_day_energy)
    for h in health_records:
        energy = energy_map.get(h.data_date)
        if energy is not None:
            paired.append((h.sleep_hours, energy))

    if len(paired) < 5:
        return {"available": False}

    # Simple bin analysis: < 6h, 6-7h, 7-8h, 8h+
    bins: dict[str, list[float]] = {"<6h": [], "6-7h": [], "7-8h": [], "8h+": []}
    for sleep, energy in paired:
        if sleep < 6:
            bins["<6h"].append(energy)
        elif sleep < 7:
            bins["6-7h"].append(energy)
        elif sleep < 8:
            bins["7-8h"].append(energy)
        else:
            bins["8h+"].append(energy)

    bin_avgs = {
        k: round(sum(v) / len(v), 2) for k, v in bins.items() if len(v) >= 2
    }

    if not bin_avgs:
        return {"available": False}

    best_bin = max(bin_avgs, key=bin_avgs.get)
    worst_bin = min(bin_avgs, key=bin_avgs.get)

    coach_note = (
        f"Your data shows your best energy follows {best_bin} of sleep ({bin_avgs[best_bin]}/10). "
        f"After {worst_bin}: {bin_avgs[worst_bin]}/10. "
        f"That gap is {round(bin_avgs[best_bin] - bin_avgs[worst_bin], 1)} points — "
        f"significant enough that sleep is probably your highest-leverage energy lever."
        if bin_avgs[best_bin] - bin_avgs[worst_bin] >= 0.8
        else f"Interestingly, sleep duration has a modest effect on your energy. "
             f"Your coach will look for other factors that matter more for you specifically."
    )

    return {
        "available": True,
        "sample_pairs": len(paired),
        "energy_by_sleep_duration": bin_avgs,
        "optimal_sleep_window": best_bin,
        "coach_note": coach_note,
    }


# ── Trend ─────────────────────────────────────────────────────────────────────

def _energy_trend(checkins: list[DailyCheckIn]) -> dict:
    """
    Is energy trending up, flat, or down over the period?
    Uses simple linear regression over the last 30 check-ins.
    """
    recent = sorted(checkins, key=lambda c: c.check_in_date)[-30:]
    if len(recent) < 7:
        return {"available": False}

    n = len(recent)
    xs = list(range(n))
    ys = [c.energy for c in recent]

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0.0

    # slope is per check-in day; scale to per 30 days
    total_change = round(slope * 30, 2)

    if total_change >= 1.0:
        direction = "rising"
        note = (
            f"Your energy has trended upward by approximately {total_change} points "
            f"over the past 30 check-ins. "
            f"Something is working. Your coach's job now is to help you identify what, "
            f"so you can protect and amplify it."
        )
    elif total_change <= -1.0:
        direction = "declining"
        note = (
            f"Your energy has trended downward by approximately {abs(total_change)} points "
            f"over the past 30 check-ins. "
            f"Your coach is paying attention to this. "
            f"A sustained decline is not a discipline problem — "
            f"it is a signal that something structural needs to change. "
            f"Let's find it."
        )
    else:
        direction = "stable"
        note = (
            f"Your energy has been relatively stable over the past 30 check-ins. "
            f"Stability is valuable — it means you are maintaining. "
            f"The question is: are you growing, or just sustaining?"
        )

    return {
        "available": True,
        "direction": direction,
        "estimated_30_day_change": total_change,
        "current_avg": round(y_mean, 2),
        "coach_note": note,
    }


# ── Coach composite insight ───────────────────────────────────────────────────

def _generate_coach_insight(
    name: str,
    dow: dict,
    stability: dict,
    recovery: dict,
    habits: list[dict],
    sleep: dict,
    trend: dict,
) -> str:
    """
    Generate the top-level coach synthesis — the 3-4 lines the user reads first.
    Picks the highest-signal observations across all analyses.
    """
    insights = []

    # Most important insight first: trend
    if trend.get("available"):
        if trend["direction"] == "declining":
            insights.append(
                f"{name}, the headline is this: your energy has been declining. "
                f"The data is clear and your coach is not going to bury it in the fine print. "
                f"Something needs to change — likely more than one thing."
            )
        elif trend["direction"] == "rising":
            insights.append(
                f"{name}, your energy has been climbing. "
                f"Whatever you've been doing over the past month is working. "
                f"Here's what the data says about what's driving it."
            )

    # Peak day
    if dow.get("available") and dow.get("gap", 0) >= 1.5:
        insights.append(
            f"Your peak day is {dow['peak_day']} ({dow['peak_avg_energy']}/10). "
            f"Your trough: {dow['trough_day']} ({dow['trough_avg_energy']}/10). "
            f"A {dow['gap']}-point gap. "
            f"Most leaders waste their peak days on meetings and their creative work "
            f"suffers for it. Protect {dow['peak_day']}."
        )

    # Top habit correlation
    if habits:
        top_habit = habits[0]
        if abs(top_habit["energy_impact"]) >= 0.5:
            insights.append(top_habit["coach_note"])

    # Sleep
    if sleep.get("available") and sleep.get("coach_note"):
        insights.append(sleep["coach_note"])

    # Stability
    if stability.get("available") and stability.get("avg_daily_swing", 0) >= 2.0:
        insights.append(stability["coach_note"])

    if not insights:
        return (
            f"{name}, your energy data is accumulating. "
            f"Patterns are beginning to emerge — check back as more check-ins come in."
        )

    return "\n\n".join(insights)


# ── Peak performance window (quick summary) ───────────────────────────────────

def get_peak_performance_window(db: Session, user_id: str) -> dict:
    """
    Quick summary: just the peak/trough day and top habit insight.
    Included in morning brief as a single-line reminder.
    """
    result = analyse_energy_patterns(db, user_id, days=60)
    if not result.get("available"):
        return {"available": False}

    dow = result.get("day_of_week", {})
    habits = result.get("habit_correlations", [])
    trend = result.get("trend", {})

    peak_day = dow.get("peak_day", "")
    peak_energy = dow.get("peak_avg_energy")
    trough_day = dow.get("trough_day", "")
    top_habit = habits[0]["habit_name"] if habits else None

    return {
        "available": True,
        "peak_day": peak_day,
        "peak_avg_energy": peak_energy,
        "trough_day": trough_day,
        "top_energy_habit": top_habit,
        "trend_direction": trend.get("direction", "stable"),
        "one_line_summary": (
            f"Peak: {peak_day} ({peak_energy}/10)"
            + (f" | Top habit: {top_habit}" if top_habit else "")
            + (f" | Trend: {trend.get('direction', 'stable')}" if trend.get("available") else "")
        ),
    }
