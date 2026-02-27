"""
Calendar-Aware Coaching
========================
Your calendar is the most honest document about your life.
Not what you say you value — what you actually spend time on.

A real coach looks at the calendar and sees things the client cannot:
  - "You have 6 meetings tomorrow and none of them are on your top 3 goals."
  - "Your HRV dropped 30% on your last three heavy-meeting days. Your body is keeping score."
  - "You have a board meeting at 9am. Your energy on Monday mornings is historically 5.2/10.
     Go for a 20-minute walk before it. Do not check email first."
  - "You were back-to-back from 10am to 6pm. No wonder you reported a stress of 8/10."

Architecture (iOS-first, privacy-safe):
  - iOS app handles all OAuth (EventKit for Apple Calendar, Google Calendar SDK for Google)
  - iOS app pushes next 7 days of events to POST /calendar/sync daily (background task)
  - Backend stores events and enriches them with coaching annotations
  - Backend NEVER stores OAuth tokens — the iOS app owns the token lifecycle
  - All calendar data is per-user, never aggregated across users

The four coaching interventions:
  1. Pre-Meeting Brief — generated 30 min before a significant meeting
     "Who's in the room, what energy you're bringing, one mindset anchor, one tactical note."

  2. Post-Meeting Prompt — sent 30 min after the meeting ends
     "How did it go? What was the one thing you wish you'd said differently?"

  3. Meeting Density Analysis — weekly pattern recognition
     "Paul Graham called it the Manager's Schedule vs the Maker's Schedule.
      Last week you had 4.2 meetings per day on average. Your energy on those days: 5.1/10.
      Your energy on meeting-light days: 7.8/10. The data speaks."

  4. Morning Calendar Brief — included in morning brief
     "Three meetings today. The 2pm with Arjun is the one that matters most. Here is your frame."
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    CalendarEvent,
    DailyCheckIn,
    HealthData,
    UserProfile,
)


# ── Meeting type classification ───────────────────────────────────────────────

_HIGH_STAKES_KEYWORDS = {
    "board", "investor", "performance review", "review", "appraisal",
    "negotiation", "pitch", "fundraise", "fundraising", "board meeting",
    "annual review", "compensation", "salary", "termination", "difficult",
    "conflict", "confrontation", "feedback", "evaluation", "okr", "strategic",
    "strategy", "leadership team", "ceo", "cxo", "executive", "partnership",
}

_FOCUS_KEYWORDS = {
    "deep work", "focus", "no meetings", "writing", "research", "blocked",
    "maker time", "thinking time", "planning", "strategy session",
}

_ONE_ON_ONE_KEYWORDS = {"1:1", "1on1", "one on one", "one-on-one", "catch up", "catch-up"}


def _classify_event(title: str, attendee_count: int) -> str:
    """Classify event type from title and attendee count."""
    tl = title.lower()
    if any(k in tl for k in _FOCUS_KEYWORDS):
        return "focus"
    if any(k in tl for k in _ONE_ON_ONE_KEYWORDS) or attendee_count == 2:
        return "1on1"
    if any(k in tl for k in _HIGH_STAKES_KEYWORDS):
        return "high_stakes"
    if attendee_count >= 8:
        return "large_meeting"
    return "meeting"


def _is_coaching_relevant(title: str, event_type: str, is_all_day: bool) -> bool:
    """Determine if coach should annotate this event."""
    if is_all_day:
        return False
    tl = title.lower()
    skip = {"lunch", "dinner", "break", "commute", "personal", "birthday", "holiday", "vacation"}
    if any(s in tl for s in skip):
        return False
    return event_type in ("high_stakes", "1on1", "meeting", "large_meeting")


# ── Calendar sync ─────────────────────────────────────────────────────────────

def sync_calendar_events(
    db: Session,
    user_id: str,
    events: list[dict],
    provider: str = "apple",
) -> dict:
    """
    Accept a batch of calendar events pushed from the iOS app.
    Upserts by external_event_id — safe to call repeatedly.

    Each event dict should contain:
      external_event_id, title, start_datetime, end_datetime,
      attendees (list of {name, email}), location, description, is_all_day
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return {"synced": 0, "error": "User not found"}

    created = 0
    updated = 0

    for ev in events:
        external_id = ev.get("external_event_id", "")
        if not external_id:
            continue

        title = ev.get("title", "Untitled")
        attendees = ev.get("attendees", [])
        is_all_day = ev.get("is_all_day", False)
        event_type = _classify_event(title, len(attendees))
        coaching_relevant = _is_coaching_relevant(title, event_type, is_all_day)

        existing = db.query(CalendarEvent).filter_by(
            user_id=user_id, external_event_id=external_id
        ).first()

        if existing:
            # Update basic fields in case time/title changed; preserve coaching annotations
            existing.title = title
            existing.start_datetime = ev.get("start_datetime", existing.start_datetime)
            existing.end_datetime = ev.get("end_datetime", existing.end_datetime)
            existing.location = ev.get("location", "")
            existing.description = ev.get("description", "")
            existing.attendees = attendees
            existing.event_type = event_type
            existing.is_all_day = is_all_day
            existing.is_coaching_relevant = coaching_relevant
            updated += 1
        else:
            ce = CalendarEvent(
                user_id=user_id,
                external_event_id=external_id,
                title=title,
                start_datetime=ev.get("start_datetime", ""),
                end_datetime=ev.get("end_datetime", ""),
                location=ev.get("location", ""),
                description=ev.get("description", ""),
                attendees=attendees,
                calendar_provider=provider,
                event_type=event_type,
                is_all_day=is_all_day,
                is_coaching_relevant=coaching_relevant,
            )
            db.add(ce)
            created += 1

    # Update profile sync metadata
    profile.calendar_integration_enabled = True
    profile.calendar_provider = provider
    profile.calendar_last_synced = datetime.utcnow().isoformat()

    db.commit()
    return {
        "synced": created + updated,
        "created": created,
        "updated": updated,
        "provider": provider,
    }


# ── Pre-meeting brief ─────────────────────────────────────────────────────────

def generate_pre_meeting_brief(db: Session, user_id: str, event_id: int) -> dict:
    """
    Generate a contextual pre-meeting coaching brief.
    Called 30 minutes before a coaching-relevant event.

    The brief includes:
      - What the coach knows about the attendees (from key_relationships)
      - User's energy level right now (from today's check-in)
      - One mindset anchor calibrated to the meeting type
      - One tactical recommendation
      - One thing NOT to do
    """
    event = db.query(CalendarEvent).filter_by(id=event_id, user_id=user_id).first()
    if not event:
        return {"error": "Event not found"}

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # Today's energy
    today_str = date.today().strftime("%Y-%m-%d")
    checkin = db.query(DailyCheckIn).filter_by(
        user_id=user_id, check_in_date=today_str
    ).first()

    # HealthKit data
    health = db.query(HealthData).filter_by(user_id=user_id, data_date=today_str).first()

    # Cross-reference attendees with key_relationships
    key_rels = profile.key_relationships if profile else []
    attendee_names = [a.get("name", "") for a in (event.attendees or [])]
    known_attendees = [
        r for r in key_rels
        if any(
            (r.get("name", "") or "").lower() in an.lower() or an.lower() in (r.get("name", "") or "").lower()
            for an in attendee_names
        )
    ]

    # Build brief sections
    sections = []

    # Section 1: Meeting overview
    meeting_time = event.start_datetime[11:16] if len(event.start_datetime) >= 16 else event.start_datetime
    sections.append(
        f"MEETING: {event.title}\n"
        f"Time: {meeting_time}"
        + (f" | Location: {event.location}" if event.location else "")
        + (f" | {len(event.attendees)} attendees" if event.attendees else "")
    )

    # Section 2: Energy calibration
    if checkin:
        energy = checkin.energy
        if energy <= 5:
            sections.append(
                f"ENERGY CHECK: Your check-in shows {energy}/10 today — lower than usual.\n"
                f"You are still capable of performing. But be deliberate: slow your pace by 20%, "
                f"listen more than you speak, and do not make any irreversible commitments today "
                f"if you can avoid them. Low energy + high-pressure meeting = reactive decisions."
            )
        elif energy >= 8:
            sections.append(
                f"ENERGY CHECK: {energy}/10 today — you are in a strong state.\n"
                f"Use this. Go in with clarity. Say the thing you've been softening."
            )
        else:
            sections.append(
                f"ENERGY CHECK: {energy}/10 — solid. You have what you need for this."
            )

    # Section 3: HRV note (if available)
    if health and health.hrv_ms:
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        recent_hrv_records = db.query(HealthData).filter(
            HealthData.user_id == user_id,
            HealthData.hrv_ms.isnot(None),
            HealthData.data_date >= (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"),
        ).all()
        if len(recent_hrv_records) >= 3:
            avg_hrv = sum(h.hrv_ms for h in recent_hrv_records if h.hrv_ms) / len(recent_hrv_records)
            if health.hrv_ms < avg_hrv * 0.8:
                sections.append(
                    f"PHYSIOLOGICAL NOTE: Your HRV is {health.hrv_ms:.0f}ms today — "
                    f"significantly below your recent average ({avg_hrv:.0f}ms). "
                    f"Your body is under load. Protect recovery time after this meeting. "
                    f"Do not schedule anything else back-to-back."
                )

    # Section 4: Known attendee context
    if known_attendees:
        for rel in known_attendees[:2]:
            rel_name = rel.get("name", "")
            rel_role = rel.get("relationship", rel.get("role", ""))
            rel_notes = rel.get("notes", rel.get("context", ""))
            attendee_note = f"PERSON: {rel_name}"
            if rel_role:
                attendee_note += f" ({rel_role})"
            if rel_notes:
                attendee_note += f"\nYour coach's note: {rel_notes}"
            sections.append(attendee_note)

    # Section 5: Mindset anchor (calibrated to meeting type)
    anchors = {
        "high_stakes": (
            "MINDSET: The goal of this meeting is not to be liked. It is to be respected and clear.\n"
            "Enter with your main ask prepared. State it in the first 3 minutes, not the last. "
            "Leaders who bury the headline lose the room."
        ),
        "1on1": (
            "MINDSET: The best thing you can do in a 1:1 is ask one great question and then listen — fully.\n"
            "Not planning your next sentence. Not half-listening while checking the time. "
            "The quality of your attention is the quality of your leadership."
        ),
        "large_meeting": (
            "MINDSET: In a large meeting, your job is not to perform. It is to move things forward.\n"
            "One clear point, well-timed, is worth more than five contributions. Choose yours."
        ),
        "meeting": (
            f"MINDSET: {name}, before you walk in — what is the single outcome you need from this meeting?\n"
            "Not what you hope for. Not what would be nice. The minimum outcome that makes this meeting worthwhile.\n"
            "Hold that in your mind. Leave if you get it early."
        ),
        "focus": (
            "FOCUS BLOCK AHEAD: Protect this time. Phone on silent. One tab open. "
            "The research on deep work is unambiguous: the first 25 minutes you are warming up. "
            "The next 90 minutes are when the real work happens. Guard it."
        ),
    }
    anchor = anchors.get(event.event_type, anchors["meeting"])
    sections.append(anchor)

    # Section 6: One thing not to do
    not_to_do = {
        "high_stakes": (
            "DO NOT: Over-explain your reasoning. State your position. Support it with one data point. "
            "Then stop. People who over-explain signal insecurity."
        ),
        "1on1": (
            "DO NOT: Make this a status update. Status updates are for email. "
            "Use this time for the conversation that cannot happen over email."
        ),
        "large_meeting": (
            "DO NOT: Talk just to be seen. Your reputation is built more by what you choose NOT to say "
            "in large rooms than by what you do say."
        ),
        "meeting": (
            "DO NOT: Leave without explicit next steps and owners. "
            "A meeting without commitments is a conversation. "
            "Commitments are what drive results."
        ),
    }
    dont = not_to_do.get(event.event_type, not_to_do["meeting"])
    sections.append(dont)

    # Assemble full brief
    brief = f"\n{'─' * 48}\n".join(sections)

    # Save to the event
    event.pre_meeting_brief = brief
    event.pre_brief_generated = True
    db.commit()

    return {
        "event_id": event_id,
        "event_title": event.title,
        "start_datetime": event.start_datetime,
        "brief": brief,
        "event_type": event.event_type,
    }


# ── Post-meeting reflection ───────────────────────────────────────────────────

def get_post_meeting_prompt(db: Session, user_id: str, event_id: int) -> dict:
    """
    Generate a post-meeting reflection prompt.
    Sent 30 minutes after the event ends.

    The prompt is calibrated to what the coach knows about the meeting.
    If a pre-meeting brief was generated, the prompt references it.
    """
    event = db.query(CalendarEvent).filter_by(id=event_id, user_id=user_id).first()
    if not event:
        return {"error": "Event not found"}

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    if event.event_type == "high_stakes":
        prompt = (
            f"{name}, that {event.title} just ended.\n\n"
            f"Three quick questions while it's fresh:\n\n"
            f"1. What was the actual outcome — did you get what you went in for?\n"
            f"2. What is the one thing you wish you'd said differently?\n"
            f"3. What's the most important follow-up action, and by when?\n\n"
            f"This doesn't need to be long. Two or three sentences per question is enough. "
            f"The reflection takes 5 minutes. The insight from it compounds for months."
        )
    elif event.event_type == "1on1":
        prompt = (
            f"Your 1:1 just wrapped. {name}, answer this honestly:\n\n"
            f"Did you give the other person your full attention — or were you partly elsewhere?\n\n"
            f"And: is there anything unsaid that still needs to be said?\n\n"
            f"(If yes, write it here and your coach will help you find the right time and words.)"
        )
    elif event.event_type == "large_meeting":
        prompt = (
            f"{event.title} is done. One question:\n\n"
            f"What was the moment in that meeting that will matter most in 3 months?\n\n"
            f"Not the whole meeting. Not the action items. The one moment. "
            f"It could be something said, a decision made, a tension left unresolved. "
            f"Name it."
        )
    else:
        prompt = (
            f"Meeting done. 30-second reflection:\n\n"
            f"What moved forward? What stalled? "
            f"And what is the most important thing that needs to happen before you sleep tonight as a result of it?\n\n"
            f"Write whatever comes. Your coach is reading."
        )

    event.post_meeting_prompt = prompt
    event.post_prompt_sent = True
    db.commit()

    return {
        "event_id": event_id,
        "event_title": event.title,
        "prompt": prompt,
    }


def save_post_meeting_note(
    db: Session, user_id: str, event_id: int, note: str
) -> dict:
    """
    Save the user's post-meeting reflection. Generate coach synthesis.
    """
    event = db.query(CalendarEvent).filter_by(id=event_id, user_id=user_id).first()
    if not event:
        return {"error": "Event not found"}

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    event.user_post_meeting_note = note

    # Coach synthesis — pattern recognition on the reflection
    note_lower = note.lower()
    synthesis_lines = []

    # Detect regret signals
    regret_words = ["wish", "should have", "shouldn't have", "mistake", "wrong", "missed", "forgot"]
    if any(w in note_lower for w in regret_words):
        synthesis_lines.append(
            f"Your coach hears some regret in this reflection. That is useful data — not a failure signal. "
            f"The leaders who improve fastest are the ones who can name what they'd do differently without "
            f"making it mean something permanent about who they are."
        )

    # Detect unresolved tension
    tension_words = ["didn't get", "not resolved", "still open", "unclear", "avoided", "didn't say"]
    if any(w in note_lower for w in tension_words):
        synthesis_lines.append(
            f"There appears to be something still unresolved. "
            f"Unresolved conversations create sustained low-level stress. "
            f"Your coach recommends scheduling a follow-up within 48 hours rather than leaving it in the air."
        )

    # Detect win signals
    win_words = ["went well", "good outcome", "agreed", "successful", "got it", "breakthrough", "progress"]
    if any(w in note_lower for w in win_words):
        synthesis_lines.append(
            f"Good. Notice this. Most high performers are faster to catalogue what went wrong "
            f"than what went right. This was a win — register it."
        )

    if not synthesis_lines:
        synthesis_lines.append(
            f"{name}, noted. Your coach has logged this reflection. "
            f"Over time, these accumulate into one of the most valuable datasets you'll own — "
            f"a record of how you think, act, and grow under pressure."
        )

    event.coach_post_meeting_synthesis = " ".join(synthesis_lines)
    db.commit()

    return {
        "event_id": event_id,
        "event_title": event.title,
        "coach_synthesis": event.coach_post_meeting_synthesis,
    }


# ── Today's calendar brief ────────────────────────────────────────────────────

def get_todays_calendar_brief(db: Session, user_id: str) -> dict:
    """
    Returns today's coaching-relevant meetings with context.
    Included in the morning brief.
    """
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id,
        CalendarEvent.start_datetime >= today_str,
        CalendarEvent.start_datetime < f"{today_str}T23:59:59",
        CalendarEvent.is_coaching_relevant == True,
        CalendarEvent.is_all_day == False,
    ).order_by(CalendarEvent.start_datetime).all()

    if not events:
        return {
            "meeting_count": 0,
            "high_stakes_count": 0,
            "coach_note": "",
            "events": [],
        }

    high_stakes = [e for e in events if e.event_type in ("high_stakes", "1on1")]
    back_to_back = _detect_back_to_back(events)

    event_summaries = []
    for e in events:
        start_time = e.start_datetime[11:16] if len(e.start_datetime) >= 16 else e.start_datetime
        end_time = e.end_datetime[11:16] if len(e.end_datetime) >= 16 else e.end_datetime
        event_summaries.append({
            "id": e.id,
            "title": e.title,
            "start_time": start_time,
            "end_time": end_time,
            "event_type": e.event_type,
            "attendee_count": len(e.attendees) if e.attendees else 0,
            "location": e.location,
        })

    # Coach note for the day
    coach_lines = []

    coach_lines.append(
        f"{'One meeting' if len(events) == 1 else f'{len(events)} meetings'} today."
    )

    if high_stakes:
        first_hs = high_stakes[0]
        hs_time = first_hs.start_datetime[11:16] if len(first_hs.start_datetime) >= 16 else ""
        coach_lines.append(
            f"The one that matters most: {first_hs.title}"
            + (f" at {hs_time}" if hs_time else "") + ". "
            f"Your coach will have a brief ready 30 minutes before."
        )

    if back_to_back:
        coach_lines.append(
            f"You have back-to-back meetings — no buffer between them. "
            f"Research shows decision quality degrades after the second consecutive meeting without a break. "
            f"If you can, push one by 15 minutes. If not, stand up and breathe between them."
        )

    if len(events) >= 5:
        coach_lines.append(
            f"{len(events)} meetings is a heavy day. Protect 60 minutes of uninterrupted time "
            f"— even if you have to decline something. A day of only meetings is a day of zero output."
        )

    return {
        "meeting_count": len(events),
        "high_stakes_count": len(high_stakes),
        "back_to_back_count": len(back_to_back),
        "coach_note": " ".join(coach_lines),
        "events": event_summaries,
    }


def _detect_back_to_back(events: list[CalendarEvent]) -> list[tuple]:
    """
    Detect back-to-back meetings (less than 15 minutes gap between end of one and start of next).
    Returns list of (event_a, event_b) pairs.
    """
    if len(events) < 2:
        return []

    btb = []
    for i in range(len(events) - 1):
        try:
            end_a = datetime.fromisoformat(events[i].end_datetime)
            start_b = datetime.fromisoformat(events[i + 1].start_datetime)
            gap_minutes = (start_b - end_a).total_seconds() / 60
            if 0 <= gap_minutes < 15:
                btb.append((events[i], events[i + 1]))
        except (ValueError, TypeError):
            continue
    return btb


# ── Meeting density analysis ──────────────────────────────────────────────────

def analyze_meeting_density(db: Session, user_id: str, days: int = 14) -> dict:
    """
    Analyse meeting load over the past N days.
    Correlates meeting density with energy scores.

    Inspired by Paul Graham's 'Maker's Schedule, Manager's Schedule' (2009):
      A maker's schedule needs large uninterrupted blocks.
      A manager's schedule is built around meetings.
      Most leaders are actually makers who've been forced onto a manager's schedule.
    """
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    today_str = date.today().strftime("%Y-%m-%d")

    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id,
        CalendarEvent.start_datetime >= cutoff,
        CalendarEvent.start_datetime < today_str,  # only past events
        CalendarEvent.is_all_day == False,
        CalendarEvent.is_coaching_relevant == True,
    ).all()

    # Group by date
    by_date: dict[str, list] = {}
    for e in events:
        d = e.start_datetime[:10]  # YYYY-MM-DD
        by_date.setdefault(d, []).append(e)

    if not by_date:
        return {
            "available": False,
            "days_analysed": days,
            "message": "No calendar data found for this period.",
        }

    # Per-day stats
    daily_stats = []
    for day_str, day_events in sorted(by_date.items()):
        # Meeting count
        meeting_count = len(day_events)

        # Back-to-back count
        btb_pairs = _detect_back_to_back(
            sorted(day_events, key=lambda e: e.start_datetime)
        )

        # Calculate total meeting time (minutes)
        total_meeting_minutes = 0
        for ev in day_events:
            try:
                start = datetime.fromisoformat(ev.start_datetime)
                end = datetime.fromisoformat(ev.end_datetime)
                total_meeting_minutes += int((end - start).total_seconds() / 60)
            except (ValueError, TypeError):
                pass

        # Energy score for that day
        checkin = db.query(DailyCheckIn).filter_by(
            user_id=user_id, check_in_date=day_str
        ).first()
        energy = checkin.energy if checkin else None

        daily_stats.append({
            "date": day_str,
            "meeting_count": meeting_count,
            "total_meeting_minutes": total_meeting_minutes,
            "back_to_back_pairs": len(btb_pairs),
            "energy": energy,
        })

    # Aggregate stats
    avg_meetings_per_day = round(
        sum(s["meeting_count"] for s in daily_stats) / len(daily_stats), 1
    )
    total_back_to_back = sum(s["back_to_back_pairs"] for s in daily_stats)
    heavy_days = [s for s in daily_stats if s["meeting_count"] >= 5]

    # Energy correlation
    energy_on_heavy_days = [
        s["energy"] for s in daily_stats
        if s["meeting_count"] >= 4 and s["energy"] is not None
    ]
    energy_on_light_days = [
        s["energy"] for s in daily_stats
        if s["meeting_count"] <= 2 and s["energy"] is not None
    ]

    avg_energy_heavy = (
        round(sum(energy_on_heavy_days) / len(energy_on_heavy_days), 1)
        if energy_on_heavy_days else None
    )
    avg_energy_light = (
        round(sum(energy_on_light_days) / len(energy_on_light_days), 1)
        if energy_on_light_days else None
    )

    # Coach's analysis
    coach_analysis = _generate_density_analysis(
        avg_meetings_per_day,
        total_back_to_back,
        len(heavy_days),
        avg_energy_heavy,
        avg_energy_light,
        days,
    )

    return {
        "available": True,
        "days_analysed": days,
        "days_with_meetings": len(by_date),
        "avg_meetings_per_day": avg_meetings_per_day,
        "total_back_to_back_incidents": total_back_to_back,
        "heavy_days_count": len(heavy_days),  # 5+ meetings
        "avg_energy_on_heavy_days": avg_energy_heavy,
        "avg_energy_on_light_days": avg_energy_light,
        "coach_analysis": coach_analysis,
        "daily_breakdown": daily_stats,
    }


def _generate_density_analysis(
    avg_meetings: float,
    total_btb: int,
    heavy_days: int,
    energy_heavy: float | None,
    energy_light: float | None,
    days: int,
) -> str:
    """Generate the coach's written analysis of meeting density patterns."""
    lines = []

    # Overall load
    if avg_meetings >= 5:
        lines.append(
            f"Over the past {days} days, you averaged {avg_meetings} meetings per day. "
            f"That is a manager's schedule — at the extreme end. "
            f"Paul Graham wrote that one meeting can destroy an afternoon for a maker. "
            f"At {avg_meetings}/day, entire weeks are being fragmented. "
            f"Your coach's question: what percentage of these meetings required your presence specifically?"
        )
    elif avg_meetings >= 3:
        lines.append(
            f"You averaged {avg_meetings} meetings per day over {days} days — a moderate-to-heavy load. "
            f"This is manageable if you have protected deep-work blocks around them. "
            f"Do you? Your coach is asking seriously."
        )
    else:
        lines.append(
            f"Your average of {avg_meetings} meetings per day is relatively healthy. "
            f"The question is whether you're using the non-meeting time for actual deep work, "
            f"or just recovering from meetings."
        )

    # Back-to-back
    if total_btb >= 5:
        lines.append(
            f"You had {total_btb} back-to-back meeting transitions in this period — "
            f"moments where one meeting ended and the next began within 15 minutes. "
            f"Each transition costs you 10-15 minutes of re-engagement time that doesn't show up anywhere. "
            f"Build 15-minute buffers. Non-negotiable."
        )

    # Energy correlation
    if energy_heavy is not None and energy_light is not None:
        gap = round(energy_light - energy_heavy, 1)
        if gap >= 1.5:
            lines.append(
                f"The data is clear: your energy on meeting-heavy days ({energy_heavy}/10) "
                f"is {gap} points lower than on lighter days ({energy_light}/10). "
                f"Your calendar is not neutral — it is actively shaping how you feel and perform. "
                f"This is not a willpower issue. This is a calendar design issue."
            )
        elif gap >= 0.5:
            lines.append(
                f"Your energy averages {energy_heavy}/10 on heavy meeting days vs "
                f"{energy_light}/10 on lighter days. A modest but consistent difference. "
                f"Watch this trend over time — the gap often widens before leaders catch it."
            )

    return " ".join(lines)


# ── Calendar context for coaching system prompt ───────────────────────────────

def get_calendar_context_for_coaching(db: Session, user_id: str) -> str:
    """
    Returns a 2-3 line calendar context string for injection into coaching system prompts.
    Only included when calendar integration is enabled and today has events.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile or not profile.calendar_integration_enabled:
        return ""

    today_str = date.today().strftime("%Y-%m-%d")
    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id,
        CalendarEvent.start_datetime >= today_str,
        CalendarEvent.start_datetime < f"{today_str}T23:59:59",
        CalendarEvent.is_coaching_relevant == True,
        CalendarEvent.is_all_day == False,
    ).order_by(CalendarEvent.start_datetime).all()

    if not events:
        return ""

    high_stakes = [e for e in events if e.event_type in ("high_stakes", "1on1")]
    context_parts = [f"Today's calendar: {len(events)} meeting(s)"]

    if high_stakes:
        titles = [e.title for e in high_stakes[:2]]
        context_parts.append(f"High-priority: {', '.join(titles)}")

    # Next upcoming event right now
    now_str = datetime.utcnow().isoformat()
    upcoming = [e for e in events if e.start_datetime >= now_str]
    if upcoming:
        next_ev = upcoming[0]
        start_time = next_ev.start_datetime[11:16] if len(next_ev.start_datetime) >= 16 else ""
        context_parts.append(f"Next: {next_ev.title}" + (f" at {start_time}" if start_time else ""))

    return "\nCALENDAR CONTEXT:\n  " + " | ".join(context_parts) + "\n"


# ── Calendar settings ─────────────────────────────────────────────────────────

def toggle_calendar_integration(
    db: Session, user_id: str, enabled: bool, provider: str = ""
) -> dict:
    """Enable or disable calendar integration for a user."""
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return {"error": "User not found"}

    profile.calendar_integration_enabled = enabled
    if provider:
        profile.calendar_provider = provider
    if not enabled:
        profile.calendar_last_synced = ""

    db.commit()
    return {
        "calendar_integration_enabled": enabled,
        "calendar_provider": profile.calendar_provider,
        "message": (
            "Calendar integration enabled. Sync your first batch of events via POST /calendar/sync."
            if enabled
            else "Calendar integration disabled. No new events will be processed."
        ),
    }
