from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CVInput(BaseModel):
    name: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TargetingPolicyInput(BaseModel):
    role_families: list[str] = Field(default_factory=list)
    geos: list[str] = Field(default_factory=list)
    seniority: list[str] = Field(default_factory=list)
    compensation: dict[str, Any] = Field(default_factory=dict)
    must_have: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    suppression_companies: list[str] = Field(default_factory=list)
    suppression_domains: list[str] = Field(default_factory=list)
    daily_rate_limits: dict[str, int] = Field(
        default_factory=lambda: {"application": 40, "outreach": 40}
    )


class ProfileIngestRequest(BaseModel):
    full_name: str
    email: str
    skills: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    raw_profile: dict[str, Any] = Field(default_factory=dict)
    cv_variants: list[CVInput] = Field(default_factory=list)
    targeting_policy: TargetingPolicyInput = Field(default_factory=TargetingPolicyInput)


class ProfileIngestResponse(BaseModel):
    profile_version_id: int


class DiscoverRunRequest(BaseModel):
    source_config_id: str


class DiscoverRunResponse(BaseModel):
    run_id: int
    discovered_count: int


class ContactOut(BaseModel):
    name: str
    title: str
    profile_url: str
    confidence: float


class QueueItemOut(BaseModel):
    batch_item_id: int
    job_id: int
    company: str
    title: str
    location: str
    relevance_score: float
    application_draft_id: int
    cv_patch: dict[str, Any]
    cover_letter: str | None
    outreach_draft_id: int
    contacts: list[ContactOut]
    connection_note: str
    follow_up_message: str
    email_variant: str
    status: str


class ReviewBatchOut(BaseModel):
    batch_id: int
    status: str
    grouped_by: str
    item_count: int
    created_at: datetime
    items: list[QueueItemOut]


class ReviewDecisionItem(BaseModel):
    batch_item_id: int
    decision: str
    edits: dict[str, Any] = Field(default_factory=dict)


class ReviewBatchDecisionRequest(BaseModel):
    decisions: list[ReviewDecisionItem]


class ReviewBatchDecisionResponse(BaseModel):
    execution_plan_id: int
    approved_count: int
    rejected_count: int
    deferred_count: int


class ExecutionItemResult(BaseModel):
    plan_item_id: int
    action: str
    channel: str
    status: str
    attempts: int
    error_message: str | None = None


class ExecutionPlanRunResponse(BaseModel):
    plan_id: int
    status: str
    items: list[ExecutionItemResult]


class AnalyticsFunnelResponse(BaseModel):
    applied: int
    replied: int
    interview: int
    offers: int


class DailyRunRequest(BaseModel):
    source_config_id: str = "daily-autonomous"


class DailyRunResponse(BaseModel):
    run_id: int
    batch_id: int | None
    execution_plan_id: int | None
    discovered_count: int
    approved_items: int
    executed_items: int
    followups_created: int
    tracking_snapshot_path: str | None


class DashboardEventOut(BaseModel):
    created_at: str
    company: str
    title: str
    event_type: str
    channel: str
    status: str
    attempt: int
    error_message: str | None = None


class DashboardFollowUpOut(BaseModel):
    due_at: str
    company: str
    title: str
    channel: str
    status: str


class DashboardQueueOut(BaseModel):
    job_id: int
    company: str
    title: str
    location: str
    score: float
    source: str
    status: str
    apply_url: str


class QuickApplyResponse(BaseModel):
    execution_plan_id: int
    job_id: int
    company: str
    title: str
    results: list[ExecutionItemResult]


class DashboardDataResponse(BaseModel):
    kpis: dict[str, int]
    job_status_counts: dict[str, int]
    recent_events: list[DashboardEventOut]
    followups: list[DashboardFollowUpOut]
    queue_preview: list[DashboardQueueOut]
    top_targets: list[DashboardQueueOut]
