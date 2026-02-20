from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReviewBatch, ReviewBatchItem
from app.schemas import ReviewDecisionItem
from app.services.discovery import run_discovery
from app.services.execution import execute_plan
from app.services.followups import schedule_followups_for_plan
from app.services.personalization import generate_drafts_and_batch
from app.services.profile_config import get_execution_preferences
from app.services.review import apply_batch_decisions
from app.services.tracking import export_tracking_snapshot


@dataclass
class DailyRunResult:
    run_id: int
    batch_id: int | None
    execution_plan_id: int | None
    discovered_count: int
    approved_items: int
    executed_items: int
    followups_created: int
    tracking_snapshot_path: str | None


def _latest_pending_batch(db: Session) -> ReviewBatch | None:
    return db.scalar(
        select(ReviewBatch)
        .where(ReviewBatch.status == "pending_review")
        .order_by(ReviewBatch.created_at.desc())
        .limit(1)
    )


def run_daily_cycle(db: Session, source_config_id: str) -> DailyRunResult:
    run = run_discovery(db, source_config_id)
    batch = generate_drafts_and_batch(db)
    if batch is None:
        batch = _latest_pending_batch(db)

    prefs = get_execution_preferences()
    auto_execute = bool(prefs.get("written_approval_received", False)) and (
        prefs.get("approval_model") == "single-policy-approval-then-auto-execute"
    )

    plan_id = None
    approved = 0
    executed = 0
    followups = 0
    tracking_path = None

    if batch is not None and auto_execute:
        items = db.scalars(
            select(ReviewBatchItem).where(ReviewBatchItem.batch_id == batch.id)
        ).all()
        decisions = [
            ReviewDecisionItem(batch_item_id=item.id, decision="approve", edits={}) for item in items
        ]
        plan = apply_batch_decisions(db, batch.id, decisions)
        plan_id = plan.id
        approved = plan.approved_count
        _, results = execute_plan(db, plan.id)
        executed = len(results)
        followups = schedule_followups_for_plan(db, plan.id)
        tracking_path = export_tracking_snapshot(db)

    return DailyRunResult(
        run_id=run.id,
        batch_id=batch.id if batch else None,
        execution_plan_id=plan_id,
        discovered_count=run.discovered_count - run.deduped_count,
        approved_items=approved,
        executed_items=executed,
        followups_created=followups,
        tracking_snapshot_path=tracking_path,
    )

