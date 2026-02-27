"""
Crisis Mode — Emergency Coaching Protocol
==========================================
Real coaches are there for the rock-bottom moments, not just the goal-setting sessions.

Crisis mode activates when:
  - Energy drops to 2 or below for 3+ consecutive days
  - The user says "I'm done", "I can't do this", "I want to quit", "I'm falling apart"
  - The check-in mood note contains crisis language (detected by keyword engine)
  - The user explicitly calls it themselves via /coach/crisis

What a real coach does in a crisis:
  1. Presence first — not advice, not frameworks, not data
  2. Validate the experience without amplifying it
  3. Get to ONE stabilising action — not a plan, not a list, one thing
  4. Separate the storm from the person — "you are not your worst week"
  5. Safety check — if there are signals of genuine mental health crisis,
     the coach acknowledges it and provides guidance to seek professional support
  6. Follow-up the NEXT DAY — a real coach does not disappear after a hard session

Mental health safety note:
  This service is a coaching tool, not a clinical intervention.
  If the user expresses genuine risk of self-harm, the response ALWAYS includes
  a recommendation to speak with a mental health professional or crisis line,
  and does NOT attempt to serve as a substitute for that support.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import DailyCheckIn, UserProfile


_CRISIS_KEYWORDS = {
    "i'm done", "i am done", "i can't do this", "i cannot do this",
    "i want to quit", "want to give up", "falling apart", "breaking down",
    "can't go on", "cannot go on", "i'm finished", "i give up",
    "what's the point", "whats the point", "no point anymore",
    "i'm failing", "i am failing", "complete failure",
}

_ACUTE_DISTRESS_KEYWORDS = {
    "hurt myself", "end it", "disappear", "don't want to be here",
    "better off without me", "can't take it anymore", "too much pain",
}


def detect_crisis_signal(text: str, energy: float | None = None) -> dict:
    """
    Detect whether a message contains crisis-level signals.
    Returns severity: none / elevated / high / acute
    """
    lower = text.lower()

    # Acute — always escalate to professional support guidance
    if any(phrase in lower for phrase in _ACUTE_DISTRESS_KEYWORDS):
        return {"severity": "acute", "matched": "acute_distress"}

    # High — full crisis mode response
    if any(phrase in lower for phrase in _CRISIS_KEYWORDS):
        return {"severity": "high", "matched": "crisis_keyword"}

    # Energy-based
    if energy is not None and energy <= 2:
        return {"severity": "high", "matched": "extreme_low_energy"}

    # Elevated — softer but still crisis-aware response
    elevated_words = {"exhausted", "overwhelmed", "hopeless", "meaningless", "trapped"}
    hits = set(re.findall(r"\b\w+\b", lower)) & elevated_words
    if len(hits) >= 2:
        return {"severity": "elevated", "matched": "elevated_distress"}

    return {"severity": "none", "matched": None}


def generate_crisis_response(
    db: Session,
    user_id: str,
    user_message: str,
    detected_severity: str,
    energy: float | None = None,
) -> dict:
    """
    Generate a crisis-mode coaching response.
    Severity determines the register: elevated → warm and grounding;
    high → full presence; acute → safety-first with professional resources.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    if detected_severity == "acute":
        response = (
            f"{name}, I hear you. What you're describing sounds like you're carrying "
            f"something much heavier than you should carry alone.\n\n"
            f"I want to be honest with you: I'm a coaching tool, not a crisis counsellor. "
            f"What you need right now is a real human — someone trained for exactly this moment.\n\n"
            f"Please reach out to one of these:\n"
            f"  - iCall (India): 9152987821\n"
            f"  - Vandrevala Foundation (India, 24/7): 1860-2662-345\n"
            f"  - Or call someone you trust right now — not tomorrow, now.\n\n"
            f"Your coach will be here when you're ready to talk about what's beneath this. "
            f"But first — reach out to a real person today."
        )
        return {
            "response": response,
            "severity": "acute",
            "professional_support_recommended": True,
            "follow_up_tomorrow": True,
        }

    elif detected_severity == "high":
        response = (
            f"{name}.\n\n"
            f"I'm not going to give you a framework right now. I'm not going to list actions. "
            f"I'm going to say one thing first: what you are feeling is real, and it makes sense.\n\n"
            f"The pressure you are under — the weight of the role, the relationships, the expectations — "
            f"is not small. The fact that you are struggling does not mean you are failing. "
            f"It means you are human, and you have been carrying too much for too long without enough support.\n\n"
            f"Here is the one thing your coach is asking of you right now:\n"
            f"Name one person — just one — you can call today. Not to solve anything. Just to hear your voice.\n\n"
            f"You don't have to have it figured out. You just have to not be alone in it right now.\n\n"
            f"Your coach will be here tomorrow morning. We will talk about what comes next. "
            f"But tonight — one call. One person. That is all."
        )
        return {
            "response": response,
            "severity": "high",
            "professional_support_recommended": False,
            "one_action": "Call one trusted person today — not to solve anything, just to connect.",
            "follow_up_tomorrow": True,
        }

    else:  # elevated
        response = (
            f"{name}, something in what you said is telling your coach that you're not okay. "
            f"Not catastrophically — but enough that the normal coaching response would miss the mark.\n\n"
            f"So let me ask you directly: what is the single hardest thing right now? "
            f"Not the list. The one thing that, if it resolved tomorrow, would change the feeling in your chest.\n\n"
            f"We can work with that. One thing at a time. You don't have to solve it today. "
            f"You just have to name it."
        )
        return {
            "response": response,
            "severity": "elevated",
            "professional_support_recommended": False,
            "one_action": "Name the single hardest thing right now. Not a list. One thing.",
            "follow_up_tomorrow": False,
        }


def get_crisis_follow_up(db: Session, user_id: str) -> dict | None:
    """
    If a crisis response was flagged for follow-up, the morning brief includes this.
    Checks if yesterday had very low energy that might indicate a crisis was ongoing.
    """
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    ci = db.query(DailyCheckIn).filter_by(user_id=user_id, check_in_date=yesterday).first()

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    if not ci or ci.energy > 4:
        return None

    # Check if mood note had crisis signals
    if ci.mood_note:
        signal = detect_crisis_signal(ci.mood_note, energy=ci.energy)
        if signal["severity"] in ("high", "acute"):
            return {
                "follow_up_message": (
                    f"{name}, your coach noticed yesterday was a very difficult day. "
                    f"How are you this morning? Before we do anything else — just tell me where you are."
                ),
                "priority": "urgent",
            }

    if ci.energy <= 3:
        return {
            "follow_up_message": (
                f"{name}, yesterday was hard. Your energy was {ci.energy}/10. "
                f"Today, your only job before 10am is to tell your coach how you're actually feeling."
            ),
            "priority": "high",
        }

    return None
