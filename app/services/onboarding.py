"""
Onboarding Interview Engine
─────────────────────────────────────────────────────────────────────────────
Runs a 10-15 minute conversational intake session when a new user signs up.
Each answer is parsed and stored into UserProfile.
Once complete, every coaching call uses that profile to personalise responses.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import UserProfile


# ── Interview Script ──────────────────────────────────────────────────────────
# Each step has a question and a parser that maps the raw answer → profile field.

ONBOARDING_QUESTIONS: list[dict[str, Any]] = [
    {
        "step": 0,
        "question": (
            "Welcome! I'm your personal coach. Let's start with the basics.\n\n"
            "What's your full name, and what role do you hold right now?"
        ),
        "hint": "e.g. Jayesh Joshi, CEO at VAAGDHARA",
        "field": "identity",
    },
    {
        "step": 1,
        "question": (
            "Great to meet you!\n\n"
            "Tell me about the organisation you lead or work in - what does it do, "
            "and roughly how many people are impacted by its work?"
        ),
        "hint": "e.g. A nonprofit focused on tribal education, ~50,000 beneficiaries",
        "field": "organization",
    },
    {
        "step": 2,
        "question": (
            "If you had to name the single biggest challenge you're facing right now - "
            "the one that keeps you up at night - what would it be?"
        ),
        "hint": "Be as specific as you like. This stays private and encrypted.",
        "field": "biggest_challenge",
    },
    {
        "step": 3,
        "question": (
            "Think about the three or four relationships that matter most to your "
            "success and wellbeing - personal and professional.\n\n"
            "Who are they, and what makes each relationship important or tricky right now?"
        ),
        "hint": "e.g. My co-founder (trust tension), my spouse (distance during travel), board chair (alignment gaps)",
        "field": "key_relationships",
    },
    {
        "step": 4,
        "question": (
            "What are the two or three values you absolutely refuse to compromise on, "
            "even when things get hard?"
        ),
        "hint": "e.g. Honesty, community-first, long-term thinking",
        "field": "core_values",
    },
    {
        "step": 5,
        "question": (
            "Looking at the next 90 days - what are the two or three outcomes that, "
            "if you achieved them, would make you say this was a great quarter?\n\n"
            "For each one, is it mainly a leadership goal, a relationship goal, "
            "or a personal wellbeing goal?"
        ),
        "hint": "e.g. Launch the new district programme (leadership), repair trust with my deputy (relationship)",
        "field": "goals_90_days",
    },
    {
        "step": 6,
        "question": (
            "On a scale from 1 to 10, where is your energy and stress right now?\n\n"
            "And what are the top one or two things draining you most?"
        ),
        "hint": "e.g. Energy 5/10 - draining: constant travel and unresolved team conflict",
        "field": "current_stressors",
    },
    {
        "step": 7,
        "question": (
            "Last question: how do you like to be coached?\n\n"
            "Do you prefer direct and no-nonsense, gentle and exploratory, "
            "or someone who asks you questions and lets you find the answers yourself?"
        ),
        "hint": "Choose one: direct / gentle / socratic - or describe your own style.",
        "field": "coaching_style_preference",
    },
]

TOTAL_STEPS = len(ONBOARDING_QUESTIONS)


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_identity(answer: str, profile: UserProfile) -> None:
    """Try to extract name and role from a free-text answer."""
    # Simple heuristic: first capitalised run = name, rest = role
    parts = re.split(r",\s*|\s+at\s+|\s+-\s+", answer, maxsplit=2)
    if parts:
        profile.full_name = parts[0].strip()
    if len(parts) >= 2:
        profile.role = parts[1].strip()
    if len(parts) >= 3:
        profile.organization = parts[2].strip()


def _parse_organization(answer: str, profile: UserProfile) -> None:
    profile.organization = answer.strip()
    lower = answer.lower()
    if any(w in lower for w in ["nonprofit", "ngo", "foundation", "trust"]):
        profile.organization_type = "nonprofit"
    elif any(w in lower for w in ["startup", "founded", "venture"]):
        profile.organization_type = "startup"
    elif any(w in lower for w in ["corporate", "firm", "company", "ltd", "inc"]):
        profile.organization_type = "corporate"
    else:
        profile.organization_type = "other"


def _parse_relationships(answer: str, profile: UserProfile) -> None:
    # Split on commas, semicolons, or newlines to get individual relationships
    items = re.split(r"[,;\n]+", answer)
    relationships = []
    for item in items:
        item = item.strip()
        if len(item) > 3:
            relationships.append({"description": item, "importance": "high"})
    profile.key_relationships = relationships[:6]  # cap at 6


def _parse_values(answer: str, profile: UserProfile) -> None:
    items = re.split(r"[,;\n]+", answer)
    profile.core_values = [v.strip() for v in items if len(v.strip()) > 1][:6]


def _parse_goals(answer: str, profile: UserProfile) -> None:
    items = re.split(r"[,;\n]+|\d+[\.\)]\s+", answer)
    goals = []
    for item in items:
        item = item.strip()
        if len(item) < 5:
            continue
        track = "general"
        lower = item.lower()
        if any(w in lower for w in ["lead", "strategy", "decision", "team", "board"]):
            track = "leadership"
        elif any(w in lower for w in ["relationship", "trust", "partner", "family", "repair"]):
            track = "relationship"
        elif any(w in lower for w in ["health", "energy", "burnout", "rest", "wellbeing"]):
            track = "wellbeing"
        goals.append({"goal": item, "track": track, "priority": len(goals) + 1})
    profile.goals_90_days = goals[:5]


def _parse_stressors(answer: str, profile: UserProfile) -> None:
    items = re.split(r"[,;\n]+", answer)
    profile.current_stressors = [s.strip() for s in items if len(s.strip()) > 2][:5]


def _parse_coaching_style(answer: str, profile: UserProfile) -> None:
    lower = answer.lower()
    if "socratic" in lower or "question" in lower or "find" in lower:
        profile.coaching_style_preference = "socratic"
    elif "gentle" in lower or "exploratory" in lower or "soft" in lower:
        profile.coaching_style_preference = "gentle"
    else:
        profile.coaching_style_preference = "direct"


FIELD_PARSERS = {
    "identity": _parse_identity,
    "organization": _parse_organization,
    "biggest_challenge": lambda a, p: setattr(p, "biggest_challenge", a.strip()),
    "key_relationships": _parse_relationships,
    "core_values": _parse_values,
    "goals_90_days": _parse_goals,
    "current_stressors": _parse_stressors,
    "coaching_style_preference": _parse_coaching_style,
}


# ── Profile Summary ───────────────────────────────────────────────────────────

def _build_profile_summary(profile: UserProfile) -> str:
    goals_text = ", ".join(g["goal"][:60] for g in profile.goals_90_days[:3])
    values_text = ", ".join(profile.core_values[:3])
    return (
        f"Welcome, {profile.full_name}. Your coaching profile is ready.\n\n"
        f"I know you as {profile.role} at {profile.organization}. "
        f"Your biggest challenge right now is: {profile.biggest_challenge[:120]}.\n\n"
        f"Your top 90-day goals: {goals_text or 'to be refined in our first session'}.\n"
        f"Values I'll always respect: {values_text or 'shared in your answers'}.\n\n"
        f"Coaching style set to: {profile.coaching_style_preference.upper()}.\n\n"
        "Every coaching session from here will be built around exactly who you are and what you're working towards. Let's begin."
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_or_create_profile(db: Session, user_id: str) -> UserProfile:
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id, full_name="", role="", organization="")
        db.add(profile)
        db.flush()
    return profile


def get_next_question(step: int) -> dict[str, Any] | None:
    if step >= TOTAL_STEPS:
        return None
    return ONBOARDING_QUESTIONS[step]


def process_onboarding_step(
    db: Session, user_id: str, step: int, answer: str
) -> tuple[str | None, bool, str | None]:
    """
    Save the answer for `step`, parse it into the profile, then return:
      (next_question_text, is_complete, profile_summary_if_complete)
    """
    profile = get_or_create_profile(db, user_id)

    # Store raw answer
    raw = profile.onboarding_answers_raw or {}
    raw[str(step)] = answer
    profile.onboarding_answers_raw = raw

    # Parse into structured profile fields
    field = ONBOARDING_QUESTIONS[step]["field"] if step < TOTAL_STEPS else None
    if field and field in FIELD_PARSERS:
        FIELD_PARSERS[field](answer, profile)

    next_step = step + 1
    profile.onboarding_step = next_step

    if next_step >= TOTAL_STEPS:
        profile.onboarding_complete = True
        db.commit()
        summary = _build_profile_summary(profile)
        return None, True, summary

    db.commit()
    next_q = ONBOARDING_QUESTIONS[next_step]
    question_text = next_q["question"]
    if next_q.get("hint"):
        question_text += f"\n\n💡 {next_q['hint']}"
    return question_text, False, None


def build_persona_context(profile: UserProfile) -> str:
    """
    Returns a rich context string injected into every coaching system prompt.
    This is what replaces the hardcoded "Jayesh" references.
    """
    if not profile or not profile.onboarding_complete:
        return ""

    goals_text = "; ".join(
        f"{g['goal']} ({g['track']})" for g in (profile.goals_90_days or [])[:3]
    )
    values_text = ", ".join(profile.core_values[:4])
    stressors_text = ", ".join(profile.current_stressors[:3])
    relationships_text = "; ".join(
        r.get("description", "")[:80] for r in (profile.key_relationships or [])[:3]
    )

    return (
        f"USER PROFILE:\n"
        f"Name: {profile.full_name}\n"
        f"Role: {profile.role} at {profile.organization} ({profile.organization_type})\n"
        f"Biggest current challenge: {profile.biggest_challenge}\n"
        f"90-day goals: {goals_text or 'not yet set'}\n"
        f"Core values: {values_text or 'not yet captured'}\n"
        f"Current stressors: {stressors_text or 'not specified'}\n"
        f"Key relationships: {relationships_text or 'not specified'}\n"
        f"Coaching style preference: {profile.coaching_style_preference}\n"
    )
