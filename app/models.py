from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CandidateProfile(Base, TimestampMixin):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    achievements: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_profile: Mapped[dict] = mapped_column(JSON, default=dict)


class CVVariant(Base, TimestampMixin):
    __tablename__ = "cv_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cv_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class TargetingPolicy(Base, TimestampMixin):
    __tablename__ = "targeting_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    role_families: Mapped[list[str]] = mapped_column(JSON, default=list)
    geos: Mapped[list[str]] = mapped_column(JSON, default=list)
    seniority: Mapped[list[str]] = mapped_column(JSON, default=list)
    compensation: Mapped[dict] = mapped_column(JSON, default=dict)
    must_have: Mapped[list[str]] = mapped_column(JSON, default=list)
    avoid: Mapped[list[str]] = mapped_column(JSON, default=list)
    suppression_companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    suppression_domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    daily_rate_limits: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"application": 40, "outreach": 40}
    )


class JobRecord(Base, TimestampMixin):
    __tablename__ = "job_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    apply_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    cover_letter_required: Mapped[bool] = mapped_column(Boolean, default=False)
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="new", nullable=False, index=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)


class DiscoveryRun(Base, TimestampMixin):
    __tablename__ = "discovery_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_config_id: Mapped[str] = mapped_column(String(255), nullable=False)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    deduped_count: Mapped[int] = mapped_column(Integer, default=0)


class ApplicationDraft(Base, TimestampMixin):
    __tablename__ = "application_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_records.id"), index=True)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cv_variant_id: Mapped[int] = mapped_column(ForeignKey("cv_variants.id"), index=True)
    cv_patch: Mapped[dict] = mapped_column(JSON, default=dict)
    cv_content: Mapped[str] = mapped_column(Text, nullable=False)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="pending_review", index=True
    )

    job: Mapped["JobRecord"] = relationship("JobRecord")


class OutreachDraft(Base, TimestampMixin):
    __tablename__ = "outreach_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_records.id"), index=True)
    contacts: Mapped[list[dict]] = mapped_column(JSON, default=list)
    connection_note: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_message: Mapped[str] = mapped_column(Text, nullable=False)
    email_variant: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="pending_review", index=True
    )

    job: Mapped["JobRecord"] = relationship("JobRecord")


class ReviewBatch(Base, TimestampMixin):
    __tablename__ = "review_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="pending_review", index=True
    )
    grouped_by: Mapped[str] = mapped_column(String(64), default="company_priority")
    item_count: Mapped[int] = mapped_column(Integer, default=0)


class ReviewBatchItem(Base, TimestampMixin):
    __tablename__ = "review_batch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("review_batches.id"), index=True)
    application_draft_id: Mapped[int] = mapped_column(
        ForeignKey("application_drafts.id"), index=True
    )
    outreach_draft_id: Mapped[int] = mapped_column(ForeignKey("outreach_drafts.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_records.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="pending_review", index=True
    )
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)


class ExecutionPlan(Base, TimestampMixin):
    __tablename__ = "execution_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("review_batches.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="created", index=True)
    approved_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    deferred_count: Mapped[int] = mapped_column(Integer, default=0)


class ExecutionPlanItem(Base, TimestampMixin):
    __tablename__ = "execution_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("execution_plans.id"), index=True)
    batch_item_id: Mapped[int] = mapped_column(ForeignKey("review_batch_items.id"), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="approved")


class ExecutionEvent(Base, TimestampMixin):
    __tablename__ = "execution_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("execution_plans.id"), index=True)
    plan_item_id: Mapped[int] = mapped_column(ForeignKey("execution_plan_items.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_records.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class FollowUpTask(Base, TimestampMixin):
    __tablename__ = "follow_up_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_records.id"), index=True)
    outreach_draft_id: Mapped[int] = mapped_column(ForeignKey("outreach_drafts.id"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="linkedin_email")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending", index=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
