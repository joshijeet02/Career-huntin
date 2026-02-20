from app.models import CandidateProfile, JobRecord, TargetingPolicy
from app.services.profile_config import get_execution_preferences, get_source_weights


def should_block_job(job: JobRecord, policy: TargetingPolicy | None) -> bool:
    if policy is None:
        return False

    company_blocked = job.company.lower() in {c.lower() for c in policy.suppression_companies}
    if company_blocked:
        return True

    domain_blocked = any(domain.lower() in job.apply_url.lower() for domain in policy.suppression_domains)
    if domain_blocked:
        return True

    if not job.title.strip() or not job.company.strip():
        return True

    return False


def relevance_score(job: JobRecord, profile: CandidateProfile | None, policy: TargetingPolicy | None) -> float:
    score = 0.0
    if profile is None:
        return score

    profile_skills = {skill.strip().lower() for skill in profile.skills}
    required = {skill.strip().lower() for skill in (job.required_skills or [])}
    if required:
        overlap = len(profile_skills & required) / max(len(required), 1)
        score += overlap * 60.0
    else:
        score += 20.0

    if policy and policy.role_families:
        families = [item.lower() for item in policy.role_families]
        if any(fam in job.title.lower() for fam in families):
            score += 20.0

    pref_remote = bool(profile.preferences.get("remote_preferred", False))
    if pref_remote and "remote" in job.location.lower():
        score += 10.0

    if job.cover_letter_required:
        score += 2.0

    source_bonus = get_source_weights().get(job.source, 0.0)
    score += source_bonus

    pref = get_execution_preferences()
    geo_priority = pref.get("geography_priority_order", [])
    intl_priority = pref.get("international_priority_order", [])
    loc = job.location.lower()
    if any(city.lower() in loc for city in geo_priority if city != "International"):
        score += 12.0
    elif "international" in geo_priority and not any(
        city.lower() in loc for city in ("mumbai", "gurugram", "bangalore")
    ):
        score += 6.0
    if any(country.lower() in loc for country in intl_priority):
        score += 8.0

    title = job.title.lower()
    desc = job.description.lower()
    if "venture" in title or "vc" in title or "venture capital" in desc:
        score += 15.0
    if "econom" in title or "policy" in title or "strategy" in title:
        score += 10.0
    if "ai" in title or "llm" in desc or "automation" in desc:
        score += 8.0

    return round(min(score, 100.0), 2)
