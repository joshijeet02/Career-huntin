"""
The First Read
==============
This is the highest-leverage retention feature in the product.

In traditional executive coaching, the intake session is where the coach
listens to everything — not just the answers, but what the answers reveal.
The client describes their goals. The coach hears their relationship with ambition.
The client names their stressors. The coach sees their relationship with control.
The client lists their values. The coach notices which ones cost them something.

Then the coach writes a synthesis. Not a summary of what was said —
a reading of who the person is. Specific enough to be uncomfortable.
Accurate enough to feel like the coach has known them for years.

This is the moment a client becomes a long-term client.
"I have talked to a lot of coaches. This person sees something in me
that I haven't been able to articulate myself."

The First Read is generated once, immediately after onboarding is complete.
It is the first thing the user sees in their morning brief on day one.
It is the benchmark against which the user measures all future coaching.
If it is good — and it must be good — they will not leave.

Six sections, written in direct coach voice, no bullet points:

  1. OPENING OBSERVATION
     One or two sentences. Who is this person really?
     Not their title. Who are they under pressure?

  2. THE STRENGTH YOU MAY BE UNDERVALUING
     Something they showed in their answers they may not fully see or credit.
     Specific to what they said — not generic.

  3. THE LIKELY BLIND SPOT
     What gets in the way for people who think and operate exactly like this.
     Honest. Not harsh. Not prescriptive. A hypothesis for them to sit with.

  4. THE RELATIONSHIP PATTERN
     What their key relationships reveal about how they relate to people.
     What does a coach notice that the person themselves might not?

  5. THE ONE SENTENCE
     The single most telling thing they said in the entire intake.
     Quoted. Then interpreted. This is what the coach will carry forward.

  6. WHAT YOUR COACH INTENDS
     How the coaching will be structured for this person specifically.
     Not generic. Based on exactly who they are and what they need.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models import FirstRead, UserProfile


# ── OpenAI call (same pattern as coach.py) ────────────────────────────────────

async def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int = 900) -> str | None:
    """Generic OpenAI call returning raw text."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_COACH_MODEL", "gpt-4o-mini").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    body = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{base_url}/responses", headers=headers, json=body)
            resp.raise_for_status()
            body_data = resp.json()

            # Extract text from Responses API format
            output = body_data.get("output", [])
            if isinstance(output, list):
                for item in output:
                    content = item.get("content", [])
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("text", "").strip():
                                return c["text"].strip()
            text = body_data.get("output_text", "")
            return text.strip() if text else None
    except Exception:
        return None


# ── Fallback First Read (no OpenAI) ──────────────────────────────────────────

def _build_fallback_first_read(profile: UserProfile) -> dict:
    """
    A non-trivial fallback when OpenAI is unavailable.
    Uses onboarding data directly to produce a structured read.
    Lower quality than GPT, but still personal and specific.
    """
    name = profile.full_name.split()[0] if profile.full_name else "friend"
    role = profile.role or "leader"
    org = profile.organization or "your organisation"
    challenge = profile.biggest_challenge or ""
    values = profile.core_values or []
    goals = profile.goals_90_days or []
    stressors = profile.current_stressors or []
    relationships = profile.key_relationships or []
    style = profile.coaching_style_preference or "direct"

    # Section 1: Opening Observation
    opening = (
        f"{name} is someone who holds themselves to a standard most people around them "
        f"cannot fully see. As {role} at {org}, the external markers of success are present — "
        f"but your coach's first read is that the internal conversation is more demanding "
        f"than anything the outside world asks of you. "
        f"You came to coaching not because things are falling apart. "
        f"You came because you know something more is possible, and you want someone to "
        f"help you get there without losing what matters most in the process."
    )

    # Section 2: Undervalued Strength
    strength = ""
    if values:
        top_value = values[0] if isinstance(values[0], str) else str(values[0])
        strength = (
            f"You named '{top_value}' as a core value. "
            f"Your coach's observation: people who name values like this in an intake interview "
            f"are not describing aspirations — they are describing load-bearing walls. "
            f"This value is already operating in you. "
            f"The question is whether you are consciously building on it, "
            f"or unconsciously defending it from a world that sometimes asks you to compromise it. "
            f"That distinction is worth exploring."
        )
    else:
        strength = (
            f"The way you described your goals — specific, time-bound, aware of the stakes — "
            f"tells your coach something important: you already think like a high-performer. "
            f"The work ahead is not about installing new capabilities. "
            f"It is about removing what is blocking the ones you already have."
        )

    # Section 3: Blind Spot
    blind_spot = ""
    if challenge:
        blind_spot = (
            f"You named your biggest challenge as: '{challenge[:120]}'. "
            f"Your coach's hypothesis — offered gently, as something to sit with rather than accept: "
            f"the challenge you described may be the symptom. "
            f"The people your coach works with who describe challenges like this "
            f"are often navigating something underneath it — a belief about what they owe people, "
            f"or what it means to ask for help, or what happens if they slow down. "
            f"Your coach will be looking for that underneath layer. "
            f"Not to challenge you — to help you see it before it costs you something."
        )
    elif stressors:
        stressor = stressors[0] if isinstance(stressors[0], str) else str(stressors[0])
        blind_spot = (
            f"You listed '{stressor}' among your current stressors. "
            f"Your coach notices: the leaders who name this particular stressor "
            f"are often the ones who are most reluctant to let anyone else carry any of the weight. "
            f"The blind spot, typically, is not a lack of capability — "
            f"it is an unwillingness to be seen as needing support. "
            f"Something to watch for."
        )
    else:
        blind_spot = (
            f"Your coach's honest first impression: you are someone who processes quickly, "
            f"decides fast, and moves on. "
            f"The blind spot that sometimes comes with that pattern "
            f"is underestimating how long other people need to catch up — "
            f"and inadvertently leaving your most important relationships slightly behind. "
            f"Watch for it."
        )

    # Section 4: Relationship Pattern
    rel_pattern = ""
    if relationships:
        rel_names = [
            r.get("name", r) if isinstance(r, dict) else str(r)
            for r in relationships[:3]
        ]
        rel_pattern = (
            f"You named {', '.join(rel_names)} as key relationships. "
            f"Your coach's observation: the relationships you named are all relationships "
            f"where you carry significant responsibility — for outcomes, for other people, "
            f"for what happens next. "
            f"This is not unusual for leaders at your level. "
            f"But your coach will be watching for one thing: "
            f"is there anyone in your life who holds space for you, "
            f"the way you hold space for the people you named? "
            f"If not — that is a gap worth addressing."
        )
    else:
        rel_pattern = (
            f"Your coach noticed that when asked about key relationships, "
            f"you led with the professional context before the personal. "
            f"This is not a criticism — it is a data point. "
            f"The leaders who sustain high performance over decades "
            f"have deep investments in relationships outside their professional identity. "
            f"Your coach will ask about this over time."
        )

    # Section 5: The One Sentence
    one_sentence_raw = challenge or (goals[0] if goals else "") or (stressors[0] if stressors else "")
    if isinstance(one_sentence_raw, dict):
        one_sentence_raw = str(one_sentence_raw)
    one_sentence = (
        f"The most telling thing you shared in this intake: \"{one_sentence_raw[:100]}...\"\n\n"
        f"Here is what your coach hears in that. "
        f"Not the surface meaning — the deeper one. "
        f"You are not describing a problem to be solved. "
        f"You are describing a tension you have been living with for a while. "
        f"Something between who you are and who the situation seems to require you to be. "
        f"That tension is not a sign of failure. "
        f"In your coach's experience, it is almost always the engine of the most important growth. "
        f"We are going to work with it — not around it."
    ) if one_sentence_raw else (
        f"Something your coach noticed: you answered every question precisely and thoughtfully. "
        f"Not a word wasted. "
        f"Your coach's read: you have been thinking about these things for a long time. "
        f"You did not need prompting. You needed a place to put it. "
        f"That is what this coaching relationship is for."
    )

    # Section 6: Coach Intention
    style_note = "direct and clear" if style == "direct" else "warm and exploratory"
    intention = (
        f"Here is how your coach intends to work with you, specifically.\n\n"
        f"You prefer coaching that is {style_note} — and your coach will honour that. "
        f"But 'direct' does not mean comfortable. "
        f"Your coach's job is not to make you feel good. "
        f"It is to make you grow. Sometimes those are the same thing. Sometimes they are not.\n\n"
        f"The focus for the first 30 days: "
        f"{'establishing the daily check-in ritual and building the data foundation, ' if not goals else f'your goals around {goals[0][:60] if isinstance(goals[0], str) else str(goals[0])[:60]}, '}"
        f"while building the habit of honest self-assessment. "
        f"Your coach will not let you drift. "
        f"You made commitments today. "
        f"Your coach will be asking about them."
    )

    # Assemble full text
    section_divider = "\n\n" + "─" * 40 + "\n\n"
    full_text = section_divider.join([
        f"YOUR COACH'S FIRST READ\n{'═' * 40}\n\nFor: {profile.full_name}\n",
        f"WHO YOU ARE UNDER PRESSURE\n\n{opening}",
        f"THE STRENGTH YOU MAY BE UNDERVALUING\n\n{strength}",
        f"THE LIKELY BLIND SPOT\n\n{blind_spot}",
        f"THE RELATIONSHIP PATTERN\n\n{rel_pattern}",
        f"THE ONE THING THAT STOOD OUT\n\n{one_sentence}",
        f"WHAT YOUR COACH INTENDS\n\n{intention}",
    ])

    return {
        "full_text": full_text,
        "opening_observation": opening,
        "undervalued_strength": strength,
        "blind_spot": blind_spot,
        "relationship_pattern": rel_pattern,
        "one_sentence": one_sentence,
        "coach_intention": intention,
        "model_used": "fallback",
    }


# ── OpenAI-powered First Read ─────────────────────────────────────────────────

async def _generate_openai_first_read(profile: UserProfile) -> dict | None:
    """Use GPT to generate the First Read from onboarding data."""

    # Build rich intake summary for the prompt
    values_str = ", ".join(
        v if isinstance(v, str) else str(v) for v in (profile.core_values or [])
    )
    goals_str = "\n".join(
        f"  - {g if isinstance(g, str) else str(g)}"
        for g in (profile.goals_90_days or [])
    )
    stressors_str = ", ".join(
        s if isinstance(s, str) else str(s) for s in (profile.current_stressors or [])
    )
    rels_str = "\n".join(
        f"  - {r.get('name', r) if isinstance(r, dict) else r}: "
        f"{r.get('relationship', r.get('role', '')) if isinstance(r, dict) else ''}"
        for r in (profile.key_relationships or [])[:5]
    )

    system_prompt = """You are an elite executive coach conducting a "First Read" on a new client.
This is the most important document you will ever write for this person.

STEP 1 — THINK FIRST (Chain of Thought):
Before writing a single word of the First Read, first output a <thought_process> section.
In this section (which will be stripped and never shown to the user), reason out loud:
  - What is the deepest sub-text beneath their stated challenge? What are they NOT saying?
  - What pattern do you see across their values, stressors, and relationships?
  - What is surprisingly specific about this person — something that would not apply to 90% of clients?
  - What is the ONE most telling sentence they wrote? Why?
  - What is the coaching hypothesis you are walking in with?

STEP 2 — WRITE THE FIRST READ:
After the </thought_process> tag, write the six sections of the First Read.

PERSONA AND VOICE RULES:
- NEVER say "I understand," "I hear you," "That makes sense," or any filler phrase.
- NEVER use words: navigate, foster, delve, holistic, empower, journey, space (as in "hold space").
- NEVER be generic. If you write a sentence that could apply to any client, delete it.
- NEVER use bullet points. Write in flowing prose paragraphs only.
- Tone: warm but penetrating. Like a coach who genuinely sees them — perhaps more clearly than they see themselves.
- Be uncomfortably specific. Reference their exact words. Every section should feel personally written.

THE SIX SECTIONS (after </thought_process>):

SECTION 1 — WHO YOU ARE UNDER PRESSURE
Two to three sentences. Not their title. Who are they really, when things are hard?

SECTION 2 — THE STRENGTH YOU MAY BE UNDERVALUING
Something they showed in their answers that they may not fully see or credit.
Reference something specific they said. Not generic strengths.

SECTION 3 — THE LIKELY BLIND SPOT
What gets in the way for people who think and operate exactly like this person?
Honest. Not harsh. A hypothesis for them to sit with. One clear pattern.

SECTION 4 — THE RELATIONSHIP PATTERN
What do their described key relationships reveal about how they relate to people?
What does a coach notice that the person themselves might not see?

SECTION 5 — THE ONE THING THAT STOOD OUT
The single most telling thing they said in the intake. Quote it or paraphrase closely.
Then interpret it — not the surface meaning, the deeper one.

SECTION 6 — WHAT YOUR COACH INTENDS
How this coaching will be structured specifically for this person.
Not generic. Based on exactly who they are, their style preference, their goals.
End with a line about accountability.

RULES:
- Each section: 3-5 sentences.
- Total prose (excluding <thought_process>): 450-550 words.
- Start each section with the section header in ALL CAPS on its own line.
"""

    user_prompt = f"""CLIENT INTAKE DATA:

Name: {profile.full_name}
Role: {profile.role}
Organisation: {profile.organization} ({profile.organization_type})
Coaching style preference: {profile.coaching_style_preference}

Biggest challenge they named:
{profile.biggest_challenge}

90-day goals:
{goals_str or '(none specified)'}

Core values they named:
{values_str or '(none specified)'}

Current stressors:
{stressors_str or '(none specified)'}

Key relationships:
{rels_str or '(none specified)'}

Raw onboarding answers (additional context):
{str(profile.onboarding_answers_raw or {})[:800]}

First, output your <thought_process>...</thought_process>.
Then write the six-section First Read."""

    raw = await _call_openai(system_prompt, user_prompt, max_tokens=1200)
    if not raw:
        return None

    # Strip the invisible chain-of-thought block — never shown to the user
    import re as _re
    raw = _re.sub(r"<thought_process>.*?</thought_process>", "", raw, flags=_re.DOTALL).strip()

    # Parse sections from the raw text
    sections = {
        "opening_observation": "",
        "undervalued_strength": "",
        "blind_spot": "",
        "relationship_pattern": "",
        "one_sentence": "",
        "coach_intention": "",
    }

    section_map = {
        "WHO YOU ARE UNDER PRESSURE": "opening_observation",
        "THE STRENGTH YOU MAY BE UNDERVALUING": "undervalued_strength",
        "THE LIKELY BLIND SPOT": "blind_spot",
        "THE RELATIONSHIP PATTERN": "relationship_pattern",
        "THE ONE THING THAT STOOD OUT": "one_sentence",
        "WHAT YOUR COACH INTENDS": "coach_intention",
    }

    current_key = None
    current_lines: list[str] = []

    for line in raw.split("\n"):
        matched = False
        for header, key in section_map.items():
            if header in line.upper():
                if current_key and current_lines:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = []
                matched = True
                break
        if not matched and current_key is not None:
            current_lines.append(line)

    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    divider = "\n\n" + "─" * 40 + "\n\n"
    full_text = (
        f"YOUR COACH'S FIRST READ\n{'═' * 40}\n\nFor: {profile.full_name}\n"
        + divider + raw
    )

    return {
        "full_text": full_text,
        "model_used": os.getenv("OPENAI_COACH_MODEL", "gpt-4o-mini"),
        **sections,
    }


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_first_read(db: Session, user_id: str) -> dict:
    """
    Generate (or retrieve existing) First Read for a user.
    Called automatically after onboarding completes.
    Safe to call multiple times — returns cached version if exists.
    """
    existing = db.query(FirstRead).filter_by(user_id=user_id).first()
    if existing:
        return {
            "user_id": user_id,
            "generated_at": existing.generated_at,
            "full_text": existing.full_text,
            "opening_observation": existing.opening_observation,
            "undervalued_strength": existing.undervalued_strength,
            "blind_spot": existing.blind_spot,
            "relationship_pattern": existing.relationship_pattern,
            "one_sentence": existing.one_sentence,
            "coach_intention": existing.coach_intention,
            "model_used": existing.model_used,
            "delivered": existing.delivered,
            "cached": True,
        }

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile or not profile.onboarding_complete:
        return {"error": "Onboarding not complete — First Read requires full onboarding."}

    # Try OpenAI first, fall back to structured fallback
    result = await _generate_openai_first_read(profile)
    if result is None:
        result = _build_fallback_first_read(profile)

    # Persist
    fr = FirstRead(
        user_id=user_id,
        generated_at=datetime.utcnow().isoformat(),
        full_text=result["full_text"],
        opening_observation=result.get("opening_observation", ""),
        undervalued_strength=result.get("undervalued_strength", ""),
        blind_spot=result.get("blind_spot", ""),
        relationship_pattern=result.get("relationship_pattern", ""),
        one_sentence=result.get("one_sentence", ""),
        coach_intention=result.get("coach_intention", ""),
        model_used=result.get("model_used", "fallback"),
        delivered=False,
    )
    db.add(fr)
    db.commit()
    db.refresh(fr)

    return {
        "user_id": user_id,
        "generated_at": fr.generated_at,
        "full_text": fr.full_text,
        "opening_observation": fr.opening_observation,
        "undervalued_strength": fr.undervalued_strength,
        "blind_spot": fr.blind_spot,
        "relationship_pattern": fr.relationship_pattern,
        "one_sentence": fr.one_sentence,
        "coach_intention": fr.coach_intention,
        "model_used": fr.model_used,
        "delivered": fr.delivered,
        "cached": False,
    }


def mark_first_read_delivered(db: Session, user_id: str) -> None:
    """Called after the First Read is surfaced to the user."""
    fr = db.query(FirstRead).filter_by(user_id=user_id).first()
    if fr and not fr.delivered:
        fr.delivered = True
        db.commit()
