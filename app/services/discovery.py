from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateProfile, DiscoveryRun, JobRecord, TargetingPolicy
from app.services.audit import log_event
from app.services.scoring import relevance_score, should_block_job


@dataclass
class SourceJob:
    source: str
    source_job_id: str
    company: str
    title: str
    location: str
    apply_url: str
    description: str
    required_skills: list[str]
    cover_letter_required: bool


def _fingerprint(company: str, title: str, location: str, apply_url: str) -> str:
    parsed = urlparse(apply_url)
    normalized = f"{company.strip().lower()}|{title.strip().lower()}|{location.strip().lower()}|{parsed.netloc.lower()}{parsed.path.lower()}"
    return sha256(normalized.encode("utf-8")).hexdigest()


def _mock_source_jobs(source_config_id: str) -> list[SourceJob]:
    # Deterministic fixture data to allow repeatable testing and local runs.
    seed = source_config_id.strip().lower()
    return [
        SourceJob(
            source="venture_capital_careers",
            source_job_id=f"{seed}-vc-1",
            company="NorthBridge Ventures",
            title="Investment Analyst (Economics + AI)",
            location="London, UK",
            apply_url="https://jobs.northbridge.vc/investment-analyst",
            description="Evaluate AI-native businesses, macro trends, incentives, and market dynamics for portfolio investment decisions.",
            required_skills=["economics", "research", "market analysis", "excel"],
            cover_letter_required=False,
        ),
        SourceJob(
            source="company_site",
            source_job_id=f"{seed}-co-2",
            company="Aurum Strategy Partners",
            title="Economic Consulting Analyst",
            location="Mumbai, India",
            apply_url="https://careers.aurumstrategy.com/econ-analyst",
            description="Support consulting engagements across public policy, incentives design, and market strategy.",
            required_skills=["econometrics", "stata", "excel", "policy analysis"],
            cover_letter_required=True,
        ),
        # Duplicate of first job from another source.
        SourceJob(
            source="wellfound",
            source_job_id=f"{seed}-wf-3",
            company="NorthBridge Ventures",
            title="Investment Analyst (Economics + AI)",
            location="London, UK",
            apply_url="https://jobs.northbridge.vc/investment-analyst?src=wellfound",
            description="Evaluate AI-native businesses, macro trends, incentives, and market dynamics for portfolio investment decisions.",
            required_skills=["economics", "research", "market analysis", "excel"],
            cover_letter_required=False,
        ),
        SourceJob(
            source="imf",
            source_job_id=f"{seed}-imf-4",
            company="International Monetary Fund",
            title="Research Officer - Emerging Markets",
            location="Washington, US",
            apply_url="https://careers.imf.org/research-officer",
            description="Economic policy analysis, macro monitoring, and writing for institutional audiences.",
            required_skills=["economics", "research", "policy analysis", "stata"],
            cover_letter_required=True,
        ),
        SourceJob(
            source="yc_jobs",
            source_job_id=f"{seed}-yc-5",
            company="SignalStack AI",
            title="Strategy Analyst (AI Markets)",
            location="Remote, International",
            apply_url="https://jobs.signalstack.ai/strategy-analyst",
            description="Translate AI product and market data into strategic recommendations for growth.",
            required_skills=["economics", "strategy", "excel", "research"],
            cover_letter_required=False,
        ),
        SourceJob(
            source="devex",
            source_job_id=f"{seed}-dx-6",
            company="Global Development Advisory",
            title="Policy and Economic Analyst",
            location="Gurugram, India",
            apply_url="https://jobs.gda.example/policy-analyst",
            description="Policy analytics for development finance clients; incentives and institutional analysis.",
            required_skills=["policy analysis", "economics", "excel", "writing"],
            cover_letter_required=True,
        ),
    ]


def run_discovery(db: Session, source_config_id: str) -> DiscoveryRun:
    profile = db.scalar(
        select(CandidateProfile).order_by(CandidateProfile.version.desc()).limit(1)
    )
    policy = None
    if profile:
        policy = db.scalar(
            select(TargetingPolicy)
            .where(TargetingPolicy.profile_version == profile.version)
            .order_by(TargetingPolicy.id.desc())
            .limit(1)
        )

    run = DiscoveryRun(source_config_id=source_config_id, discovered_count=0, deduped_count=0)
    db.add(run)
    db.flush()

    source_jobs = _mock_source_jobs(source_config_id)
    run.discovered_count = len(source_jobs)
    deduped = 0

    for raw in source_jobs:
        fp = _fingerprint(raw.company, raw.title, raw.location, raw.apply_url)
        existing = db.scalar(select(JobRecord).where(JobRecord.fingerprint == fp).limit(1))
        if existing:
            deduped += 1
            continue

        job = JobRecord(
            source=raw.source,
            source_job_id=raw.source_job_id,
            company=raw.company,
            title=raw.title,
            location=raw.location,
            apply_url=raw.apply_url,
            description=raw.description,
            required_skills=raw.required_skills,
            cover_letter_required=raw.cover_letter_required,
            fingerprint=fp,
            raw_data=raw.__dict__,
        )

        if should_block_job(job, policy):
            job.status = "blocked"
        else:
            job.relevance_score = relevance_score(job, profile, policy)
            job.status = "new"

        db.add(job)
        db.flush()
        log_event(
            db,
            entity_type="job_record",
            entity_id=job.id,
            action="discovered",
            details={"source": raw.source, "score": job.relevance_score, "status": job.status},
        )

    run.deduped_count = deduped
    log_event(
        db,
        entity_type="discovery_run",
        entity_id=run.id,
        action="completed",
        details={"source_config_id": source_config_id, "count": run.discovered_count, "deduped": deduped},
    )
    return run
