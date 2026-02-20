from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    ExecutionPlan,
    ExecutionPlanItem,
    OutreachDraft,
    ReviewBatch,
    ReviewBatchItem,
)
from app.schemas import ReviewDecisionItem
from app.services.audit import log_event


def _apply_edits(item: ReviewBatchItem, decision: ReviewDecisionItem, db: Session) -> None:
    if not decision.edits:
        return
    app_draft = db.get(ApplicationDraft, item.application_draft_id)
    outreach = db.get(OutreachDraft, item.outreach_draft_id)
    if app_draft and "cover_letter" in decision.edits:
        app_draft.cover_letter = decision.edits["cover_letter"]
    if app_draft and "cv_patch" in decision.edits:
        app_draft.cv_patch = decision.edits["cv_patch"]
    if outreach and "connection_note" in decision.edits:
        outreach.connection_note = decision.edits["connection_note"]
    if outreach and "email_variant" in decision.edits:
        outreach.email_variant = decision.edits["email_variant"]


def apply_batch_decisions(
    db: Session, batch_id: int, decisions: list[ReviewDecisionItem]
) -> ExecutionPlan:
    batch = db.get(ReviewBatch, batch_id)
    if batch is None:
        raise ValueError("Batch not found")
    if batch.status != "pending_review":
        raise ValueError("Batch is not open for decisions")

    decision_map = {entry.batch_item_id: entry for entry in decisions}
    items = db.scalars(select(ReviewBatchItem).where(ReviewBatchItem.batch_id == batch_id)).all()

    plan = ExecutionPlan(batch_id=batch_id, status="created", approved_count=0, rejected_count=0, deferred_count=0)
    db.add(plan)
    db.flush()

    for item in items:
        decision = decision_map.get(item.id)
        if decision is None:
            # Any unspecified item defaults to deferred for safety.
            item.status = "deferred"
            plan.deferred_count += 1
            continue

        normalized = decision.decision.strip().lower()
        _apply_edits(item, decision, db)
        app_draft = db.get(ApplicationDraft, item.application_draft_id)
        outreach = db.get(OutreachDraft, item.outreach_draft_id)

        if normalized == "approve":
            item.status = "approved"
            if app_draft:
                app_draft.status = "approved"
            if outreach:
                outreach.status = "approved"
            plan.approved_count += 1

            db.add(
                ExecutionPlanItem(
                    plan_id=plan.id,
                    batch_item_id=item.id,
                    action="submit_application",
                    channel="job_board",
                    status="approved",
                )
            )
            db.add(
                ExecutionPlanItem(
                    plan_id=plan.id,
                    batch_item_id=item.id,
                    action="send_outreach",
                    channel="linkedin_email",
                    status="approved",
                )
            )
        elif normalized == "reject":
            item.status = "rejected"
            if app_draft:
                app_draft.status = "rejected"
            if outreach:
                outreach.status = "rejected"
            plan.rejected_count += 1
        else:
            item.status = "deferred"
            if app_draft:
                app_draft.status = "deferred"
            if outreach:
                outreach.status = "deferred"
            plan.deferred_count += 1

    batch.status = "decided"
    # Session has autoflush=False, so persist plan items before execution queries.
    db.flush()
    log_event(
        db,
        entity_type="review_batch",
        entity_id=batch.id,
        action="decision_applied",
        details={
            "execution_plan_id": plan.id,
            "approved": plan.approved_count,
            "rejected": plan.rejected_count,
            "deferred": plan.deferred_count,
        },
    )
    return plan
