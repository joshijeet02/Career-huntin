from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.schemas import CoachRequest, CoachResponse
from app.services.persona_policy import (
    PERSONA_POLICY_VERSION,
    build_persona_system_prompt,
    enforce_persona_policy,
)
from app.services.research_intel import latest_insights, spotlight_for_track


def _extract_int(label: str, context: str, default: int = 0) -> int:
    pattern = rf"{re.escape(label)}=(\\d+)"
    match = re.search(pattern, context)
    if not match:
        return default
    return int(match.group(1))


def _extract_text(label: str, context: str, default: str = "") -> str:
    pattern = rf"{re.escape(label)}=([^,]+)"
    match = re.search(pattern, context)
    if not match:
        return default
    return match.group(1).strip()


def _fallback_response(payload: CoachRequest) -> CoachResponse:
    load_score = _extract_int("loadScore", payload.context)
    executive_score = _extract_int("execScore", payload.context)
    relationship_score = _extract_int("relScore", payload.context)
    burnout_risk = _extract_text("burnoutRisk", payload.context, default="Moderate")
    track = payload.track.lower().strip()

    headline = "Daily coaching actions prepared"
    if load_score >= 75:
        headline = "Packed schedule detected: protect strategic attention"
    elif executive_score < 70:
        headline = "Leadership quality needs reinforcement today"

    actions: list[str] = []

    if load_score >= 75:
        actions.append("Block one 45-minute focus window and decline one low-leverage meeting.")
    else:
        actions.append("Use your largest free block for strategic review and mission execution tracking.")

    if executive_score < 70:
        actions.append("Run a 20-minute decision hygiene check: assumptions, downside, owner, deadline.")
    else:
        actions.append("Delegate one high-impact task with clear owner, quality bar, and due date.")

    if relationship_score < 65:
        actions.append("Initiate a repair-oriented conversation using soft startup and appreciation.")
    else:
        actions.append("Maintain relational trust with one specific appreciation before the day ends.")

    if burnout_risk.lower() == "high":
        actions.append("Reduce cognitive load: defer one non-essential commitment and protect recovery tonight.")

    if track == "relationship":
        actions.insert(0, "Start with a repair script: acknowledge emotion, own your part, and request a calm reset.")
    elif track == "leadership":
        actions.insert(0, "Choose one critical mission outcome and align your top two meetings to it.")

    response = CoachResponse(message=headline, suggested_actions=actions)
    spotlight = spotlight_for_track(payload.track)
    evidence = f"{spotlight.title} ({spotlight.published_date})"
    return enforce_persona_policy(payload, response, evidence)


def _extract_output_text(body: dict[str, Any]) -> str:
    text = body.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    output = body.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                value = c.get("text")
                if isinstance(value, str) and value.strip():
                    chunks.append(value.strip())
        if chunks:
            return "\n".join(chunks)
    return ""


def _parse_openai_json(text: str) -> CoachResponse | None:
    if not text.strip():
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    message = data.get("message")
    suggested_actions = data.get("suggested_actions")
    if not isinstance(message, str) or not isinstance(suggested_actions, list):
        return None
    actions = [str(item).strip() for item in suggested_actions if str(item).strip()]
    if not message.strip() or not actions:
        return None
    return CoachResponse(message=message.strip(), suggested_actions=actions[:5])


async def _openai_response(payload: CoachRequest, user_context: str = "") -> CoachResponse | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_COACH_MODEL", "gpt-4o-mini").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    evidence = latest_insights(limit=4, track=payload.track)
    evidence_lines = [
        f"- {item.title} [{item.published_date}] -> {item.takeaway}" for item in evidence
    ]
    system_prompt = build_persona_system_prompt(
        track=payload.track, evidence_lines=evidence_lines, user_context=user_context
    )
    user_prompt = (
        f"Policy version: {PERSONA_POLICY_VERSION}\\n"
        f"Context: {payload.context}\n"
        f"Goal: {payload.goal}\n"
        f"Track: {payload.track}\n"
        "Return JSON only."
    )

    body = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": 400,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{base_url}/responses", headers=headers, json=body)
            response.raise_for_status()
            text = _extract_output_text(response.json())
            parsed = _parse_openai_json(text)
            if parsed is None:
                return None
            spotlight = spotlight_for_track(payload.track)
            evidence_spotlight = f"{spotlight.title} ({spotlight.published_date})"
            return enforce_persona_policy(payload, parsed, evidence_spotlight)
    except Exception:
        return None


async def generate_coach_response(payload: CoachRequest, user_context: str = "") -> CoachResponse:
    remote = await _openai_response(payload, user_context=user_context)
    if remote is not None:
        return remote
    return _fallback_response(payload)
