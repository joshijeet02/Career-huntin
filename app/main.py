from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import (
    ApplicationDraft,
    CVVariant,
    CandidateProfile,
    OutreachDraft,
    ReviewBatch,
    ReviewBatchItem,
    TargetingPolicy,
)
from app.schemas import (
    AnalyticsFunnelResponse,
    DashboardDataResponse,
    DailyRunRequest,
    DailyRunResponse,
    DiscoverRunRequest,
    DiscoverRunResponse,
    ProfileIngestRequest,
    ProfileIngestResponse,
    QueueItemOut,
    ReviewBatchDecisionRequest,
    ReviewBatchDecisionResponse,
    ReviewBatchOut,
    ExecutionPlanRunResponse,
)
from app.services.analytics import funnel
from app.services.discovery import run_discovery
from app.services.personalization import generate_drafts_and_batch
from app.services.review import apply_batch_decisions
from app.services.execution import execute_plan
from app.services.audit import log_event
from app.services.dashboard import collect_dashboard_data
from app.services.orchestrator import run_daily_cycle
from app.services.tracking import TRACKING_PATH

app = FastAPI(title="Job Search Automation MVP", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.post("/ingest/profile", response_model=ProfileIngestResponse)
def ingest_profile(payload: ProfileIngestRequest, db: Session = Depends(get_db)) -> ProfileIngestResponse:
    latest = db.scalar(select(CandidateProfile).order_by(CandidateProfile.version.desc()).limit(1))
    next_version = 1 if latest is None else latest.version + 1

    profile = CandidateProfile(
        version=next_version,
        full_name=payload.full_name,
        email=payload.email,
        skills=payload.skills,
        achievements=payload.achievements,
        preferences=payload.preferences,
        raw_profile=payload.raw_profile,
    )
    db.add(profile)
    db.flush()

    for variant in payload.cv_variants:
        db.add(
            CVVariant(
                profile_version=next_version,
                name=variant.name,
                cv_metadata=variant.metadata,
                content=variant.content,
            )
        )

    db.add(
        TargetingPolicy(
            profile_version=next_version,
            role_families=payload.targeting_policy.role_families,
            geos=payload.targeting_policy.geos,
            seniority=payload.targeting_policy.seniority,
            compensation=payload.targeting_policy.compensation,
            must_have=payload.targeting_policy.must_have,
            avoid=payload.targeting_policy.avoid,
            suppression_companies=payload.targeting_policy.suppression_companies,
            suppression_domains=payload.targeting_policy.suppression_domains,
            daily_rate_limits=payload.targeting_policy.daily_rate_limits,
        )
    )
    log_event(
        db,
        entity_type="candidate_profile",
        entity_id=profile.id,
        action="ingested",
        details={"version": next_version, "cv_count": len(payload.cv_variants)},
    )
    db.commit()
    return ProfileIngestResponse(profile_version_id=next_version)


@app.post("/jobs/discover/run", response_model=DiscoverRunResponse)
def discover_jobs(payload: DiscoverRunRequest, db: Session = Depends(get_db)) -> DiscoverRunResponse:
    run = run_discovery(db, payload.source_config_id)
    batch = generate_drafts_and_batch(db)
    if batch:
        log_event(
            db,
            entity_type="review_batch",
            entity_id=batch.id,
            action="queued",
            details={"from_run_id": run.id},
        )
    db.commit()
    return DiscoverRunResponse(run_id=run.id, discovered_count=run.discovered_count - run.deduped_count)


@app.get("/jobs/queue", response_model=list[ReviewBatchOut])
def queue(
    status: str = Query(default="pending_review"),
    db: Session = Depends(get_db),
) -> list[ReviewBatchOut]:
    batches = db.scalars(
        select(ReviewBatch).where(ReviewBatch.status == status).order_by(ReviewBatch.created_at.desc())
    ).all()
    out: list[ReviewBatchOut] = []
    for batch in batches:
        batch_items = db.scalars(
            select(ReviewBatchItem).where(ReviewBatchItem.batch_id == batch.id).order_by(ReviewBatchItem.priority_score.desc())
        ).all()
        items: list[QueueItemOut] = []
        for item in batch_items:
            app_draft = db.get(ApplicationDraft, item.application_draft_id)
            outreach = db.get(OutreachDraft, item.outreach_draft_id)
            if app_draft is None or outreach is None or app_draft.job is None:
                continue
            job = app_draft.job
            contacts = [
                {
                    "name": c.get("name", ""),
                    "title": c.get("title", ""),
                    "profile_url": c.get("profile_url", ""),
                    "confidence": float(c.get("confidence", 0.0)),
                }
                for c in outreach.contacts
            ]
            items.append(
                QueueItemOut(
                    batch_item_id=item.id,
                    job_id=job.id,
                    company=job.company,
                    title=job.title,
                    location=job.location,
                    relevance_score=job.relevance_score,
                    application_draft_id=app_draft.id,
                    cv_patch=app_draft.cv_patch,
                    cover_letter=app_draft.cover_letter,
                    outreach_draft_id=outreach.id,
                    contacts=contacts,
                    connection_note=outreach.connection_note,
                    follow_up_message=outreach.follow_up_message,
                    email_variant=outreach.email_variant,
                    status=item.status,
                )
            )
        out.append(
            ReviewBatchOut(
                batch_id=batch.id,
                status=batch.status,
                grouped_by=batch.grouped_by,
                item_count=batch.item_count,
                created_at=batch.created_at,
                items=items,
            )
        )
    return out


@app.post("/review/batch/{batch_id}/decision", response_model=ReviewBatchDecisionResponse)
def decide_batch(
    batch_id: int, payload: ReviewBatchDecisionRequest, db: Session = Depends(get_db)
) -> ReviewBatchDecisionResponse:
    try:
        plan = apply_batch_decisions(db, batch_id, payload.decisions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return ReviewBatchDecisionResponse(
        execution_plan_id=plan.id,
        approved_count=plan.approved_count,
        rejected_count=plan.rejected_count,
        deferred_count=plan.deferred_count,
    )


@app.post("/execute/plan/{plan_id}", response_model=ExecutionPlanRunResponse)
def execute(plan_id: int, db: Session = Depends(get_db)) -> ExecutionPlanRunResponse:
    try:
        plan, results = execute_plan(db, plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return ExecutionPlanRunResponse(plan_id=plan.id, status=plan.status, items=results)


@app.get("/analytics/funnel", response_model=AnalyticsFunnelResponse)
def analytics(db: Session = Depends(get_db)) -> AnalyticsFunnelResponse:
    return funnel(db)


@app.post("/orchestrator/run-daily", response_model=DailyRunResponse)
def run_daily(payload: DailyRunRequest, db: Session = Depends(get_db)) -> DailyRunResponse:
    result = run_daily_cycle(db, payload.source_config_id)
    db.commit()
    return DailyRunResponse(
        run_id=result.run_id,
        batch_id=result.batch_id,
        execution_plan_id=result.execution_plan_id,
        discovered_count=result.discovered_count,
        approved_items=result.approved_items,
        executed_items=result.executed_items,
        followups_created=result.followups_created,
        tracking_snapshot_path=result.tracking_snapshot_path,
    )


@app.get("/tracking/snapshot-path")
def tracking_snapshot_path() -> dict[str, str | bool]:
    return {"exists": TRACKING_PATH.exists(), "path": str(TRACKING_PATH)}


@app.get("/dashboard/data", response_model=DashboardDataResponse)
def dashboard_data(
    source: str | None = Query(default=None),
    geography: str | None = Query(default=None),
    role_family: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DashboardDataResponse:
    data = collect_dashboard_data(
        db, source=source, geography=geography, role_family=role_family, status=status
    )
    return DashboardDataResponse(
        kpis=data.kpis,
        job_status_counts=data.job_status_counts,
        recent_events=data.recent_events,
        followups=data.followups,
        queue_preview=data.queue_preview,
        top_targets=data.top_targets,
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jeet Job Ops Dashboard</title>
  <style>
    :root {
      --ink: #1a1d29;
      --paper: #f3efe6;
      --accent: #0e8575;
      --accent2: #f0894a;
      --muted: #6b6f7a;
      --card: #fffdf7;
      --danger: #ba1f33;
      --ok: #117744;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Space Grotesk", "Avenir Next", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 9%, #ffe9cf 0, #ffe9cf 12%, transparent 13%),
        radial-gradient(circle at 90% 18%, #d8f3ef 0, #d8f3ef 13%, transparent 14%),
        linear-gradient(160deg, #faf6ec 0%, #efe9db 100%);
      min-height: 100vh;
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 24px; }
    h1 {
      margin: 0 0 4px;
      font-size: clamp(28px, 4vw, 44px);
      letter-spacing: 0.3px;
      font-family: "Baskerville", "Times New Roman", serif;
    }
    .sub { color: var(--muted); margin-bottom: 18px; }
    .row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .card {
      background: var(--card);
      border: 1px solid #e6dfcf;
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 10px 25px rgba(20, 25, 30, 0.05);
    }
    .kpi-label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 32px; margin-top: 8px; font-weight: 700; color: var(--accent); }
    .sections {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    @media (max-width: 920px) { .sections { grid-template-columns: 1fr; } }
    h2 { margin: 0 0 8px; font-size: 18px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid #ece6d9; padding: 8px 6px; text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.4px;
    }
    .ok { background: #d8f5e7; color: var(--ok); }
    .bad { background: #ffe5e8; color: var(--danger); }
    .neutral { background: #eef0f6; color: #4a4e59; }
    .bar-wrap { display: flex; flex-direction: column; gap: 7px; }
    .bar-item { display: grid; grid-template-columns: 120px 1fr 34px; gap: 8px; align-items: center; }
    .bar-bg { height: 12px; background: #efe7d5; border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 999px; }
    .toolbar { display: flex; gap: 8px; margin: 14px 0; flex-wrap: wrap; }
    .filters {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }
    .filters input, .filters select {
      width: 100%;
      border-radius: 10px;
      border: 1px solid #d9d3c4;
      background: #fffef9;
      padding: 10px;
      font-size: 13px;
      font-family: inherit;
    }
    button {
      border: 0;
      border-radius: 10px;
      padding: 10px 13px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      background: var(--ink);
      color: #fff;
    }
    .secondary { background: #364057; }
    .stamp { color: var(--muted); font-size: 12px; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Job Ops Command Deck</h1>
    <div class="sub">Autonomous pipeline monitor: discovery, applications, outreach, follow-ups, and execution health.</div>
    <div class="toolbar">
      <button onclick="runDaily()">Run Daily Cycle</button>
      <button class="secondary" onclick="refresh()">Refresh</button>
      <span class="stamp" id="stamp">Loading…</span>
    </div>
    <div class="filters">
      <select id="sourceFilter">
        <option value="">All Sources</option>
        <option value="venture_capital_careers">Venture Capital Careers</option>
        <option value="company_site">Company Careers</option>
        <option value="wellfound">Wellfound</option>
        <option value="yc_jobs">YC Jobs</option>
        <option value="imf">IMF</option>
        <option value="devex">Devex</option>
      </select>
      <input id="geoFilter" placeholder="Geography (e.g. Mumbai, London)" />
      <select id="roleFamilyFilter">
        <option value="">All Role Families</option>
        <option value="vc">VC</option>
        <option value="consulting">Consulting</option>
        <option value="economics_ai">Economics + AI</option>
      </select>
      <select id="statusFilter">
        <option value="">All Statuses</option>
        <option value="new">New</option>
        <option value="pending_review">Pending Review</option>
        <option value="applied">Applied</option>
        <option value="outreach_sent">Outreach Sent</option>
        <option value="blocked">Blocked</option>
      </select>
    </div>
    <div class="row" id="kpis"></div>
    <div class="sections">
      <section class="card">
        <h2>Top Targets (VC / Consulting / High-Pay)</h2>
        <table>
          <thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Score</th><th>Source</th></tr></thead>
          <tbody id="top-targets"></tbody>
        </table>
      </section>
      <section class="card">
        <h2>Job Status Mix</h2>
        <div class="bar-wrap" id="status-bars"></div>
      </section>
      <section class="card">
        <h2>Follow-Ups Due</h2>
        <table>
          <thead><tr><th>Due</th><th>Company</th><th>Role</th><th>Channel</th></tr></thead>
          <tbody id="followups"></tbody>
        </table>
      </section>
      <section class="card">
        <h2>Recent Executions</h2>
        <table>
          <thead><tr><th>Time</th><th>Company</th><th>Event</th><th>Status</th></tr></thead>
          <tbody id="events"></tbody>
        </table>
      </section>
      <section class="card">
        <h2>Pending Review Queue</h2>
        <table>
          <thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Score</th><th>Source</th></tr></thead>
          <tbody id="queue"></tbody>
        </table>
      </section>
    </div>
  </div>
<script>
const fmt = (iso) => new Date(iso).toLocaleString();
const esc = (s) => (s ?? "").toString().replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const badge = (status) => {
  const s = (status || "").toLowerCase();
  const cls = s.includes("success") ? "ok" : (s.includes("failed") || s.includes("blocked")) ? "bad" : "neutral";
  return `<span class="pill ${cls}">${esc(status)}</span>`;
};

async function runDaily() {
  await fetch("/orchestrator/run-daily", {
    method: "POST",
    headers: {"content-type":"application/json"},
    body: JSON.stringify({source_config_id: "dashboard-trigger"})
  });
  await refresh();
}

async function refresh() {
  const params = new URLSearchParams();
  const source = document.getElementById("sourceFilter").value.trim();
  const geo = document.getElementById("geoFilter").value.trim();
  const roleFamily = document.getElementById("roleFamilyFilter").value.trim();
  const status = document.getElementById("statusFilter").value.trim();
  if (source) params.set("source", source);
  if (geo) params.set("geography", geo);
  if (roleFamily) params.set("role_family", roleFamily);
  if (status) params.set("status", status);
  const qs = params.toString();
  const res = await fetch("/dashboard/data" + (qs ? `?${qs}` : ""));
  const data = await res.json();
  document.getElementById("stamp").textContent = "Last refresh: " + new Date().toLocaleTimeString();

  const kpiMap = [
    ["Total Jobs", data.kpis.total_jobs ?? 0],
    ["Applied", data.kpis.applied_jobs ?? 0],
    ["Pending Review", data.kpis.pending_review_items ?? 0],
    ["Pending Follow-Ups", data.kpis.pending_followups ?? 0],
    ["Active Batches", data.kpis.active_batches ?? 0],
  ];
  document.getElementById("kpis").innerHTML = kpiMap.map(([k, v]) => `
    <article class="card"><div class="kpi-label">${esc(k)}</div><div class="kpi-value">${v}</div></article>
  `).join("");

  const statuses = Object.entries(data.job_status_counts || {});
  const max = Math.max(...statuses.map(([_,v]) => v), 1);
  document.getElementById("status-bars").innerHTML = statuses.map(([name, count]) => `
    <div class="bar-item">
      <div>${esc(name)}</div>
      <div class="bar-bg"><div class="bar-fill" style="width:${(count/max)*100}%"></div></div>
      <div>${count}</div>
    </div>
  `).join("") || "<div class='sub'>No jobs yet.</div>";

  document.getElementById("top-targets").innerHTML = (data.top_targets || []).map(row => `
    <tr><td>${esc(row.company)}</td><td>${esc(row.title)}</td><td>${esc(row.location)}</td><td>${row.score}</td><td>${esc(row.source)}</td></tr>
  `).join("") || "<tr><td colspan='5'>No top targets for current filters.</td></tr>";

  document.getElementById("followups").innerHTML = (data.followups || []).map(row => `
    <tr><td>${fmt(row.due_at)}</td><td>${esc(row.company)}</td><td>${esc(row.title)}</td><td>${esc(row.channel)}</td></tr>
  `).join("") || "<tr><td colspan='4'>No pending follow-ups.</td></tr>";

  document.getElementById("events").innerHTML = (data.recent_events || []).map(row => `
    <tr><td>${fmt(row.created_at)}</td><td>${esc(row.company)}</td><td>${esc(row.event_type)}</td><td>${badge(row.status)}</td></tr>
  `).join("") || "<tr><td colspan='4'>No execution events yet.</td></tr>";

  document.getElementById("queue").innerHTML = (data.queue_preview || []).map(row => `
    <tr><td>${esc(row.company)}</td><td>${esc(row.title)}</td><td>${esc(row.location)}</td><td>${row.score}</td><td>${esc(row.source)}</td></tr>
  `).join("") || "<tr><td colspan='5'>No queue items.</td></tr>";
}

refresh();
["sourceFilter","geoFilter","roleFamilyFilter","statusFilter"].forEach((id) => {
  document.getElementById(id).addEventListener("change", refresh);
  document.getElementById(id).addEventListener("input", refresh);
});
setInterval(refresh, 30000);
</script>
</body>
</html>"""
