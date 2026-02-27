"""
Bilingual Coaching — Hindi + English
======================================
For Indian professionals, the emotional register of Hindi is fundamentally richer.
A leader who thinks in Hindi but communicates in English carries a translation tax
every time they try to express something emotional, urgent, or deeply personal.

This service:
  1. Detects the dominant language of any message (Hindi script, Hinglish, English)
  2. Issues coaching responses in the same language the user wrote in
  3. Supports Hinglish (Hindi-English code-switching) — the real language of urban India
  4. Stores the user's preferred language in UserProfile

Detection logic:
  - Devanagari Unicode range (0900-097F) → Hindi
  - High frequency of common Hinglish words → Hinglish
  - Otherwise → English

Response strategy:
  - Full Hindi: respond in Hindi (using the system prompt instruction)
  - Hinglish: respond in Hinglish — natural, warm, not formal
  - English: respond in English (default)

The coaching voice does not change — only the language.
Robin Sharma in Hindi would still say the same things. He would just say them in a way
that lands closer to home.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import UserProfile


# Devanagari Unicode block (simplified check)
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# Common Hinglish markers (high-confidence code-switch indicators)
_HINGLISH_WORDS = {
    "yaar", "bhai", "kya", "nahi", "haan", "bilkul", "matlab",
    "accha", "achi", "theek", "lagta", "bahut", "thoda", "abhi",
    "phir", "sahi", "agar", "toh", "lekin", "aur", "woh", "main",
    "mujhe", "apna", "apni", "unka", "unki", "samajh", "zyada",
    "kam", "bohot", "kaafi", "itna", "kitna", "kuch", "koi",
}


def detect_language(text: str) -> str:
    """
    Returns: 'hi' (Hindi/Devanagari), 'hi-en' (Hinglish), or 'en' (English)
    """
    if _DEVANAGARI_RE.search(text):
        return "hi"

    words = set(re.findall(r"\b\w+\b", text.lower()))
    hinglish_hits = words & _HINGLISH_WORDS
    if len(hinglish_hits) >= 2:
        return "hi-en"

    return "en"


def get_language_instruction(lang: str) -> str:
    """
    Returns a system prompt instruction to include when the user writes in Hindi/Hinglish.
    """
    if lang == "hi":
        return (
            "\n[LANGUAGE INSTRUCTION: The user has written in Hindi. "
            "Respond entirely in Hindi (Devanagari script). "
            "Maintain the coaching voice — direct, warm, evidence-based. "
            "Do not translate frameworks literally; use equivalent Hindi expressions where possible.]"
        )
    elif lang == "hi-en":
        return (
            "\n[LANGUAGE INSTRUCTION: The user is writing in Hinglish (Hindi-English mix). "
            "Respond in natural Hinglish — mix Hindi and English as a peer would, "
            "warm and direct. Avoid formal Hindi. Sound like a trusted mentor who speaks both. "
            "Key coaching terms (goal, accountability, milestone, habit) can stay in English.]"
        )
    return ""  # English — no instruction needed


def update_language_preference(db: Session, user_id: str, lang: str) -> None:
    """Update stored preference based on detected language."""
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if profile and profile.preferred_language != lang:
        profile.preferred_language = lang
        db.commit()


def get_language_aware_greeting(profile: UserProfile | None) -> str:
    """Return a language-appropriate greeting based on stored preference."""
    lang = profile.preferred_language if profile else "en"
    name = profile.full_name.split()[0] if profile and profile.full_name else ""

    if lang == "hi":
        return f"नमस्ते, {name}। आज आप कैसे हैं?" if name else "नमस्ते। आज आप कैसे हैं?"
    elif lang == "hi-en":
        return f"Hey {name}, kaise ho? Aaj ka din kaisa chal raha hai?" if name else "Kaise ho? Aaj ka din kaisa chal raha hai?"
    else:
        return f"Good morning, {name}." if name else "Good morning."
