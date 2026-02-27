"""
Conflict Preparation Script Generator
========================================
Before a hard conversation, a great coach sits with the client and prepares them.
Not just "what to say" — but the mindset, the opening line, the key points,
what NOT to say, how to close, and the one calm anchor thought to carry in.

The types of hard conversations this handles:
  - Difficult feedback (to a team member, a board member, a direct report)
  - Negotiation (salary, partnership terms, vendor contracts)
  - Conflict repair (with a partner, colleague, or family member)
  - Performance conversation (putting someone on notice)
  - Boundary setting (pushing back on a boss or parent or investor)
  - Apology (when the user needs to own something)

Research basis:
  - Crucial Conversations framework (VitalSmarts)
  - Gottman's repair attempt research
  - ICF (International Coach Federation) conversation structure
  - Chris Voss negotiation principles (Never Split the Difference)
  - Marshall Rosenberg's Nonviolent Communication (NVC) framework
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ConflictPrep, UserProfile


_CONVERSATION_TYPES = {
    "feedback": {
        "opening_template": "I want to share something with you because I respect you and care about your success.",
        "framework": "Situation → Behaviour → Impact → Future request",
        "what_not_to_say": [
            "\"You always...\" or \"You never...\" (overgeneralisation)",
            "\"I'm just being honest\" (used to justify harshness)",
            "\"Other people think...\" (triangulating)",
            "Anything said while emotionally dysregulated — wait 20 minutes first",
        ],
        "closing_template": "What I am asking for going forward is [specific behaviour]. Can we agree on that?",
    },
    "negotiation": {
        "opening_template": "I value our relationship, and I want to find something that works for both of us.",
        "framework": "Anchor high → Listen for the 'no' → Mirror and label → Make the other side feel heard before asking",
        "what_not_to_say": [
            "Your first number (let them go first if possible)",
            "\"That's my final offer\" unless it truly is",
            "Anything that sounds like desperation — they will sense it",
            "\"To be honest...\" signals that you haven't been honest before",
        ],
        "closing_template": "Let's agree on this: [specific terms]. I want to shake hands on something today.",
    },
    "repair": {
        "opening_template": "I've been thinking about us, and there's something I need to say.",
        "framework": "Own → Express → Request → Commit (Gottman Repair Sequence)",
        "what_not_to_say": [
            "\"I'm sorry you feel that way\" (invalidating non-apology)",
            "\"But you also...\" (counterattack disguised as repair)",
            "Bringing up past grievances during a repair attempt",
            "Apologising to end the argument rather than to reconnect",
        ],
        "closing_template": "I'm committed to [specific change]. What would help you feel that I mean it?",
    },
    "performance": {
        "opening_template": "I need to have an honest conversation with you about your performance, and I respect you too much not to.",
        "framework": "Facts → Impact on team/business → Your expectation → The consequence if unchanged → How I will support you",
        "what_not_to_say": [
            "Sugarcoating the core message — it must be clear",
            "Making it about personality: \"You're not a fit\" vs. \"These specific behaviours need to change\"",
            "Leaving without agreement on what changes and by when",
            "This conversation without documentation of previous feedback",
        ],
        "closing_template": "What I need from you by [specific date] is [specific observable change]. Can you commit to that?",
    },
    "boundary": {
        "opening_template": "I want to be straight with you about something, because I value this relationship.",
        "framework": "State the boundary clearly → State why it matters to you → State what you will do if it is not respected (not a threat — a fact)",
        "what_not_to_say": [
            "Apologising for the boundary itself",
            "Over-explaining or justifying — one clear reason is enough",
            "\"I'll try\" — either the boundary stands or it doesn't",
            "Making it about them: frame it as what you need, not what they are doing wrong",
        ],
        "closing_template": "This is what I need going forward. I'm not asking you to agree — I'm telling you what I need.",
    },
    "apology": {
        "opening_template": "I owe you an apology, and I want to do it properly.",
        "framework": "Name exactly what you did → Acknowledge its impact → Take full responsibility → Make a specific commitment to change",
        "what_not_to_say": [
            "\"I'm sorry, but...\" — the 'but' erases everything before it",
            "Defending your intention: your intent doesn't determine their experience",
            "Vague apologies: \"I'm sorry if I upset you\" (transfers responsibility)",
            "Asking for forgiveness in the same breath — give them time",
        ],
        "closing_template": "What I am committing to is [specific behaviour change]. I don't expect immediate forgiveness. I expect to earn it.",
    },
}


def generate_conflict_prep(
    db: Session,
    user_id: str,
    conversation_type: str,
    other_person: str,
    relationship_to_user: str,
    situation_description: str,
    desired_outcome: str,
    user_fear: str,
) -> dict:
    """
    Generates a full conversation preparation script.
    Saves it to ConflictPrep for reference before the conversation.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    name = profile.full_name.split()[0] if profile and profile.full_name else "friend"

    conv_type = conversation_type.lower()
    framework = _CONVERSATION_TYPES.get(conv_type, _CONVERSATION_TYPES["feedback"])

    opening = framework["opening_template"]
    key_points = [
        f"Open with: \"{opening}\"",
        f"State clearly what you observed or what you need — no ambiguity",
        f"Use the {framework['framework']} structure to guide the conversation",
        f"Name your desired outcome before you begin: \"{desired_outcome[:100]}\"",
        f"Close with: \"{framework['closing_template']}\"",
    ]

    # Personalise to the situation
    situation_lower = situation_description.lower()
    mindset_anchor = _select_mindset_anchor(conv_type, user_fear, relationship_to_user)

    full_script = f"""CONVERSATION PREPARATION SCRIPT
================================
Name: {name}  |  With: {other_person} ({relationship_to_user})
Type: {conversation_type.replace('_', ' ').title()}
Date: {date.today().strftime('%B %d, %Y')}

BEFORE YOU WALK IN
------------------
{mindset_anchor}

YOUR OPENING LINE
-----------------
"{opening}"

THE STRUCTURE ({framework['framework']})
{'-' * (len(framework['framework']) + 16)}
1. {key_points[0]}
2. {key_points[1]}
3. {key_points[2]}

YOUR DESIRED OUTCOME (say this to yourself before you enter)
-------------------------------------------------------------
"{desired_outcome}"

WHAT NOT TO SAY
---------------
{chr(10).join(f'  - {w}' for w in framework['what_not_to_say'])}

YOUR CLOSING LINE
-----------------
"{framework['closing_template']}"

YOUR FEAR VS. THE TRUTH
------------------------
You fear: "{user_fear}"
The truth: Hard conversations that are avoided always grow larger.
           The version of you that walks into this conversation is stronger than the one who doesn't.

REMEMBER
--------
The goal is not to win the conversation.
The goal is to be clear, respectful, and to create the conditions for the outcome you named above.
You have prepared. You are ready. Go.
"""

    entry = ConflictPrep(
        user_id=user_id,
        prep_date=date.today().strftime("%Y-%m-%d"),
        conversation_type=conv_type,
        other_person=other_person,
        relationship_to_user=relationship_to_user,
        situation_description=situation_description,
        user_desired_outcome=desired_outcome,
        user_fear=user_fear,
        coach_opening_line=opening,
        coach_key_points=key_points,
        coach_what_not_to_say=framework["what_not_to_say"],
        coach_closing_move=framework["closing_template"],
        coach_mindset_anchor=mindset_anchor,
        full_prep_script=full_script,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "prep_id": entry.id,
        "full_prep_script": full_script,
        "opening_line": opening,
        "key_points": key_points,
        "what_not_to_say": framework["what_not_to_say"],
        "closing_line": framework["closing_template"],
        "mindset_anchor": mindset_anchor,
        "framework": framework["framework"],
    }


def _select_mindset_anchor(conv_type: str, user_fear: str, relationship: str) -> str:
    """Select the most relevant calming anchor based on conversation type and fear."""
    if "fail" in user_fear.lower() or "wrong" in user_fear.lower():
        return (
            "Remember: the goal of this conversation is clarity, not control of the outcome. "
            "You cannot control how they receive it. You can only control that you said it "
            "with honesty and respect. That is enough."
        )
    if relationship in ("partner", "wife", "husband", "spouse"):
        return (
            "The person in that room loves you. The conflict is between you, not the love. "
            "Start from that. Say the hard thing from a place of care, not score-keeping."
        )
    if relationship in ("boss", "board"):
        return (
            "You are not smaller than this person. Your clarity is your authority. "
            "Walk in knowing your value. Speak from fact, not from fear."
        )
    if conv_type == "apology":
        return (
            "You are not walking in to be forgiven. You are walking in to be honest. "
            "Keep those two things separate. One you can control. The other is theirs to give."
        )
    return (
        "Take one breath before you begin. Remind yourself: the person across from you is a human being "
        "trying to navigate their own complexity. Approach them with that in mind."
    )


def get_conflict_prep(db: Session, prep_id: int, user_id: str) -> dict | None:
    """Retrieve a saved prep script."""
    entry = db.query(ConflictPrep).filter_by(id=prep_id, user_id=user_id).first()
    if not entry:
        return None
    return {
        "prep_id": entry.id,
        "prep_date": entry.prep_date,
        "conversation_type": entry.conversation_type,
        "other_person": entry.other_person,
        "full_prep_script": entry.full_prep_script,
        "mindset_anchor": entry.coach_mindset_anchor,
    }


def list_conflict_preps(db: Session, user_id: str) -> list[dict]:
    preps = (
        db.query(ConflictPrep)
        .filter_by(user_id=user_id)
        .order_by(ConflictPrep.prep_date.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "prep_id": p.id,
            "prep_date": p.prep_date,
            "conversation_type": p.conversation_type,
            "other_person": p.other_person,
            "relationship_to_user": p.relationship_to_user,
        }
        for p in preps
    ]
