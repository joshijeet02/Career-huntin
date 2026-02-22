from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ExecutionEvent, FollowUpTask, JobRecord, ReviewBatch, ReviewBatchItem


@dataclass
class DashboardData:
    kpis: dict[str, int]
    job_status_counts: dict[str, int]
    recent_events: list[dict[str, Any]]
    followups: list[dict[str, Any]]
    queue_preview: list[dict[str, Any]]
    top_targets: list[dict[str, Any]]


def _count_rows(db: Session, stmt) -> int:
    value = db.scalar(stmt)
    return int(value or 0)


def _matches_role_family(job: JobRecord, role_family: str | None) -> bool:
    if not role_family:
        return True
    rf = role_family.lower().strip()
    title_desc = f"{job.title} {job.description}".lower()
    if rf == "vc":
        return "venture" in title_desc or "investment" in title_desc or "vc" in title_desc
    if rf == "consulting":
        return "consult" in title_desc or "advisory" in title_desc or "strategy" in title_desc
    if rf == "economics_ai":
        return ("econom" in title_desc or "policy" in title_desc) and (
            "ai" in title_desc or "llm" in title_desc or "automation" in title_desc
        )
    return rf in title_desc


def _is_top_target(job: JobRecord) -> bool:
    text = f"{job.title} {job.description}".lower()
    vc = "venture" in text or "investment" in text or "vc" in text
    consulting = "consult" in text or "advisory" in text or "strategy" in text
    ai_econ = ("econom" in text or "policy" in text) and (
        "ai" in text or "automation" in text or "llm" in text
    )
    high_signal_source = job.source in {
        "venture_capital_careers",
        "wellfound",
        "yc_jobs",
        "company_site",
        "imf",
        "world_bank",
        "un",
        "adb",
    }
    return vc or consulting or ai_econ or (high_signal_source and job.relevance_score >= 70)


def collect_dashboard_data(
    db: Session,
    source: str | None = None,
    geography: str | None = None,
    role_family: str | None = None,
    status: str | None = None,
) -> DashboardData:
    jobs = db.scalars(select(JobRecord).order_by(JobRecord.relevance_score.desc())).all()
    filtered_jobs: list[JobRecord] = []
    for job in jobs:
        if source and job.source.lower() != source.lower():
            continue
        if geography and geography.lower() not in job.location.lower():
            continue
        if status and job.status.lower() != status.lower():
            continue
        if not _matches_role_family(job, role_family):
            continue
        filtered_jobs.append(job)
    filtered_job_ids = {job.id for job in filtered_jobs}

    kpis = {
        "total_jobs": len(filtered_jobs),
        "applied_jobs": sum(1 for job in filtered_jobs if job.status in {"applied", "outreach_sent"}),
        "pending_review_items": _count_rows(
            db,
            select(func.count())
            .select_from(ReviewBatchItem)
            .where(
                ReviewBatchItem.status == "pending_review",
                ReviewBatchItem.job_id.in_(filtered_job_ids) if filtered_job_ids else False,
            ),
        ),
        "pending_followups": _count_rows(
            db,
            select(func.count())
            .select_from(FollowUpTask)
            .where(
                FollowUpTask.status == "pending",
                FollowUpTask.job_id.in_(filtered_job_ids) if filtered_job_ids else False,
            ),
        ),
        "active_batches": _count_rows(
            db,
            select(func.count()).select_from(ReviewBatch).where(ReviewBatch.status == "pending_review"),
        ),
    }

    job_status_counts: dict[str, int] = {}
    for job in filtered_jobs:
        job_status_counts[job.status] = job_status_counts.get(job.status, 0) + 1

    events = db.scalars(
        select(ExecutionEvent)
        .order_by(ExecutionEvent.created_at.desc(), ExecutionEvent.id.desc())
        .limit(12)
    ).all()
    recent_events = []
    for event in events:
        if filtered_job_ids and event.job_id not in filtered_job_ids:
            continue
        job = db.get(JobRecord, event.job_id)
        recent_events.append(
            {
                "created_at": event.created_at.isoformat(),
                "company": job.company if job else "",
                "title": job.title if job else "",
                "event_type": event.event_type,
                "channel": event.channel,
                "status": event.status,
                "attempt": event.attempt,
                "error_message": event.error_message,
            }
        )

    followup_rows = db.scalars(
        select(FollowUpTask)
        .where(FollowUpTask.status == "pending")
        .order_by(FollowUpTask.due_at.asc())
        .limit(12)
    ).all()
    followups = []
    for row in followup_rows:
        if filtered_job_ids and row.job_id not in filtered_job_ids:
            continue
        job = db.get(JobRecord, row.job_id)
        followups.append(
            {
                "due_at": row.due_at.isoformat(),
                "company": job.company if job else "",
                "title": job.title if job else "",
                "channel": row.channel,
                "status": row.status,
            }
        )

    queue_items = db.scalars(
        select(ReviewBatchItem)
        .where(ReviewBatchItem.status == "pending_review")
        .order_by(ReviewBatchItem.priority_score.desc())
        .limit(12)
    ).all()
    queue_preview = []
    for item in queue_items:
        job = db.get(JobRecord, item.job_id)
        if job is None:
            continue
        if filtered_job_ids and job.id not in filtered_job_ids:
            continue
        queue_preview.append(
            {
                "job_id": job.id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "score": job.relevance_score,
                "source": job.source,
                "status": item.status,
                "apply_url": job.apply_url,
            }
        )

    top_targets: list[dict[str, Any]] = []
    for job in filtered_jobs:
        if not _is_top_target(job):
            continue
        top_targets.append(
            {
                "job_id": job.id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "score": job.relevance_score,
                "source": job.source,
                "status": job.status,
                "apply_url": job.apply_url,
            }
        )
    top_targets.sort(key=lambda x: x["score"], reverse=True)
    top_targets = top_targets[:12]

    return DashboardData(
        kpis=kpis,
        job_status_counts=job_status_counts,
        recent_events=recent_events,
        followups=followups,
        queue_preview=queue_preview,
        top_targets=top_targets,
    )
