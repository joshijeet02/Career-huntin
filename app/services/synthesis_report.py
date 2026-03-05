from __future__ import annotations
import os
import json
import httpx
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models import DailyCheckIn, UserProfile, WeeklyReflection, HabitRecord, HabitCompletion
from app.services.council import COUNCIL

async def generate_council_synthesis_report(db: Session, user_id: str, days: int = 30) -> str:
    """
    Generates a comprehensive PDF-ready Markdown report pulling all 4 voices
    together to analyse the user's past `days`.
    """
    # 1. Gather data
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id, 
        DailyCheckIn.check_in_date >= cutoff
    ).order_by(DailyCheckIn.check_in_date).all()
    
    reflections = db.query(WeeklyReflection).filter(
        WeeklyReflection.user_id == user_id,
        WeeklyReflection.created_at >= cutoff
    ).order_by(WeeklyReflection.created_at).all()

    habits = db.query(HabitRecord).filter_by(user_id=user_id, active=True).all()

    if len(checkins) < 5:
        return "Not enough data yet. Please complete at least 5 daily check-ins so your Council has enough context to synthesize."

    # 2. Build context string
    avg_energy = sum(c.energy for c in checkins) / len(checkins)
    avg_stress = sum(c.stress for c in checkins) / len(checkins)
    moods = [c.mood_note for c in checkins if c.mood_note]
    
    ctx = [
        f"User Name: {profile.full_name if profile else 'Client'}",
        f"Role/Org: {profile.role} at {profile.organization}" if profile else "",
        f"Biggest Challenge: {profile.biggest_challenge}" if profile else "",
        f"Over the last {days} days ({len(checkins)} check-ins):",
        f"- Avg Energy: {avg_energy:.1f}/10",
        f"- Avg Stress: {avg_stress:.1f}/10",
        f"- Notable Moods/Obstacles: {'; '.join(moods[-10:])}",
    ]
    
    if reflections:
        ctx.append("\nRecent Weekly Reflections:")
        for r in reflections[-3:]:
            ctx.append(f"  Win: {r.biggest_win} | Lesson: {r.biggest_lesson} | Next Goal: {r.one_commitment_next_week}")

    if habits:
        ctx.append("\nActive Habits Tracking:")
        ctx.append(", ".join(h.name for h in habits))

    context_str = "\n".join(ctx)

    # 3. Call LLM
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "# Council Synthesis Unavailable\n\nOpenAI API key is missing. Please configure it in your environment."

    model = os.getenv("OPENAI_COACH_MODEL", "gpt-4o-mini").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    voice_prompts = "\n\n".join([f"**{v['name']} ({v['domain']})**:\n{v['voice']}" for k, v in COUNCIL.items()])

    system_prompt = f"""You are the unified voice of 'The Council' — four distinct master advisors.
You are tasked with writing a comprehensive {days}-day Coaching Synthesis Report for the user.

First, read the user's data context below. 
Then, structure a rich, Markdown-formatted coaching report.

# Tone & Rules:
- The tone should be premium, executive, highly personalized, and completely free of AI platitudes. 
- NEVER use the words "delve", "navigate", "foster", "empower", or "hold space".
- Speak directly to the user (e.g. "John,").

# Required Document Structure (use exactly these Markdown headers):
## Executive Summary
A 2-3 paragraph synthesis combining all four perspectives into one stark, clear observation of where the user is right now based on their energy, stress, and reflections.

## The Strategist's Read
From the Strategist's perspective ({COUNCIL['strategist']['thinkers']}). What is the user avoiding? Where is the execution breaking down? Name one specific structural or behavioural change.

## The Scientist's Diagnosis
From the Scientist's perspective ({COUNCIL['scientist']['thinkers']}). What habit loops, limiting beliefs, or cognitive patterns are evident in the data? Prescribe one behavioural micro-experiment.

## The Heart's Observation
From the Heart's perspective ({COUNCIL['heart']['thinkers']}). What emotional or relational dynamics are at play? What feeling is being masked by the stress?

## The Sage's Truth
From the Sage's perspective ({COUNCIL['sage']['thinkers']}). What is the deeper, timeless truth to remember? One sharp, philosophical perspective on the user's current situation.

## The Final Verdict
One binding, cohesive, absolute priority for the next 30 days.

# The Four Voices context:
{voice_prompts}
"""

    body = {
        "model": "gpt-4o",  # We explicitly use 4o for this high-value premium synthesis
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please write my Synthesis Report based on this {days}-day context:\n\n{context_str}"},
        ],
        "temperature": 0.5,
        "max_tokens": 2500,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"# Report Generation Failed\n\nThere was an issue contacting the AI provider: {str(e)}"
