from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ExecutionEvent,
    ExecutionPlanItem,
    FollowUpTask,
    OutreachDraft,
    ReviewBatchItem,
)


def schedule_followups_for_plan(db: Session, plan_id: int) -> int:
    outreach_events = db.scalars(
        select(ExecutionEvent).where(
            ExecutionEvent.plan_id == plan_id,
            ExecutionEvent.event_type == "outreach",
            ExecutionEvent.status == "success",
        )
    ).all()
    created = 0
    for event in outreach_events:
        # Never schedule follow-up on the same day as first outreach.
        due_at = datetime.utcnow() + timedelta(days=1, hours=7)
        plan_item = db.get(ExecutionPlanItem, event.plan_item_id)
        if plan_item is None:
            continue
        batch_item = db.get(ReviewBatchItem, plan_item.batch_item_id)
        if batch_item is None:
            continue
        outreach = db.get(OutreachDraft, batch_item.outreach_draft_id)
        if outreach is None:
            continue
        existing = db.scalar(
            select(FollowUpTask).where(
                FollowUpTask.job_id == event.job_id,
                FollowUpTask.outreach_draft_id == outreach.id,
                FollowUpTask.status == "pending",
            )
        )
        if existing:
            continue
        db.add(
            FollowUpTask(
                job_id=event.job_id,
                outreach_draft_id=outreach.id,
                due_at=due_at,
                channel=event.channel,
                status="pending",
            )
        )
        created += 1
    return created
