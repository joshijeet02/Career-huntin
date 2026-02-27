from __future__ import annotations

from dataclasses import dataclass

from app.schemas import PremiumFeatureOut, PremiumTierOut, ResearchInsightOut


@dataclass(frozen=True)
class ResearchInsight:
    id: str
    title: str
    published_date: str
    category: str
    takeaway: str
    application: str
    source_url: str
    tags: tuple[str, ...]


CATALOG: tuple[ResearchInsight, ...] = (
    ResearchInsight(
        id="executive-coaching-meta-2023",
        title="What can coachs do for you? The effects of executive coaching, a metaanalysis",
        published_date="2023-06-14",
        category="Executive Coaching",
        takeaway="Executive coaching shows meaningful positive effects, especially for behavioral outcomes.",
        application="Prioritize behavior-level commitments and weekly accountability over motivational talk.",
        source_url="https://pubmed.ncbi.nlm.nih.gov/37333584/",
        tags=("leadership", "coaching", "execution"),
    ),
    ResearchInsight(
        id="peer-coaching-physicians-2024",
        title="Effectiveness of Peer Coaching to Improve Well-Being in Internal Medicine Residents",
        published_date="2024-08-20",
        category="Wellbeing",
        takeaway="Structured coaching can improve wellbeing-related indicators in high-pressure professional contexts.",
        application="Use concise peer-style reflection and stress reset loops during overloaded days.",
        source_url="https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2822718",
        tags=("wellbeing", "burnout", "coaching"),
    ),
    ResearchInsight(
        id="group-coaching-rct-2024",
        title="The Efficacy of Group Coaching for Burnout and Professional Fulfillment in Family Physicians",
        published_date="2024-05-17",
        category="Burnout",
        takeaway="Coaching structures can reduce burnout and support professional fulfillment in clinical leadership roles.",
        application="Include burnout sentinel checks with mandatory recovery interventions when risk is high.",
        source_url="https://www.jabfm.org/content/37/3/440",
        tags=("burnout", "wellbeing", "leadership"),
    ),
    ResearchInsight(
        id="habit-meta-review-2024",
        title="Context Stability and Habit Formation: A Meta-Analysis",
        published_date="2024-06-17",
        category="Behavior Change",
        takeaway="Stable context and cue consistency improve habit formation quality.",
        application="Schedule fixed daily cue windows (morning, midday, evening) for coaching nudges.",
        source_url="https://onlinelibrary.wiley.com/doi/10.1111/bjhp.12784",
        tags=("habits", "behavior", "execution"),
    ),
    ResearchInsight(
        id="habit-timescale-2023",
        title="Predicting goal progress from automaticity trajectories",
        published_date="2023-01-03",
        category="Behavior Change",
        takeaway="Habit formation timelines vary significantly across behavior complexity and context.",
        application="Use minimum viable actions on tough days while tracking trend progress over weeks.",
        source_url="https://www.pnas.org/doi/10.1073/pnas.2215676120",
        tags=("habits", "goal-setting", "execution"),
    ),
    ResearchInsight(
        id="urban-nonprofit-leader-2025",
        title="Nonprofit leaders started 2025 worried about funding and policy shifts",
        published_date="2025-03-25",
        category="Nonprofit Leadership",
        takeaway="Funding instability and policy uncertainty are major pressure multipliers for nonprofit leaders.",
        application="Anchor weekly strategy reviews to risk-adjusted funding and stakeholder scenarios.",
        source_url="https://www.urban.org/urban-wire/nonprofit-leaders-started-2025-worried-about-funding-and-policy-shifts",
        tags=("nonprofit", "strategy", "leadership"),
    ),
    ResearchInsight(
        id="icf-competencies-2025",
        title="ICF Core Competencies",
        published_date="2025-04-01",
        category="Coaching Standards",
        takeaway="High-grade coaching emphasizes trust, active listening, awareness, and client accountability.",
        application="Keep responses question-led, specific, and accountable with concrete follow-through prompts.",
        source_url="https://coachingfederation.org/credentials-and-standards/core-competencies",
        tags=("coaching", "standards", "ethics"),
    ),
    ResearchInsight(
        id="icf-ethics-2025",
        title="ICF Code of Ethics (effective April 1, 2025)",
        published_date="2025-04-01",
        category="Coaching Standards",
        takeaway="Confidentiality, boundaries, and role clarity are non-negotiable coaching requirements.",
        application="Maintain strict privacy controls and explicit scope for coaching vs. therapy or legal advice.",
        source_url="https://coachingfederation.org/code-of-ethics-overview/",
        tags=("coaching", "ethics", "security"),
    ),
    ResearchInsight(
        id="who-burnout-icd11",
        title="Burn-out an occupational phenomenon: ICD-11",
        published_date="2019-05-28",
        category="Wellbeing",
        takeaway="Burnout is an occupational syndrome linked to unmanaged chronic workplace stress.",
        application="Treat persistent exhaustion/cynicism signals as operational risk requiring schedule redesign.",
        source_url="https://www.who.int/news/item/28-05-2019-burn-out-an-occupational-phenomenon-international-classification-of-diseases",
        tags=("burnout", "wellbeing", "risk"),
    ),
    ResearchInsight(
        id="gottman-research",
        title="The Gottman Institute Research Overview",
        published_date="2024-01-01",
        category="Relationship Science",
        takeaway="Repair attempts and interaction quality strongly influence relationship resilience.",
        application="Use repair-first scripts quickly after conflict in close relationships.",
        source_url="https://www.gottman.com/about/research/",
        tags=("relationship", "conflict", "repair"),
    ),
)


def _to_schema(item: ResearchInsight) -> ResearchInsightOut:
    return ResearchInsightOut(
        id=item.id,
        title=item.title,
        published_date=item.published_date,
        category=item.category,
        takeaway=item.takeaway,
        application=item.application,
        source_url=item.source_url,
    )


def latest_insights(limit: int = 5, track: str | None = None) -> list[ResearchInsightOut]:
    data = list(CATALOG)
    if track:
        t = track.lower().strip()
        data = [item for item in data if t in item.tags]
        if not data:
            data = list(CATALOG)
    data.sort(key=lambda item: item.published_date, reverse=True)
    return [_to_schema(item) for item in data[: max(limit, 1)]]


def spotlight_for_track(track: str) -> ResearchInsightOut:
    options = latest_insights(limit=3, track=track)
    if options:
        return options[0]
    return _to_schema(CATALOG[0])


def premium_tiers() -> list[PremiumTierOut]:
    tier_1k = PremiumTierOut(
        tier_name="Executive Core",
        price_usd_per_month=1000,
        ideal_for="A single CEO who needs disciplined daily coaching and relationship resilience",
        features=[
            PremiumFeatureOut(
                name="Adaptive Daily Operating Plan",
                description="Mood-aware and schedule-aware daily action plan with minimum viable fallback actions.",
                delivery_frequency="Daily",
                evidence_ids=["habit-meta-review-2024", "who-burnout-icd11"],
            ),
            PremiumFeatureOut(
                name="Relationship Repair Guidance",
                description="Conflict de-escalation and repair scripts for personal and professional relationships.",
                delivery_frequency="On demand",
                evidence_ids=["gottman-research"],
            ),
            PremiumFeatureOut(
                name="Research Distillation Brief",
                description="Curated evidence-to-action brief focused on leadership, wellbeing, and execution.",
                delivery_frequency="Weekly",
                evidence_ids=["executive-coaching-meta-2023", "icf-competencies-2025"],
            ),
        ],
    )

    tier_10k = PremiumTierOut(
        tier_name="Chairman Concierge",
        price_usd_per_month=10000,
        ideal_for="Mission-critical leaders who expect a full decision, relationship, and resilience operating system",
        features=[
            PremiumFeatureOut(
                name="Strategic Decision Intelligence",
                description="Decision quality checks with pre-mortems, stakeholder framing, and execution ownership paths.",
                delivery_frequency="Per major decision",
                evidence_ids=["executive-coaching-meta-2023", "urban-nonprofit-leader-2025"],
            ),
            PremiumFeatureOut(
                name="Board and Donor Communication Coach",
                description="High-stakes communication prep with calibrated narratives and ask clarity.",
                delivery_frequency="Weekly",
                evidence_ids=["icf-competencies-2025", "urban-nonprofit-leader-2025"],
            ),
            PremiumFeatureOut(
                name="Burnout and Recovery Command Loop",
                description="Continuous strain monitoring with intervention protocols and schedule redesign suggestions.",
                delivery_frequency="Daily",
                evidence_ids=["who-burnout-icd11", "group-coaching-rct-2024"],
            ),
            PremiumFeatureOut(
                name="Encrypted Leadership Journal",
                description="Confidential coaching memory with retention-controlled and encrypted storage.",
                delivery_frequency="Continuous",
                evidence_ids=["icf-ethics-2025"],
            ),
        ],
    )

    return [tier_1k, tier_10k]
