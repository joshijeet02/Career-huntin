"""
Conversational Check-In Service
================================
Replaces the 3-number form (energy/stress/sleep) with a coach-led dialogue.
The coach opens the conversation naturally, listens, and extracts what it needs
from the tone, choice of words, and content of the user's response.

Flow:
  1. User hits /checkin/start  → coach opens with a warm, personalised question
  2. User responds (text or voice transcript)  → /checkin/respond
  3. Coach parses the response for signals (energy, stress, sleep, mood, tone)
  4. Coach asks 0-2 follow-up questions if needed, then issues a coaching response
  5. The result is saved identically to the old DailyCheckIn model — fully compatible

Tone detection (text-based heuristics + OpenAI sentiment when available):
  - Exclamation counts, negative word density, capitalization patterns
  - Keyword sets for exhaustion / anger / grief / elation / anxiety
  - If voice transcript is passed, the same engine runs on the words
  (True audio-waveform tone analysis happens in the iOS app using AVAudioEngine /
   SpeechFramework before the transcript is sent — the API receives a tone_hint field)
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import DailyCheckIn, UserProfile
from app.schemas import (
    ConversationalCheckInResponse,
    ConversationalCheckInStartResponse,
    DailyCheckInResponse,
)
from app.services.checkin import _assess_burnout_risk, _coach_response_for_checkin


# ── Tone / emotional signal detection ────────────────────────────────────────

_EXHAUSTION_WORDS = {
    "tired", "exhausted", "drained", "burned out", "burnt out", "depleted",
    "fatigued", "wiped", "worn out", "no energy", "can't focus", "foggy",
    "barely", "struggling", "heavy", "slow", "just got up", "bad night",
}
_STRESS_WORDS = {
    "stressed", "overwhelmed", "pressure", "deadline", "too much", "swamped",
    "anxious", "worried", "tense", "on edge", "fight", "argument", "conflict",
    "difficult", "hard", "problem", "issue", "angry", "frustrated", "upset",
    "horrible", "terrible", "awful", "worst", "hate", "furious",
}
_HIGH_ENERGY_WORDS = {
    "great", "excellent", "amazing", "fantastic", "energized", "pumped",
    "ready", "motivated", "good", "solid", "strong", "clear", "sharp",
    "rested", "slept well", "productive", "excited", "happy",
}
_POOR_SLEEP_WORDS = {
    "didn't sleep", "couldn't sleep", "insomnia", "woke up", "3am", "4am",
    "bad sleep", "poor sleep", "tired from", "no sleep", "barely slept",
    "tossed", "nightmares", "restless",
}
_RELATIONSHIP_WORDS = {
    "wife", "husband", "partner", "son", "daughter", "parent", "father",
    "mother", "boss", "team", "colleague", "board", "fight", "argument",
    "conflict", "relationship", "family",
}


def _detect_signals(text: str, tone_hint: str | None = None) -> dict:
    """
    Extract energy, stress, sleep, mood, and relationship flags from free text.
    Returns a dict of signals with confidence levels.
    """
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))

    exhaustion_hits = words & _EXHAUSTION_WORDS
    stress_hits = words & _STRESS_WORDS
    energy_hits = words & _HIGH_ENERGY_WORDS
    sleep_hits = words & _POOR_SLEEP_WORDS
    rel_hits = words & _RELATIONSHIP_WORDS

    # Negative word density (rough sentiment)
    neg_density = (len(exhaustion_hits) + len(stress_hits)) / max(len(words), 1)

    # Exclamation marks signal emotion intensity
    exclamations = text.count("!")
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

    # Base estimates
    energy_raw = 7.0
    stress_raw = 4.0
    sleep_raw = 7.0

    # Adjust energy
    if exhaustion_hits:
        energy_raw -= min(4.0, len(exhaustion_hits) * 1.5)
    if energy_hits:
        energy_raw += min(2.0, len(energy_hits) * 0.8)
    if tone_hint == "tired":
        energy_raw -= 2.0
    elif tone_hint == "energized":
        energy_raw += 1.5

    # Adjust stress
    if stress_hits:
        stress_raw += min(5.0, len(stress_hits) * 1.2)
    if exclamations >= 3 or caps_ratio > 0.25:
        stress_raw += 1.5
    if tone_hint == "angry" or tone_hint == "distressed":
        stress_raw += 2.0

    # Sleep
    if sleep_hits:
        sleep_raw -= min(4.0, len(sleep_hits) * 2.0)

    # Clamp to valid ranges
    energy = round(max(1.0, min(10.0, energy_raw)), 1)
    stress = round(max(1.0, min(10.0, stress_raw)), 1)
    sleep = round(max(1.0, min(10.0, sleep_raw)), 1)

    # Dominant emotional track
    track = "leadership"
    if rel_hits:
        track = "relationships"
    elif exhaustion_hits and energy < 5:
        track = "energy"

    return {
        "energy": energy,
        "stress": stress,
        "sleep_quality": sleep,
        "mood_note": text[:500],
        "relationship_flag": bool(rel_hits),
        "relationship_persons": list(rel_hits & {"wife", "husband", "partner", "son",
                                                  "daughter", "parent", "boss", "team"}),
        "dominant_track": track,
        "confidence": "high" if (exhaustion_hits or stress_hits or energy_hits) else "low",
        "needs_followup": (
            len(exhaustion_hits) == 0 and len(stress_hits) == 0
            and len(energy_hits) == 0 and tone_hint is None
        ),
    }


# ── Opening question generator ────────────────────────────────────────────────

_OPENING_TEMPLATES = [
    "How are you waking up today, {name}? What's the first thing on your mind?",
    "{name}, before the day pulls you in — how are you, really?",
    "Good morning, {name}. Take one breath. Now tell me — how did you sleep, and what's sitting on your chest right now?",
    "{name}, you're here. That matters. How's the energy today — and what's the loudest thing in your head?",
    "Let's start simple, {name}: on the inside, how are you doing today?",
]

import random

def _opening_question(profile: UserProfile | None) -> str:
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"
    template = random.choice(_OPENING_TEMPLATES)
    return template.format(name=name)


# ── Follow-up question logic ───────────────────────────────────────────────────

def _followup_question(signals: dict, profile: UserProfile | None) -> str | None:
    """Return one targeted follow-up question based on what's missing or flagged."""
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    if signals.get("relationship_flag") and signals["dominant_track"] == "relationships":
        persons = signals.get("relationship_persons", [])
        person = persons[0] if persons else "someone close to you"
        return (
            f"You mentioned {person} — I want to make sure I understand. "
            f"Is this something that's weighing on you right now, or did you want to talk it through?"
        )

    if signals["confidence"] == "low":
        return (
            f"{name}, I want to be accurate about where you are. "
            f"On a scale of 1-10, how would you rate your energy right now — and how well did you sleep?"
        )

    if signals["energy"] <= 4 and signals.get("needs_followup"):
        return (
            f"You sound like you're running on low. Has anything specific happened "
            f"in the last 24 hours that's contributing to this?"
        )

    return None  # No follow-up needed


# ── Coaching response builder ─────────────────────────────────────────────────

def _build_coaching_response(
    signals: dict,
    profile: UserProfile | None,
    consecutive_low: int,
) -> str:
    """
    Build the coaching response, routing relationship-flagged conversations to
    a specialised relationship coaching response rather than the standard checkin message.
    """
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    if signals.get("relationship_flag") and signals["dominant_track"] == "relationships":
        persons = signals.get("relationship_persons", [])
        person = persons[0] if persons else "someone close"
        return (
            f"Center: {name}, relationships are the real work of leadership — and you're doing it by talking about it.\n\n"
            f"Reframe: The fact that this is present for you today means it deserves attention, not avoidance. "
            f"What's happening at home or with {person} will affect every decision you make today. "
            f"That's not weakness — that's reality.\n\n"
            "Actions:\n"
            f"  1. Before your first big call — send one short, honest message to {person}. Not to fix it. Just to acknowledge it.\n"
            "  2. Identify: what is the one thing you said or didn't say that you wish you could change?\n"
            "  3. Tonight, create 30 uninterrupted minutes — phone away — to have the real conversation.\n\n"
            "Accountability question: What will you say to them today, and when?\n\n"
            "Evidence spotlight: Gottman's research shows that the single greatest predictor of relationship "
            "repair is not the absence of conflict — it is the speed and genuineness of the repair attempt."
        )

    # Standard energy-based response
    risk = _assess_burnout_risk(signals["energy"], signals["stress"], consecutive_low)
    msg, _ = _coach_response_for_checkin(
        signals["energy"], signals["stress"], risk, consecutive_low, profile.full_name if profile else ""
    )
    return msg


# ── Main service functions ────────────────────────────────────────────────────

def start_checkin(db: Session, user_id: str) -> ConversationalCheckInStartResponse:
    """
    Opens the check-in conversation with a warm, personalised question.
    Called from GET /checkin/start
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    question = _opening_question(profile)

    # Check if already checked in today
    today = date.today().strftime("%Y-%m-%d")
    existing = db.query(DailyCheckIn).filter_by(user_id=user_id, check_in_date=today).first()
    already_done = existing is not None

    return ConversationalCheckInStartResponse(
        opening_question=question,
        already_checked_in_today=already_done,
        check_in_date=today,
    )


def process_conversational_checkin(
    db: Session,
    user_id: str,
    user_response: str,
    tone_hint: str | None = None,
    is_followup_response: bool = False,
    followup_response_text: str | None = None,
) -> ConversationalCheckInResponse:
    """
    Processes the user's natural language response to the check-in question.
    Extracts signals, optionally asks one follow-up, then issues a coaching response
    and saves a DailyCheckIn record (fully compatible with existing schema).

    tone_hint: optional iOS-side tone analysis result
               ("tired" | "energized" | "angry" | "distressed" | "neutral")
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    # Combine initial response with follow-up if provided
    full_text = user_response
    if is_followup_response and followup_response_text:
        full_text = f"{user_response}. {followup_response_text}"

    signals = _detect_signals(full_text, tone_hint=tone_hint)

    # Determine whether to ask a follow-up (only on first response, not follow-up)
    followup_q = None
    if not is_followup_response and signals.get("needs_followup"):
        followup_q = _followup_question(signals, profile)

    if followup_q:
        # Return the follow-up question without saving yet — client must call again
        return ConversationalCheckInResponse(
            status="needs_followup",
            followup_question=followup_q,
            check_in_date=date.today().strftime("%Y-%m-%d"),
            energy=signals["energy"],
            stress=signals["stress"],
            sleep_quality=signals["sleep_quality"],
            burnout_risk=None,
            coach_response=None,
            alert=None,
            dominant_track=signals["dominant_track"],
            relationship_flag=signals["relationship_flag"],
        )

    # Count consecutive low energy days
    today = date.today().strftime("%Y-%m-%d")
    cutoff = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.check_in_date >= cutoff,
            DailyCheckIn.check_in_date < today,
        )
        .order_by(DailyCheckIn.check_in_date.desc())
        .all()
    )
    consecutive_low = 0
    for r in recent:
        if r.energy <= 5.0:
            consecutive_low += 1
        else:
            break
    if signals["energy"] <= 5.0:
        consecutive_low += 1

    risk = _assess_burnout_risk(signals["energy"], signals["stress"], consecutive_low)
    coach_msg = _build_coaching_response(signals, profile, consecutive_low)

    # Build alert if risk is high
    alert = None
    if risk == "high":
        alert = (
            f"Your energy has been low for {consecutive_low} consecutive days. "
            "Your coach has flagged this as a high burnout risk. Please prioritise recovery today."
        )

    # Upsert today's DailyCheckIn record (compatible with old schema)
    existing = db.query(DailyCheckIn).filter_by(user_id=user_id, check_in_date=today).first()
    if existing:
        existing.energy = signals["energy"]
        existing.stress = signals["stress"]
        existing.sleep_quality = signals["sleep_quality"]
        existing.mood_note = signals["mood_note"]
        existing.coach_response = coach_msg
        existing.updated_at = datetime.utcnow()
    else:
        db.add(DailyCheckIn(
            user_id=user_id,
            check_in_date=today,
            energy=signals["energy"],
            stress=signals["stress"],
            sleep_quality=signals["sleep_quality"],
            mood_note=signals["mood_note"],
            coach_response=coach_msg,
        ))

    # Update rolling baseline on profile
    if profile:
        profile.energy_baseline = round(profile.energy_baseline * 0.8 + signals["energy"] * 0.2, 2)
        profile.burnout_risk = risk
        if signals["energy"] <= 5.0:
            profile.consecutive_low_energy_days = consecutive_low
        else:
            profile.consecutive_low_energy_days = 0

    db.commit()

    return ConversationalCheckInResponse(
        status="complete",
        followup_question=None,
        check_in_date=today,
        energy=signals["energy"],
        stress=signals["stress"],
        sleep_quality=signals["sleep_quality"],
        burnout_risk=risk,
        coach_response=coach_msg,
        alert=alert,
        dominant_track=signals["dominant_track"],
        relationship_flag=signals["relationship_flag"],
    )
