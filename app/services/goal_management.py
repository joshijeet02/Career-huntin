from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import BigGoal, GoalMilestone, Commitment, UserProfile
from app.services.coach import generate_coach_response
from app.schemas import CoachRequest

def create_big_goal(
    db: Session,
    user_id: str,
    title: str,
    description: str = "",
    target_date: str | None = None,
    category: str = "growth"
) -> BigGoal:
    goal = BigGoal(
        user_id=user_id,
        title=title,
        description=description,
        target_date=target_date,
        category=category,
        status="active",
        progress_pct=0
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal

def get_user_goals(db: Session, user_id: str) -> list[BigGoal]:
    return db.query(BigGoal).filter_by(user_id=user_id).all()

def get_goal_details(db: Session, goal_id: int, user_id: str) -> dict[str, Any]:
    goal = db.query(BigGoal).filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return {"error": "Goal not found"}
    
    milestones = db.query(GoalMilestone).filter_by(parent_goal_id=goal_id).all()
    commitments = db.query(Commitment).filter_by(parent_goal_id=goal_id).all()
    
    return {
        "goal": goal,
        "milestones": milestones,
        "commitments": commitments
    }

async def refine_goal_with_coach(
    db: Session,
    user_id: str,
    goal_id: int,
    user_vision: str
) -> str:
    """
    Council Alignment Flow:
    AI analyzes the goal and refines it into a SMART vision statement.
    Checks feasibility against current energy and workload.
    """
    goal = db.query(BigGoal).filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return "Goal not found."
    
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    
    # Context: User's energy baseline, burnout risk, and existing commitments
    energy = profile.energy_baseline if profile else 7.0
    risk = profile.burnout_risk if profile else "low"
    
    open_commitments = db.query(Commitment).filter_by(user_id=user_id, status="open").count()
    
    prompt = (
        f"Goal: {goal.title}\n"
        f"User's Vision: {user_vision}\n"
        f"Current Energy: {energy}/10\n"
        f"Burnout Risk: {risk}\n"
        f"Active Commitments: {open_commitments}\n\n"
        "Act as an executive coach. Analyze this goal. Is it SMART (Specific, Measurable, Achievable, Relevant, Time-bound)? "
        "If the user's energy is low or workload is high, warn them. "
        "Provide a refined vision statement that makes this goal more tactical and inspiring. "
        "Return the refined vision statement as a concise paragraph."
    )
    
    coach_resp = await generate_coach_response(
        CoachRequest(
            context=prompt,
            goal="Refine the user's goal into a realistic and inspiring SMART vision.",
            track="leadership",
            user_id=user_id
        )
    )
    
    goal.vision_statement = coach_resp.message
    db.commit()
    return coach_resp.message

def update_goal_progress(db: Session, goal_id: int, user_id: str) -> int:
    """
    Calculate progress based on completed milestones and commitments.
    Milestones carry more weight than daily commitments.
    """
    goal = db.query(BigGoal).filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return 0
    
    milestones = db.query(GoalMilestone).filter_by(parent_goal_id=goal_id).all()
    commitments = db.query(Commitment).filter_by(parent_goal_id=goal_id).all()
    
    total_weight = 0
    completed_weight = 0
    
    # Milestones (Weight: 10 each)
    for m in milestones:
        total_weight += 10
        if m.status == "complete":
            completed_weight += 10
        elif m.status == "on_track":
            completed_weight += 5
            
    # Commitments (Weight: 2 each)
    for c in commitments:
        total_weight += 2
        if c.status == "kept":
            completed_weight += 2
        elif c.status == "partial":
            completed_weight += 1
            
    if total_weight == 0:
        return 0
    
    progress = int((completed_weight / total_weight) * 100)
    goal.progress_pct = progress
    db.commit()
    return progress
