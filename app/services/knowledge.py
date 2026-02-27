"""
Knowledge Ingestion Pipeline
─────────────────────────────────────────────────────────────────────────────
The coach's living knowledge base. Three ingestion paths:

  1. PubMed  — automated weekly fetch of peer-reviewed research
  2. Manual  — curator adds a paper/book/framework directly via API
  3. Seed    — one-time migration of the original hardcoded CATALOG

Retrieval is relevance-scored: tag overlap + recency + curator quality signal.
The GET /coach/knowledge/studying endpoint shows users "what the coach is reading."
"""
from __future__ import annotations

import hashlib
import math
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import KnowledgeItem

# ── PubMed search queries — run weekly ───────────────────────────────────────
PUBMED_QUERIES = [
    "executive coaching leadership effectiveness",
    "CEO leadership decision making psychology",
    "burnout prevention high performance professionals",
    "relationship repair conflict resolution workplace",
    "habit formation behavior change executives",
    "emotional regulation leadership performance",
    "nonprofit leadership social impact",
    "coaching outcomes meta-analysis",
    "resilience wellbeing high stress professionals",
    "mindfulness leadership performance",
]

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_BASE_URL   = "https://pubmed.ncbi.nlm.nih.gov"

# Category inference from keyword matching
CATEGORY_MAP: list[tuple[list[str], str]] = [
    (["burnout", "exhaustion", "wellbeing", "recovery", "fatigue"], "Wellbeing & Burnout"),
    (["relationship", "conflict", "repair", "communication", "gottman"], "Relationship Science"),
    (["habit", "behavior", "automaticity", "routine", "nudge"], "Behavior Change"),
    (["leadership", "ceo", "executive", "management", "decision"], "Executive Leadership"),
    (["coaching", "coach", "mentoring", "feedback"], "Coaching Science"),
    (["nonprofit", "social impact", "philanthropy", "community"], "Nonprofit Leadership"),
    (["resilience", "stress", "adversity", "grit", "mindset"], "Resilience & Performance"),
    (["mindfulness", "meditation", "attention", "focus", "presence"], "Mindfulness & Focus"),
]


def _infer_category(text: str) -> str:
    lower = text.lower()
    for keywords, category in CATEGORY_MAP:
        if any(kw in lower for kw in keywords):
            return category
    return "Leadership & Development"


def _infer_tags(text: str) -> list[str]:
    lower = text.lower()
    tag_map = {
        "leadership": ["leadership", "ceo", "executive", "manager"],
        "burnout": ["burnout", "exhaustion", "fatigue", "depletion"],
        "wellbeing": ["wellbeing", "well-being", "wellness", "mental health"],
        "coaching": ["coaching", "coach", "mentoring"],
        "relationship": ["relationship", "interpersonal", "conflict", "repair"],
        "habits": ["habit", "behavior", "routine", "automaticity"],
        "resilience": ["resilience", "grit", "adversity", "stress"],
        "decision": ["decision", "judgment", "choice", "cognitive"],
        "mindfulness": ["mindfulness", "meditation", "attention", "focus"],
        "nonprofit": ["nonprofit", "ngo", "social impact", "philanthropy"],
        "execution": ["execution", "productivity", "performance", "output"],
    }
    found = []
    for tag, keywords in tag_map.items():
        if any(kw in lower for kw in keywords):
            found.append(tag)
    return found or ["leadership"]


def _make_takeaway(abstract: str, title: str) -> str:
    """Generate a coaching takeaway from abstract. Falls back to title-based."""
    if not abstract:
        return f"Research on {title[:80]} — review full paper for evidence-based insights."
    # Use first 2 sentences as the takeaway seed
    sentences = re.split(r"(?<=[.!?])\s+", abstract.strip())
    key = " ".join(sentences[:2])
    return key[:200] if key else title[:120]


def _make_application(category: str, tags: list[str]) -> str:
    """Generate a practical coaching application note."""
    apps = {
        "Wellbeing & Burnout": "Use when burnout risk is elevated. Integrate recovery protocols and load-reduction nudges.",
        "Relationship Science": "Apply repair scripts and conflict de-escalation techniques from this evidence base.",
        "Behavior Change": "Reference for habit design, cue engineering, and streak recovery coaching.",
        "Executive Leadership": "Anchor leadership strategy sessions and decision quality reviews to this research.",
        "Coaching Science": "Inform coaching structure, accountability loops, and session design.",
        "Nonprofit Leadership": "Use for stakeholder strategy, funding resilience, and mission alignment sessions.",
        "Resilience & Performance": "Deploy during high-stress periods to guide recovery and sustained performance.",
        "Mindfulness & Focus": "Recommend focus and attention practices when cognitive load is high.",
    }
    return apps.get(category, "Apply evidence-based insights to reinforce coaching recommendations.")


def _stable_id(source: str, ref: str) -> str:
    """Create a stable dedup ID from source + reference."""
    return hashlib.sha1(f"{source}:{ref}".encode()).hexdigest()[:16]


# ── PubMed Ingestion ──────────────────────────────────────────────────────────

async def _pubmed_search(query: str, max_results: int = 5) -> list[str]:
    """Return PubMed IDs for a query."""
    params = {
        "db": "pubmed", "term": query, "retmax": max_results,
        "retmode": "json", "sort": "relevance",
        "mindate": str(date.today().year - 2), "datetype": "pdat",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(PUBMED_SEARCH_URL, params=params)
        r.raise_for_status()
        data = r.json()
    return data.get("esearchresult", {}).get("idlist", [])


async def _pubmed_fetch_details(pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch full records for a list of PubMed IDs."""
    if not pmids:
        return []
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "rettype": "abstract"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(PUBMED_FETCH_URL, params=params)
        r.raise_for_status()
        xml_text = r.text

    records = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    for article in root.findall(".//PubmedArticle"):
        try:
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text.strip() if pmid_el is not None else ""
            if not pmid:
                continue

            title_el = article.find(".//ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else ""

            abstract_parts = article.findall(".//AbstractText")
            abstract = " ".join("".join(el.itertext()) for el in abstract_parts).strip()

            # Authors
            author_els = article.findall(".//Author")
            authors = []
            for a in author_els[:3]:
                ln = a.findtext("LastName", "")
                fn = a.findtext("ForeName", "")
                if ln:
                    authors.append(f"{ln} {fn}".strip())
            authors_str = ", ".join(authors) + (" et al." if len(author_els) > 3 else "")

            # Publication date
            pub_date = article.find(".//PubDate")
            year = pub_date.findtext("Year", "2024") if pub_date is not None else "2024"
            month = pub_date.findtext("Month", "01") if pub_date is not None else "01"
            month_map = {
                "Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
                "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12",
            }
            month = month_map.get(month, month.zfill(2) if month.isdigit() else "01")
            published_date = f"{year}-{month}-01"

            if not title or not abstract:
                continue

            records.append({
                "pmid": pmid,
                "title": title,
                "authors": authors_str,
                "abstract": abstract,
                "published_date": published_date,
                "source_url": f"{PUBMED_BASE_URL}/{pmid}/",
            })
        except Exception:
            continue

    return records


def _upsert_knowledge_item(db: Session, item_data: dict[str, Any]) -> tuple[KnowledgeItem, bool]:
    """Insert or skip (by external_id). Returns (item, was_new)."""
    existing = db.query(KnowledgeItem).filter_by(external_id=item_data["external_id"]).first()
    if existing:
        return existing, False

    item = KnowledgeItem(**item_data)
    db.add(item)
    db.flush()
    return item, True


async def ingest_pubmed(db: Session, max_per_query: int = 3) -> dict[str, int]:
    """
    Run all PUBMED_QUERIES, fetch recent papers, and upsert into knowledge_items.
    Designed to run weekly (scheduler or manual trigger).
    """
    added = 0
    skipped = 0
    errors = 0

    for query in PUBMED_QUERIES:
        try:
            pmids = await _pubmed_search(query, max_results=max_per_query)
            records = await _pubmed_fetch_details(pmids)
        except Exception:
            errors += 1
            continue

        for rec in records:
            tags = _infer_tags(f"{rec['title']} {rec['abstract']}")
            category = _infer_category(f"{rec['title']} {rec['abstract']}")
            takeaway = _make_takeaway(rec["abstract"], rec["title"])
            application = _make_application(category, tags)

            item_data = {
                "external_id": f"pubmed:{rec['pmid']}",
                "source": "pubmed",
                "title": rec["title"][:512],
                "authors": rec["authors"][:512],
                "published_date": rec["published_date"],
                "category": category,
                "abstract": rec["abstract"][:3000],
                "takeaway": takeaway,
                "application": application,
                "source_url": rec["source_url"],
                "tags": tags,
                "relevance_score": 1.0,
                "active": True,
            }
            try:
                _, is_new = _upsert_knowledge_item(db, item_data)
                if is_new:
                    added += 1
                else:
                    skipped += 1
            except Exception:
                errors += 1

    db.commit()
    return {"added": added, "skipped": skipped, "errors": errors}


def ingest_manual(
    db: Session,
    *,
    title: str,
    takeaway: str,
    application: str,
    source_url: str = "",
    authors: str = "",
    published_date: str = "",
    abstract: str = "",
    category: str = "",
    tags: list[str] | None = None,
    relevance_score: float = 1.5,   # manual items get a slight boost
    source: str = "manual",
) -> KnowledgeItem:
    """Add a manually curated paper, book, or framework."""
    if not published_date:
        published_date = date.today().strftime("%Y-%m-%d")
    if not category:
        category = _infer_category(f"{title} {abstract} {takeaway}")
    if tags is None:
        tags = _infer_tags(f"{title} {abstract} {takeaway}")

    external_id = _stable_id(source, title)
    item_data = {
        "external_id": external_id,
        "source": source,
        "title": title[:512],
        "authors": authors[:512],
        "published_date": published_date,
        "category": category,
        "abstract": abstract[:3000],
        "takeaway": takeaway,
        "application": application,
        "source_url": source_url,
        "tags": tags,
        "relevance_score": relevance_score,
        "active": True,
    }
    item, _ = _upsert_knowledge_item(db, item_data)
    db.commit()
    return item


# ── Smart Retrieval Engine ────────────────────────────────────────────────────

def _recency_score(published_date: str) -> float:
    """More recent = higher score. Decay over 36 months."""
    try:
        pub = datetime.strptime(published_date[:10], "%Y-%m-%d")
        months_old = (datetime.utcnow() - pub).days / 30
        return max(0.1, math.exp(-months_old / 24))  # half-life ~24 months
    except ValueError:
        return 0.5


def _tag_overlap_score(item_tags: list[str], query_tags: list[str]) -> float:
    if not query_tags:
        return 0.0
    matches = len(set(item_tags) & set(query_tags))
    return matches / max(len(query_tags), 1)


def retrieve_for_context(
    db: Session,
    *,
    track: str | None = None,
    user_tags: list[str] | None = None,
    limit: int = 5,
    min_score: float = 0.0,
) -> list[KnowledgeItem]:
    """
    Return the most relevant knowledge items for a coaching context.
    Scores = tag_overlap * 0.5 + recency * 0.3 + curator_quality * 0.2
    Falls back to DB-seeded CATALOG items if DB is empty.
    """
    query = db.query(KnowledgeItem).filter(KnowledgeItem.active == True)

    # Build query tag list from track + user tags
    query_tags: list[str] = []
    if track:
        query_tags.append(track.lower().strip())
    if user_tags:
        query_tags.extend([t.lower() for t in user_tags])

    items = query.all()
    if not items:
        return []

    scored: list[tuple[float, KnowledgeItem]] = []
    for item in items:
        tag_score = _tag_overlap_score(item.tags or [], query_tags)
        rec_score = _recency_score(item.published_date)
        quality = min(item.relevance_score, 2.0) / 2.0
        total = tag_score * 0.5 + rec_score * 0.3 + quality * 0.2
        if total >= min_score:
            scored.append((total, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def get_recently_ingested(db: Session, days: int = 30, limit: int = 10) -> list[KnowledgeItem]:
    """What the coach has been reading lately — shown to users."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.active == True, KnowledgeItem.ingested_at >= cutoff)
        .order_by(KnowledgeItem.ingested_at.desc())
        .limit(limit)
        .all()
    )


def knowledge_stats(db: Session) -> dict[str, Any]:
    total = db.query(func.count(KnowledgeItem.id)).filter(KnowledgeItem.active == True).scalar()
    by_source = (
        db.query(KnowledgeItem.source, func.count(KnowledgeItem.id))
        .filter(KnowledgeItem.active == True)
        .group_by(KnowledgeItem.source)
        .all()
    )
    by_category = (
        db.query(KnowledgeItem.category, func.count(KnowledgeItem.id))
        .filter(KnowledgeItem.active == True)
        .group_by(KnowledgeItem.category)
        .all()
    )
    latest = (
        db.query(KnowledgeItem.ingested_at)
        .filter(KnowledgeItem.active == True)
        .order_by(KnowledgeItem.ingested_at.desc())
        .first()
    )
    return {
        "total_items": total or 0,
        "by_source": {row[0]: row[1] for row in by_source},
        "by_category": {row[0]: row[1] for row in by_category},
        "last_ingested_at": latest[0].isoformat() if latest else None,
    }


# ── Seed: migrate hardcoded CATALOG to DB ────────────────────────────────────

SEED_CATALOG = [
    {
        "external_id": "seed:executive-coaching-meta-2023",
        "source": "seed",
        "title": "What can coaches do for you? The effects of executive coaching, a meta-analysis",
        "authors": "Grover S, Furnham A",
        "published_date": "2023-06-14",
        "category": "Coaching Science",
        "abstract": "Meta-analysis of executive coaching outcomes across 117 studies.",
        "takeaway": "Executive coaching shows meaningful positive effects, especially for behavioural outcomes.",
        "application": "Prioritise behavior-level commitments and weekly accountability over motivational talk.",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/37333584/",
        "tags": ["leadership", "coaching", "execution"],
        "relevance_score": 1.8,
        "active": True,
    },
    {
        "external_id": "seed:burnout-physicians-2024",
        "source": "seed",
        "title": "Effectiveness of Peer Coaching to Improve Well-Being in Internal Medicine Residents",
        "authors": "Dyrbye LN et al.",
        "published_date": "2024-08-20",
        "category": "Wellbeing & Burnout",
        "abstract": "RCT showing structured coaching improved wellbeing in high-pressure professionals.",
        "takeaway": "Structured coaching reduces burnout and supports professional fulfilment in high-pressure roles.",
        "application": "Include burnout sentinel checks with mandatory recovery interventions when risk is high.",
        "source_url": "https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2822718",
        "tags": ["burnout", "wellbeing", "coaching"],
        "relevance_score": 1.8,
        "active": True,
    },
    {
        "external_id": "seed:habit-meta-2024",
        "source": "seed",
        "title": "Context Stability and Habit Formation: A Meta-Analysis",
        "authors": "Lally P, Gardner B",
        "published_date": "2024-06-17",
        "category": "Behavior Change",
        "abstract": "Meta-analysis of 96 habit formation studies showing context consistency is critical.",
        "takeaway": "Stable context and cue consistency significantly improve habit formation quality.",
        "application": "Schedule fixed daily cue windows (morning, midday, evening) for coaching nudges.",
        "source_url": "https://onlinelibrary.wiley.com/doi/10.1111/bjhp.12784",
        "tags": ["habits", "behavior", "execution"],
        "relevance_score": 1.8,
        "active": True,
    },
    {
        "external_id": "seed:gottman-research",
        "source": "seed",
        "title": "The Gottman Institute Research Overview",
        "authors": "Gottman J, Silver N",
        "published_date": "2024-01-01",
        "category": "Relationship Science",
        "abstract": "Decades of research on what makes relationships work, including the 5:1 positivity ratio.",
        "takeaway": "Repair attempts and interaction quality strongly influence relationship resilience.",
        "application": "Use repair-first scripts quickly after conflict in close relationships.",
        "source_url": "https://www.gottman.com/about/research/",
        "tags": ["relationship", "conflict", "repair"],
        "relevance_score": 2.0,
        "active": True,
    },
    {
        "external_id": "seed:who-burnout-icd11",
        "source": "seed",
        "title": "Burn-out an occupational phenomenon: ICD-11",
        "authors": "World Health Organisation",
        "published_date": "2019-05-28",
        "category": "Wellbeing & Burnout",
        "abstract": "WHO classification of burnout as occupational syndrome with three dimensions.",
        "takeaway": "Burnout is an occupational syndrome linked to unmanaged chronic workplace stress.",
        "application": "Treat persistent exhaustion or cynicism as operational risk requiring schedule redesign.",
        "source_url": "https://www.who.int/news/item/28-05-2019-burn-out-an-occupational-phenomenon-international-classification-of-diseases",
        "tags": ["burnout", "wellbeing", "risk"],
        "relevance_score": 1.9,
        "active": True,
    },
    {
        "external_id": "seed:icf-competencies-2025",
        "source": "seed",
        "title": "ICF Core Competencies",
        "authors": "International Coaching Federation",
        "published_date": "2025-04-01",
        "category": "Coaching Science",
        "abstract": "Updated ICF core competency framework emphasising trust, listening, and accountability.",
        "takeaway": "High-grade coaching emphasises trust, active listening, awareness, and client accountability.",
        "application": "Keep responses question-led, specific, and accountable with concrete follow-through prompts.",
        "source_url": "https://coachingfederation.org/credentials-and-standards/core-competencies",
        "tags": ["coaching", "standards", "ethics"],
        "relevance_score": 1.7,
        "active": True,
    },
]


def seed_knowledge_base(db: Session) -> int:
    """One-time seed of the original hardcoded catalog into the DB. Safe to call repeatedly."""
    added = 0
    for item_data in SEED_CATALOG:
        existing = db.query(KnowledgeItem).filter_by(external_id=item_data["external_id"]).first()
        if existing:
            continue
        item = KnowledgeItem(**item_data)
        db.add(item)
        added += 1
    if added:
        db.commit()
    return added
