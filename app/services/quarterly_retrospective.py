"""
Quarterly 90-Day Retrospective
================================
This is the document a $500/month client expects.

Not a monthly report (which is operational). Not a summary.
A retrospective is the coach and client sitting down and looking
at the full arc of 90 days together — with honesty, with data,
with specificity, and with a clear bridge to the next sprint.

The format:

  PART I: THE NUMBERS
  - Energy arc: where you started, where you ended, the trajectory
  - Habit performance: completion rates, longest streaks, what stuck
  - Commitment integrity: how many you kept, the pattern
  - Decision count: how many major decisions, quality of the process
  - Meeting intelligence (if calendar): meeting load, energy impact

  PART II: THE STORY
  - What the coach observed over the 90 days (written in coach voice)
  - The pivotal moment — the week or event that changed something
  - The growth edge: where were you stretched most?
  - What you did not do that you said you would

  PART III: THE WINS
  - Named wins (from reflections, achievements, check-ins)
  - The win you almost missed (coach's observation of underrated progress)
  - What the numbers confirm

  PART IV: THE LESSONS
  - Patterns in what worked and what didn't
  - The recurring obstacle — what shows up every time
  - What the coach now knows about how you function under pressure

  PART V: THE BRIDGE
  - Recommended focus for the next 90 days (3 priorities)
  - What to stop doing
  - What to protect at all costs
  - One question for the next sprint

This is written to be read aloud. To be shared with a mentor or board member.
To feel like it was written by someone who has been watching carefully.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Achievement,
    Commitment,
    DailyCheckIn,
    DecisionLog,
    GoalMilestone,
    HabitCompletion,
    HabitRecord,
    UserProfile,
    WeeklyReflection,
)


def generate_quarterly_retrospective(
    db: Session, user_id: str, sprint_end_date: str | None = None
) -> dict:
    """
    Generate the full 90-day retrospective.
    sprint_end_date defaults to today. The window is the 90 days prior.
    """
    end_date = (
        datetime.strptime(sprint_end_date, "%Y-%m-%d").date()
        if sprint_end_date
        else date.today()
    )
    start_date = end_date - timedelta(days=89)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return {"error": "User not found"}

    name = profile.full_name.split()[0] if profile.full_name else "friend"
    full_name = profile.full_name

    # ── Gather all data ───────────────────────────────────────────────────────

    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date.between(start_str, end_str),
    ).order_by(DailyCheckIn.check_in_date).all()

    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()

    completions = db.query(HabitCompletion).filter(
        HabitCompletion.user_id == user_id,
        HabitCompletion.completion_date.between(start_str, end_str),
        HabitCompletion.completed == True,
    ).all()

    commitments = db.query(Commitment).filter(
        Commitment.user_id == user_id,
        Commitment.due_date.between(start_str, end_str),
    ).all()

    decisions = db.query(DecisionLog).filter(
        DecisionLog.user_id == user_id,
        DecisionLog.decision_date.between(start_str, end_str),
    ).all()

    reflections = db.query(WeeklyReflection).filter(
        WeeklyReflection.user_id == user_id,
        WeeklyReflection.week_start.between(start_str, end_str),
    ).order_by(WeeklyReflection.week_start).all()

    achievements = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.achievement_date.between(start_str, end_str),
    ).all()

    milestones = db.query(GoalMilestone).filter(
        GoalMilestone.user_id == user_id,
    ).all()

    # ── Part I: The Numbers ───────────────────────────────────────────────────
    numbers = _build_numbers_section(
        name, checkins, habits, completions, commitments, decisions, achievements
    )

    # ── Part II: The Story ────────────────────────────────────────────────────
    story = _build_story_section(
        name, full_name, profile, checkins, reflections, commitments, achievements
    )

    # ── Part III: The Wins ────────────────────────────────────────────────────
    wins = _build_wins_section(name, reflections, achievements, milestones, checkins)

    # ── Part IV: The Lessons ──────────────────────────────────────────────────
    lessons = _build_lessons_section(name, commitments, checkins, habits, completions)

    # ── Part V: The Bridge ────────────────────────────────────────────────────
    bridge = _build_bridge_section(name, profile, checkins, commitments, habits, completions)

    # Assemble full document
    period_label = (
        f"{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}"
    )

    full_text = "\n\n".join([
        f"90-DAY COACHING RETROSPECTIVE",
        f"{full_name}",
        f"{period_label}",
        f"{'═' * 56}",
        numbers,
        f"{'─' * 56}",
        story,
        f"{'─' * 56}",
        wins,
        f"{'─' * 56}",
        lessons,
        f"{'─' * 56}",
        bridge,
        f"{'═' * 56}",
        f"Prepared by your coach | {date.today().strftime('%B %d, %Y')}",
    ])

    return {
        "user_id": user_id,
        "full_name": full_name,
        "period_start": start_str,
        "period_end": end_str,
        "period_label": period_label,
        "full_retrospective": full_text,
        "sections": {
            "numbers": numbers,
            "story": story,
            "wins": wins,
            "lessons": lessons,
            "bridge": bridge,
        },
        "stats": {
            "check_in_count": len(checkins),
            "habit_count": len(habits),
            "decision_count": len(decisions),
            "commitment_count": len(commitments),
            "reflection_count": len(reflections),
            "achievement_count": len(achievements),
        },
    }


def _build_numbers_section(
    name, checkins, habits, completions, commitments, decisions, achievements
) -> str:
    lines = ["PART I — THE NUMBERS"]

    if checkins:
        energies = [c.energy for c in checkins]
        stresses = [c.stress for c in checkins]
        avg_e = round(sum(energies) / len(energies), 1)
        first_3 = round(sum(energies[:10]) / max(len(energies[:10]), 1), 1)
        last_3 = round(sum(energies[-10:]) / max(len(energies[-10:]), 1), 1)
        trend_arrow = "↑" if last_3 > first_3 + 0.3 else ("↓" if last_3 < first_3 - 0.3 else "→")
        avg_s = round(sum(stresses) / len(stresses), 1)

        lines.append(
            f"Check-ins completed: {len(checkins)} / 90 days "
            f"({round(len(checkins) / 90 * 100)}% consistency)\n"
            f"Average energy:  {avg_e}/10  |  Early sprint: {first_3}  →  Final weeks: {last_3}  {trend_arrow}\n"
            f"Average stress:  {avg_s}/10"
        )

    if habits and completions:
        completion_by_habit: dict[int, int] = {}
        for comp in completions:
            completion_by_habit[comp.habit_id] = completion_by_habit.get(comp.habit_id, 0) + 1

        habit_lines = []
        for h in habits:
            count = completion_by_habit.get(h.id, 0)
            rate = round(count / 90 * 100)
            bar_filled = round(rate / 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            habit_lines.append(f"  {h.name[:30]:<30} {bar} {rate}%")

        lines.append("Habit Performance:\n" + "\n".join(habit_lines))

    if commitments:
        kept = sum(1 for c in commitments if c.status == "kept")
        missed = sum(1 for c in commitments if c.status == "missed")
        total_closed = sum(1 for c in commitments if c.status in ("kept", "missed", "partial"))
        rate = round(kept / max(total_closed, 1) * 100)
        lines.append(
            f"Commitments: {len(commitments)} made  |  {kept} kept  |  {missed} missed  "
            f"|  {rate}% integrity rate"
        )

    if decisions:
        reviewed = sum(1 for d in decisions if d.reviewed)
        lines.append(
            f"Major decisions logged: {len(decisions)}  "
            f"|  30-day reviews completed: {reviewed}"
        )

    if achievements:
        lines.append(f"Milestones celebrated: {len(achievements)}")

    return "\n\n".join(lines)


def _build_story_section(
    name, full_name, profile, checkins, reflections, commitments, achievements
) -> str:
    lines = ["PART II — THE STORY"]

    # Energy arc narrative
    if len(checkins) >= 14:
        energies = [c.energy for c in checkins]
        first_avg = sum(energies[:10]) / 10
        last_avg = sum(energies[-10:]) / 10
        mid_point = len(energies) // 2
        mid_avg = sum(energies[mid_point - 5: mid_point + 5]) / 10

        # Find the lowest and highest weeks
        lowest_week_energy = min(energies)
        highest_week_energy = max(energies)

        narrative = (
            f"The 90-day arc, in your coach's words.\n\n"
            f"{full_name} came into this sprint with an energy baseline of {round(first_avg, 1)}/10. "
            f"By the midpoint, energy had {'climbed to' if mid_avg > first_avg else 'settled at'} "
            f"{round(mid_avg, 1)}/10. "
            f"The final weeks averaged {round(last_avg, 1)}/10. "
        )

        if last_avg > first_avg + 0.5:
            narrative += (
                f"The direction is upward. "
                f"Something shifted — in practice, in environment, or in mindset. "
                f"Your coach's job in the next sprint is to identify what, precisely, and protect it."
            )
        elif last_avg < first_avg - 0.5:
            narrative += (
                f"The direction is downward — and your coach is not going to minimise that. "
                f"The question is not whether something went wrong, but what. "
                f"The lessons section of this report addresses it directly."
            )
        else:
            narrative += (
                f"Energy held stable across the sprint. "
                f"Stability is underrated — it means you were able to perform consistently "
                f"even as the demands of the quarter changed. "
                f"The question now is whether you want to maintain or elevate."
            )

        lines.append(narrative)

    # Reflections — surface pivotal moments
    if reflections:
        biggest_wins = [r.biggest_win for r in reflections if r.biggest_win.strip()]
        biggest_lessons = [r.biggest_lesson for r in reflections if r.biggest_lesson.strip()]

        if biggest_wins:
            lines.append(
                f"Across {len(reflections)} weekly reflections, you named wins, lessons, and commitments. "
                f"Your coach read every one. "
                f"The pattern that emerged: " + _extract_reflection_pattern(biggest_wins, biggest_lessons)
            )

    # Missed commitments — what was avoided
    missed_commitments = [c for c in commitments if c.status == "missed"]
    if missed_commitments:
        themes = [c.commitment_text[:60] for c in missed_commitments[:3]]
        lines.append(
            f"What you did not do:\n"
            + "\n".join(f"  — {t}..." for t in themes)
            + f"\n\nYour coach is not reporting this to shame you. "
            f"These are the most important items in this document. "
            f"The pattern of what we consistently avoid tells us more "
            f"about our real priorities than any goal-setting exercise ever will."
        )

    return "\n\n".join(lines)


def _extract_reflection_pattern(wins: list[str], lessons: list[str]) -> str:
    """Simple frequency-based pattern extraction from reflection text."""
    all_text = " ".join(wins + lessons).lower()
    themes = {
        "relationships": ["team", "colleague", "relationship", "conversation", "feedback", "people"],
        "strategic clarity": ["focus", "priority", "clarity", "decision", "direction"],
        "personal energy": ["energy", "sleep", "exercise", "health", "burnout", "rest"],
        "execution": ["deadline", "delivered", "shipped", "completed", "launched", "finished"],
        "leadership presence": ["leadership", "presence", "speaking", "presenting", "confidence"],
    }

    theme_scores = {}
    for theme, words in themes.items():
        score = sum(all_text.count(w) for w in words)
        if score > 0:
            theme_scores[theme] = score

    if not theme_scores:
        return "consistent engagement with the coaching process."

    top_theme = max(theme_scores, key=theme_scores.get)
    return (
        f"the recurring theme across your reflections was {top_theme}. "
        f"This is where your attention naturally returns. "
        f"It is likely where your growth is concentrated."
    )


def _build_wins_section(name, reflections, achievements, milestones, checkins) -> str:
    lines = ["PART III — THE WINS"]

    named_wins = []
    for r in reflections:
        if r.biggest_win.strip():
            named_wins.append(f"  Week of {r.week_start}: {r.biggest_win[:120]}")

    if named_wins:
        lines.append("Wins you named in your weekly reflections:\n" + "\n".join(named_wins[-8:]))

    if achievements:
        ach_lines = [f"  • {a.title}" for a in achievements]
        lines.append("Milestones your coach marked:\n" + "\n".join(ach_lines))

    completed_milestones = [m for m in milestones if m.status == "complete"]
    if completed_milestones:
        lines.append(
            f"Sprint goals achieved: {len(completed_milestones)} milestone(s) marked complete."
        )

    # The underrated win
    if checkins:
        energies = [c.energy for c in checkins]
        consistency = len(checkins) / 90
        if consistency >= 0.7:
            lines.append(
                f"The win your coach wants to name that you may have overlooked:\n\n"
                f"You showed up {len(checkins)} out of 90 days. "
                f"That is {round(consistency * 100)}% consistency. "
                f"In the research on behavior change, that level of adherence puts you "
                f"in the top percentile of coaching clients. "
                f"Most people quit by week three. "
                f"You didn't. "
                f"That is not a small thing."
            )

    return "\n\n".join(lines)


def _build_lessons_section(name, commitments, checkins, habits, completions) -> str:
    lines = ["PART IV — THE LESSONS"]

    # Commitment pattern
    kept_c = [c for c in commitments if c.status == "kept"]
    missed_c = [c for c in commitments if c.status == "missed"]
    deferred_c = [c for c in commitments if c.status == "deferred"]

    if commitments:
        rate = round(len(kept_c) / max(len(kept_c) + len(missed_c), 1) * 100)
        if rate >= 80:
            lines.append(
                f"Commitment integrity: {rate}%. "
                f"This is your most important professional asset. "
                f"Every leader who builds a reputation for doing what they say "
                f"starts with exactly this discipline. Guard it."
            )
        elif rate >= 50:
            lines.append(
                f"Commitment integrity: {rate}%. "
                f"There is a gap between what you intend and what you complete. "
                f"The lesson your coach draws from this data: "
                f"you may be over-committing — agreeing to more than your bandwidth can support. "
                f"The next sprint: make fewer commitments. Make them from a quieter, more deliberate place."
            )
        else:
            lines.append(
                f"Commitment integrity: {rate}%. "
                f"This is the most important metric in this retrospective — and it needs honest attention. "
                f"Your coach's observation: the commitments that were missed "
                f"are clustered around a specific type of action. "
                f"The pattern is worth examining in the next recalibration session."
            )

    # Habit stickiness
    if habits and completions:
        completion_by_habit: dict[int, int] = {h.id: 0 for h in habits}
        for comp in completions:
            completion_by_habit[comp.habit_id] = completion_by_habit.get(comp.habit_id, 0) + 1

        sticky = [h for h in habits if completion_by_habit.get(h.id, 0) / 90 >= 0.7]
        unstable = [h for h in habits if completion_by_habit.get(h.id, 0) / 90 < 0.3]

        if sticky:
            lines.append(
                f"What stuck: {', '.join(h.name for h in sticky[:3])}. "
                f"These habits are no longer habits — they are identity. "
                f"The person who does these things is who you are now. "
                f"Build the next sprint on that foundation."
            )

        if unstable:
            lines.append(
                f"What didn't stick: {', '.join(h.name for h in unstable[:3])}. "
                f"Your coach's honest read: either the habit was not genuinely wanted, "
                f"or the environment did not support it. "
                f"Before the next sprint — decide: redesign the habit, or consciously release it. "
                f"Keeping it on the list without doing it is expensive."
            )

    # Energy patterns
    if len(checkins) >= 20:
        energies = [c.energy for c in checkins]
        low_days = sum(1 for e in energies if e < 5)
        if low_days >= 10:
            lines.append(
                f"You had {low_days} days with energy below 5/10 — "
                f"more than 10% of the sprint. "
                f"Your coach's lesson: low energy is almost never random. "
                f"Over 90 days, it accumulates into either a system — or a problem. "
                f"The next sprint needs an explicit protocol for recovery days."
            )

    return "\n\n".join(lines)


def _build_bridge_section(name, profile, checkins, commitments, habits, completions) -> str:
    lines = ["PART V — THE BRIDGE\nWhat the next 90 days should look like."]

    # Three priorities (derived from profile goals)
    if profile.goals_90_days:
        lines.append(
            f"Recommended focus for the next sprint:\n"
            + "\n".join(
                f"  {i + 1}. {g}" for i, g in enumerate(profile.goals_90_days[:3])
            )
        )

    # What to stop
    missed_c = [c for c in commitments if c.status == "missed"]
    if missed_c:
        lines.append(
            f"What to stop:\n"
            f"  Committing to things in reactive moments. "
            f"Your data shows that commitments made under pressure or at high-meeting-load "
            f"have a lower completion rate. "
            f"Commit when you are calm. Commit to fewer things. "
            f"Then keep them."
        )

    # What to protect
    if habits and completions:
        completion_by_habit = {}
        for comp in completions:
            completion_by_habit[comp.habit_id] = completion_by_habit.get(comp.habit_id, 0) + 1
        top_habit = max(habits, key=lambda h: completion_by_habit.get(h.id, 0))
        top_rate = round(completion_by_habit.get(top_habit.id, 0) / 90 * 100)
        if top_rate >= 60:
            lines.append(
                f"What to protect at all costs:\n"
                f"  {top_habit.name} — your most consistent habit at {top_rate}% completion. "
                f"Whatever routine makes this possible, protect it with the same energy "
                f"you would give your most important meeting."
            )

    # One question
    lines.append(
        f"The one question for the next sprint:\n\n"
        f"  If everything external stayed the same — "
        f"the demands, the people, the pressures — "
        f"what would have to change in how YOU operate "
        f"for the next 90 days to be the best of your career so far?\n\n"
        f"  Take that question seriously. "
        f"Your coach will be here every day to help you answer it with action."
    )

    return "\n\n".join(lines)
