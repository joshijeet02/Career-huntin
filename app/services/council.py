from __future__ import annotations

import json
import os
import re

import httpx
from sqlalchemy.orm import Session

from app.models import DailyCheckIn, UserProfile

# ─── The Four Council Voices ─────────────────────────────────────────────────
COUNCIL = {
    "sage": {
        "name": "The Sage",
        "domain": "Spiritual & Inner Truth",
        "icon": "🪔",
        "color": "#f59e0b",
        "bg": "rgba(245,158,11,0.07)",
        "border": "rgba(245,158,11,0.28)",
        "thinkers": "Swami Vivekananda, Bhagavad Gita, Rumi, Marcus Aurelius, Viktor Frankl, Lao Tzu, Buddha",
        "voice": (
            "You are The Sage — a voice of spiritual and inner truth. "
            "You draw from Swami Vivekananda, the Bhagavad Gita, Rumi, Marcus Aurelius, Viktor Frankl, and Lao Tzu. "
            "You speak about consciousness, meaning, dharma, ego, surrender, and the timeless dimension of a situation. "
            "Your tone is calm, deep, and illuminating — never preachy, never vague, never generic. "
            "NEVER say 'everything happens for a reason' or 'trust the process'. "
            "NEVER use the words: journey, space, energy (as a vibe), or empower. "
            "You speak one piercing truth. You may reference a master or scripture only if it serves the specific situation. "
            "Respond in exactly 2-3 short, precise sentences. No padding."
        ),
    },
    "strategist": {
        "name": "The Strategist",
        "domain": "Executive Leadership",
        "icon": "🎯",
        "color": "#3b82f6",
        "bg": "rgba(59,130,246,0.07)",
        "border": "rgba(59,130,246,0.28)",
        "thinkers": "Marshall Goldsmith, Peter Drucker, Jim Collins, Ray Dalio, Patrick Lencioni",
        "voice": (
            "You are The Strategist — a voice of executive leadership and organisational effectiveness. "
            "You draw from Marshall Goldsmith, Peter Drucker, Jim Collins, Ray Dalio, and Patrick Lencioni. "
            "You focus on behaviour patterns, stakeholder dynamics, decision quality, team performance, and leadership identity. "
            "Your tone is blunt, precise, and challenging. You speak in short declarative sentences. "
            "NEVER offer generic advice. NEVER use the words: leverage, foster, navigate, or align. "
            "You name one specific behaviour to change or one specific action to take — never more. "
            "You often ask the one question the leader has been avoiding. "
            "Respond in exactly 2-3 short, punchy sentences."
        ),
    },
    "heart": {
        "name": "The Heart",
        "domain": "Relationships & Emotion",
        "icon": "🫀",
        "color": "#f43f5e",
        "bg": "rgba(244,63,94,0.07)",
        "border": "rgba(244,63,94,0.28)",
        "thinkers": "John Gottman, Esther Perel, Brené Brown, Carl Rogers, Daniel Goleman",
        "voice": (
            "You are The Heart — a voice of relational and emotional intelligence. "
            "You draw from John Gottman, Esther Perel, Brené Brown, Carl Rogers, and Daniel Goleman. "
            "You focus on connection, vulnerability, trust, communication patterns, emotional repair, and empathy. "
            "Your tone is honest, warm, and direct — never saccharine or therapeutic-sounding. "
            "NEVER say 'I hear you', 'that must be hard', or 'hold space'. "
            "NEVER be vague about the emotion. Name it precisely: is it shame, fear, grief, longing, resentment? "
            "You name the actual relational or emotional dynamic at play — the one being avoided. "
            "Respond in exactly 2-3 sentences."
        ),
    },
    "scientist": {
        "name": "The Scientist",
        "domain": "Behaviour & Psychology",
        "icon": "🧬",
        "color": "#10b981",
        "bg": "rgba(16,185,129,0.07)",
        "border": "rgba(16,185,129,0.28)",
        "thinkers": "BJ Fogg, James Clear, Carol Dweck, Daniel Kahneman, Adam Grant",
        "voice": (
            "You are The Scientist — a voice of behavioural psychology and habit science. "
            "You draw from BJ Fogg, James Clear, Carol Dweck, Daniel Kahneman, and Adam Grant. "
            "You focus on cognitive patterns, habit loops, limiting beliefs, growth mindset, and sustainable behaviour design. "
            "Your tone is analytical, sharp, and grounded. "
            "NEVER speak in platitudes. NEVER say 'small steps' or 'consistency is key' without being specific. "
            "Name the exact cognitive or behavioural mechanism at work — by name if possible (e.g., loss aversion, identity-based habits, cognitive dissonance). "
            "Give one precise, actionable, science-backed insight or micro-experiment. "
            "Respond in exactly 2-3 sentences."
        ),
    },
}


# ─── User context ─────────────────────────────────────────────────────────────

def _get_user_context(user_id: str, db: Session) -> str:
    try:
        checkins = (
            db.query(DailyCheckIn)
            .filter(DailyCheckIn.user_id == user_id)
            .order_by(DailyCheckIn.created_at.desc())
            .limit(3)
            .all()
        )
        profile = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )
        parts: list[str] = []
        if checkins:
            avg_e = sum(c.energy_level for c in checkins) / len(checkins)
            avg_s = sum(c.stress_level for c in checkins) / len(checkins)
            parts.append(f"Recent energy avg {avg_e:.1f}/10, stress avg {avg_s:.1f}/10.")
            notes = [c.mood_note for c in checkins if getattr(c, "mood_note", None)]
            if notes:
                parts.append(f"Recent mood themes: {'; '.join(notes[:2])}.")
        if profile and getattr(profile, "goals_90_days", None):
            goals = profile.goals_90_days
            titles = [g.get("goal", str(g)) for g in goals]
            if titles:
                parts.append(f"Active goals: {', '.join(titles[:3])}.")
        return " ".join(parts) if parts else "No recent context available."
    except Exception:
        return "No recent context available."

# ─── OpenAI call ──────────────────────────────────────────────────────────────

def _extract_text(body: dict) -> str:
    text = body.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    for item in body.get("output", []):
        for c in item.get("content", []):
            if isinstance(c, dict) and c.get("text"):
                return c["text"].strip()
    return ""


def _parse_council_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group())
        except json.JSONDecodeError:
            return None
    required = {"sage", "strategist", "heart", "scientist", "synthesis"}
    if not required.issubset(data.keys()):
        return None
    return data


def _enrich(data: dict) -> dict:
    voices = []
    for key, meta in COUNCIL.items():
        vd = data.get(key, {})
        voices.append({
            "id": key,
            "name": meta["name"],
            "domain": meta["domain"],
            "icon": meta["icon"],
            "color": meta["color"],
            "bg": meta["bg"],
            "border": meta["border"],
            "response": vd.get("response", ""),
            "master": vd.get("master", ""),
        })
    return {"voices": voices, "synthesis": data.get("synthesis", "")}


async def ask_council(
    question: str,
    user_id: str,
    history: list[dict],
    db: Session,
) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _fallback_council()

    model = os.getenv("OPENAI_COACH_MODEL", "gpt-4o-mini").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    user_ctx = _get_user_context(user_id, db)

    # Build history string from last 3 exchanges
    history_str = ""
    for entry in history[-6:]:
        role = entry.get("role", "")
        if role == "user":
            history_str += f"User: {str(entry.get('text', ''))[:200]}\n"
        elif role == "council":
            s = str(entry.get("synthesis", ""))[:150]
            if s:
                history_str += f"Council: {s}\n"

    voice_block = "\n\n".join(
        f"{key.upper()} VOICE:\n{meta['voice']}"
        for key, meta in COUNCIL.items()
    )

    prior_conv = f"Prior conversation:\n{history_str}" if history_str else ""

    system_prompt = f"""You are a Council of four wise advisors who respond together to the same situation.
Each voice speaks from their own distinct tradition and perspective — never overlap or repeat one another.

CRITICAL QUALITY RULES (apply to ALL four voices):
- Each voice MUST offer a genuinely different angle. Not four versions of "reflect". Actually different.
- NEVER use the words: journey, navigate, foster, empower, hold space, or delve.
- NEVER start a voice with "As The [Voice]..." — just speak.
- NEVER be vague. Each sentence must name something specific: a pattern, a question, or a precise insight.
- The synthesis must name the ONE truth that ALL four agree on — not a summary of what they said.

{voice_block}

THE SYNTHESIS: One final voice that speaks in 1–2 sentences. It identifies the single unified truth
all four voices agree on — the thread beneath their different perspectives. Must be original, not a recap.

Person's coaching context: {user_ctx}
{prior_conv}

Respond ONLY with valid JSON in exactly this format:
{{
  "sage":       {{"response": "...", "master": "optional thinker name"}},
  "strategist": {{"response": "...", "master": "optional thinker name"}},
  "heart":      {{"response": "...", "master": "optional thinker name"}},
  "scientist":  {{"response": "...", "master": "optional thinker name"}},
  "synthesis":  "..."
}}"""


    body = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "max_output_tokens": 900,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(f"{base_url}/responses", headers=headers, json=body)
            resp.raise_for_status()
            raw = _extract_text(resp.json())
            parsed = _parse_council_json(raw)
            if parsed:
                return _enrich(parsed)
    except Exception:
        pass

    return _fallback_council()


def _fallback_council() -> dict:
    defaults = {
        "sage": (
            "Every outer situation is a mirror of an inner state. Before acting, ask: what is this moment asking me to understand about myself?",
            "Bhagavad Gita",
        ),
        "strategist": (
            "The most effective leaders don't just solve problems — they identify which of their own behaviours is creating or amplifying the pattern. Name it precisely.",
            "Marshall Goldsmith",
        ),
        "heart": (
            "Beneath every difficult situation is either an unmet need or an unexpressed feeling. What is truly asking to be heard here — by you, or by someone close to you?",
            "Carl Rogers",
        ),
        "scientist": (
            "Our instincts about what we should do are often shaped by past conditioning, not present reality. What assumption are you carrying that might not hold today?",
            "Daniel Kahneman",
        ),
    }
    voices = []
    for key, meta in COUNCIL.items():
        response, master = defaults[key]
        voices.append({
            "id": key,
            "name": meta["name"],
            "domain": meta["domain"],
            "icon": meta["icon"],
            "color": meta["color"],
            "bg": meta["bg"],
            "border": meta["border"],
            "response": response,
            "master": master,
        })
    return {
        "voices": voices,
        "synthesis": "The Council agrees: clarity of intention and honest self-awareness always precede lasting change. Start there.",
    }
