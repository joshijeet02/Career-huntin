from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    CVVariant,
    CandidateProfile,
    JobRecord,
    OutreachDraft,
    ReviewBatch,
    ReviewBatchItem,
)
from app.services.audit import log_event


def _choose_cv_variant(db: Session, profile_version: int, job: JobRecord) -> CVVariant:
    variants = db.scalars(
        select(CVVariant).where(CVVariant.profile_version == profile_version).order_by(CVVariant.id.asc())
    ).all()
    if not variants:
        raise ValueError("No CV variants found for active profile")

    title_lower = job.title.lower()
    for variant in variants:
        name_lower = variant.name.lower()
        if "backend" in title_lower and "backend" in name_lower:
            return variant
        if "platform" in title_lower and "platform" in name_lower:
            return variant
    return variants[0]


def _build_cv_patch(job: JobRecord, profile: CandidateProfile) -> dict:
    top_skills = [skill for skill in profile.skills if skill.lower() in {s.lower() for s in job.required_skills}]
    return {
        "summary_update": f"Emphasize impact for {job.title} at {job.company}.",
        "skills_highlighted": top_skills[:6],
        "why": f"Matched required skills for {job.title} and aligned achievements to job description.",
    }


def _cover_letter(job: JobRecord, profile: CandidateProfile) -> str | None:
    if not job.cover_letter_required:
        return None
    return (
        f"Dear {job.company} team,\n\n"
        f"I am excited to apply for the {job.title} role. "
        f"My background in {', '.join(profile.skills[:4])} aligns with your needs.\n\n"
        "I would value the opportunity to discuss how I can contribute quickly.\n\n"
        f"Best regards,\n{profile.full_name}"
    )


def _outreach(job: JobRecord, profile: CandidateProfile) -> OutreachDraft:
    contacts = [
        {
            "name": f"{job.company} Hiring Manager",
            "title": f"Hiring Manager, {job.title}",
            "profile_url": f"https://www.linkedin.com/company/{job.company.lower().replace(' ', '-')}",
            "confidence": 0.74,
        },
        {
            "name": f"{job.company} Recruiter",
            "title": "Technical Recruiter",
            "profile_url": f"https://www.linkedin.com/company/{job.company.lower().replace(' ', '-')}",
            "confidence": 0.68,
        },
    ]
    connection_note = (
        f"Hi, I just applied for {job.title} at {job.company}. "
        "I’d love to connect and share a concise overview of my relevant experience."
    )
    follow_up = (
        f"Thanks for connecting. I’m highly interested in {job.title}. "
        "Happy to send a short portfolio of recent impact aligned to this role."
    )
    email_variant = (
        f"Subject: Interest in {job.title} at {job.company}\n\n"
        f"Hi team,\n\nI’ve applied for {job.title} and wanted to share a brief intro. "
        f"I bring strong experience in {', '.join(profile.skills[:4])} and would welcome a conversation.\n\n"
        f"Regards,\n{profile.full_name}"
    )
    return OutreachDraft(
        job_id=job.id,
        contacts=contacts,
        connection_note=connection_note,
        follow_up_message=follow_up,
        email_variant=email_variant,
        status="pending_review",
    )


def generate_drafts_and_batch(db: Session) -> ReviewBatch | None:
    profile = db.scalar(
        select(CandidateProfile).order_by(CandidateProfile.version.desc()).limit(1)
    )
    if profile is None:
        return None

    jobs = db.scalars(
        select(JobRecord)
        .where(JobRecord.status == "new")
        .order_by(JobRecord.relevance_score.desc(), JobRecord.id.asc())
    ).all()
    if not jobs:
        return None

    batch = ReviewBatch(status="pending_review", grouped_by="company_priority", item_count=0)
    db.add(batch)
    db.flush()

    for job in jobs:
        cv_variant = _choose_cv_variant(db, profile.version, job)
        patch = _build_cv_patch(job, profile)
        app_draft = ApplicationDraft(
            job_id=job.id,
            profile_version=profile.version,
            cv_variant_id=cv_variant.id,
            cv_patch=patch,
            cv_content=cv_variant.content,
            cover_letter=_cover_letter(job, profile),
            status="pending_review",
        )
        db.add(app_draft)
        db.flush()

        outreach = _outreach(job, profile)
        db.add(outreach)
        db.flush()

        item = ReviewBatchItem(
            batch_id=batch.id,
            application_draft_id=app_draft.id,
            outreach_draft_id=outreach.id,
            job_id=job.id,
            status="pending_review",
            priority_score=job.relevance_score,
        )
        db.add(item)

        job.status = "pending_review"
        log_event(
            db,
            entity_type="job_record",
            entity_id=job.id,
            action="drafted_for_review",
            details={"batch_id": batch.id, "score": job.relevance_score},
        )

    batch.item_count = len(jobs)
    log_event(
        db,
        entity_type="review_batch",
        entity_id=batch.id,
        action="created",
        details={"item_count": batch.item_count},
    )
    return batch

