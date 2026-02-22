from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    ExecutionEvent,
    ExecutionPlan,
    ExecutionPlanItem,
    JobRecord,
    OutreachDraft,
    ReviewBatchItem,
)
from app.schemas import ExecutionItemResult
from app.services.audit import log_event
from app.services.compliance import run_compliance_checks


MAX_ATTEMPTS = 3


def _attempt_action(job: JobRecord, action: str, attempt: int) -> tuple[bool, str | None]:
    if "transient" in job.company.lower() and attempt < MAX_ATTEMPTS:
        return False, "Transient connector timeout"
    if "blocked" in job.status:
        return False, "Job blocked"
    return True, None


def execute_plan(db: Session, plan_id: int) -> tuple[ExecutionPlan, list[ExecutionItemResult]]:
    plan = db.get(ExecutionPlan, plan_id)
    if plan is None:
        raise ValueError("Execution plan not found")

    items = db.scalars(
        select(ExecutionPlanItem).where(ExecutionPlanItem.plan_id == plan_id).order_by(ExecutionPlanItem.id.asc())
    ).all()
    results: list[ExecutionItemResult] = []

    for item in items:
        batch_item = db.get(ReviewBatchItem, item.batch_item_id)
        if batch_item is None:
            continue
        job = db.get(JobRecord, batch_item.job_id)
        if job is None:
            continue

        allowed, error = run_compliance_checks(db, batch_item.id, item.action, item.channel)
        if not allowed:
            item.status = "blocked"
            db.add(
                ExecutionEvent(
                    plan_id=plan.id,
                    plan_item_id=item.id,
                    job_id=job.id,
                    event_type="application" if item.action == "submit_application" else "outreach",
                    channel=item.channel,
                    status="blocked",
                    attempt=1,
                    error_message=error,
                )
            )
            results.append(
                ExecutionItemResult(
                    plan_item_id=item.id,
                    action=item.action,
                    channel=item.channel,
                    status="blocked",
                    attempts=1,
                    error_message=error,
                )
            )
            continue

        success = False
        error_message = None
        attempts = 0
        for attempts in range(1, MAX_ATTEMPTS + 1):
            ok, failure = _attempt_action(job, item.action, attempts)
            if ok:
                success = True
                break
            error_message = failure
            db.add(
                ExecutionEvent(
                    plan_id=plan.id,
                    plan_item_id=item.id,
                    job_id=job.id,
                    event_type="application" if item.action == "submit_application" else "outreach",
                    channel=item.channel,
                    status="retrying",
                    attempt=attempts,
                    error_message=failure,
                )
            )

        if success:
            item.status = "success"
            db.add(
                ExecutionEvent(
                    plan_id=plan.id,
                    plan_item_id=item.id,
                    job_id=job.id,
                    event_type="application" if item.action == "submit_application" else "outreach",
                    channel=item.channel,
                    status="success",
                    attempt=attempts,
                    error_message=None,
                )
            )
            if item.action == "submit_application":
                job.status = "applied"
            else:
                if job.status == "applied":
                    job.status = "outreach_sent"
            results.append(
                ExecutionItemResult(
                    plan_item_id=item.id,
                    action=item.action,
                    channel=item.channel,
                    status="success",
                    attempts=attempts,
                )
            )
        else:
            item.status = "failed"
            db.add(
                ExecutionEvent(
                    plan_id=plan.id,
                    plan_item_id=item.id,
                    job_id=job.id,
                    event_type="application" if item.action == "submit_application" else "outreach",
                    channel=item.channel,
                    status="failed",
                    attempt=attempts,
                    error_message=error_message,
                )
            )
            results.append(
                ExecutionItemResult(
                    plan_item_id=item.id,
                    action=item.action,
                    channel=item.channel,
                    status="failed",
                    attempts=attempts,
                    error_message=error_message,
                )
            )

    plan.status = "completed"
    log_event(
        db,
        entity_type="execution_plan",
        entity_id=plan.id,
        action="executed",
        details={"items": len(results), "success": sum(1 for r in results if r.status == "success")},
    )
    return plan, results


def approve_and_execute_batch_item(
    db: Session, batch_item_id: int
) -> tuple[ExecutionPlan, list[ExecutionItemResult]]:
    item = db.get(ReviewBatchItem, batch_item_id)
    if item is None:
        raise ValueError("Batch item not found")

    app_draft = db.get(ApplicationDraft, item.application_draft_id)
    outreach_draft = db.get(OutreachDraft, item.outreach_draft_id)
    if app_draft is None or outreach_draft is None:
        raise ValueError("Drafts not found for batch item")

    # Idempotency guard: if already executed successfully, avoid duplicating sends.
    existing_success = db.scalar(
        select(ExecutionEvent)
        .where(ExecutionEvent.job_id == item.job_id, ExecutionEvent.status == "success")
        .limit(1)
    )
    if existing_success:
        raise ValueError("Job already executed successfully")

    item.status = "approved"
    app_draft.status = "approved"
    outreach_draft.status = "approved"

    plan = ExecutionPlan(
        batch_id=item.batch_id,
        status="created",
        approved_count=1,
        rejected_count=0,
        deferred_count=0,
    )
    db.add(plan)
    db.flush()

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
    db.flush()
    return execute_plan(db, plan.id)
