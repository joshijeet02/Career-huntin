from collections import Counter
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    CandidateProfile,
    ExecutionEvent,
    JobRecord,
    OutreachDraft,
    ReviewBatchItem,
    TargetingPolicy,
)


def _active_policy(db: Session) -> TargetingPolicy | None:
    profile = db.scalar(select(CandidateProfile).order_by(CandidateProfile.version.desc()).limit(1))
    if not profile:
        return None
    return db.scalar(
        select(TargetingPolicy)
        .where(TargetingPolicy.profile_version == profile.version)
        .order_by(TargetingPolicy.id.desc())
        .limit(1)
    )


def run_compliance_checks(
    db: Session,
    item_id: int,
    action: str,
    channel: str,
) -> tuple[bool, str | None]:
    policy = _active_policy(db)
    item = db.get(ReviewBatchItem, item_id)
    if item is None:
        return False, "Review item not found"

    job = db.get(JobRecord, item.job_id)
    if job is None:
        return False, "Job not found"

    if policy:
        if job.company.lower() in {c.lower() for c in policy.suppression_companies}:
            return False, "Company is suppressed"

        domain = urlparse(job.apply_url).netloc.lower()
        if any(d.lower() in domain for d in policy.suppression_domains):
            return False, "Domain is suppressed"

        limits = policy.daily_rate_limits or {"application": 40, "outreach": 40}
    else:
        limits = {"application": 40, "outreach": 40}

    today_events = db.scalars(
        select(ExecutionEvent).where(ExecutionEvent.status == "success")
    ).all()
    counter = Counter([event.event_type for event in today_events])
    limit_key = "application" if action == "submit_application" else "outreach"
    if counter[limit_key] >= limits.get(limit_key, 40):
        return False, f"Rate limit exceeded for {limit_key}"

    if action == "send_outreach":
        outreach = db.get(OutreachDraft, item.outreach_draft_id)
        if outreach:
            same_note_count = db.scalars(select(OutreachDraft)).all()
            identical = sum(1 for draft in same_note_count if draft.connection_note == outreach.connection_note)
            if identical > 10:
                return False, "Message uniqueness guard triggered"

    if action == "submit_application":
        app_draft = db.get(ApplicationDraft, item.application_draft_id)
        if app_draft is None:
            return False, "Application draft missing"
        if not app_draft.cv_content.strip():
            return False, "Missing CV content"

    return True, None

