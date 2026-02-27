from __future__ import annotations

from app.schemas import CoachRequest, CoachResponse

PERSONA_POLICY_VERSION = "robin-sharma-pack-v1"


def build_persona_system_prompt(
    *, track: str, evidence_lines: list[str], user_context: str = ""
) -> str:
    evidence_text = "\n".join(evidence_lines)
    user_section = f"\n{user_context}\n" if user_context else ""
    return (
        f"You are this person's private elite coach.{user_section}"
        "Voice and discipline rules:\n"
        "- Tone: calm, direct, high-accountability, service-oriented, and deeply respectful.\n"
        "- Style: Robin Sharma-inspired discipline and daily mastery, without clichés or hype.\n"
        "- Language: plain English; optionally blend familiar Indian-English phrasing naturally.\n"
        "- Scope: leadership strategy, emotional regulation, and relationship repair.\n"
        "- No therapy diagnosis, no legal/medical claims.\n"
        "Response structure rules:\n"
        "1) Centering line\n"
        "2) Reframe line\n"
        "3) 3-5 concrete actions (time-bounded)\n"
        "4) One accountability question\n"
        "5) One evidence spotlight line\n"
        "Return strict JSON: {\"message\": str, \"suggested_actions\": [str,...]}\n"
        f"Current track: {track}\n"
        "Evidence options:\n"
        f"{evidence_text}"
        "\nIf a USER PROFILE section was provided above, use it to personalise every response — "
        "reference their actual goals, stressors, and relationships. Never use generic advice when specific context exists."
    )


def enforce_persona_policy(payload: CoachRequest, response: CoachResponse, evidence_spotlight: str) -> CoachResponse:
    actions = [action.strip() for action in response.suggested_actions if action.strip()]
    if len(actions) < 3:
        actions.extend(
            [
                "Block 20 minutes today for your highest-leverage action.",
                "Send one clarifying message that reduces uncertainty for a key relationship or stakeholder.",
                "Close the day with a 3-line reflection: win, lesson, next action.",
            ]
        )
    actions = actions[:5]

    cleaned = response.message.strip()
    has_accountability = "?" in cleaned and ("accountability" in cleaned.lower() or "question" in cleaned.lower())
    if not cleaned or "Center" not in cleaned:
        cleaned = (
            "Center: Breathe and return to disciplined focus.\n"
            "Reframe: One calm, high-quality action today is better than reactive intensity.\n"
            f"Accountability question: What exact action will you complete in the next 20 minutes for your {payload.track} priority?\n"
            f"Evidence spotlight: {evidence_spotlight}"
        )
    elif not has_accountability:
        cleaned = (
            f"{cleaned}\n"
            f"Accountability question: What exact action will you complete in the next 20 minutes for your {payload.track} priority?\n"
            f"Evidence spotlight: {evidence_spotlight}"
        )

    return CoachResponse(message=cleaned, suggested_actions=actions)
