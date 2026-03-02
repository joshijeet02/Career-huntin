import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import SpiritualWisdom, UserProfile
from app.schemas import (
    CoachConversationHistoryItem,
    CoachConversationMessageRequest,
    CoachConversationMessageResponse,
    CoachNotebookEntryResponse,
    CoachRequest,
    CoachResponse,
    ConversationalCheckInRequest,
    ConversationalCheckInResponse,
    ConversationalCheckInStartResponse,
    DailyCheckInRequest,
    DailyCheckInResponse,
    EveningReviewQuestionsResponse,
    EveningReviewRequest,
    EveningReviewResponse,
    HabitCompleteRequest,
    HabitCreateRequest,
    HabitsResponse,
    KnowledgeIngestManualRequest,
    KnowledgeIngestResponse,
    KnowledgeItemOut,
    KnowledgeStatsResponse,
    MorningBriefResponse,
    OnboardingStatusResponse,
    OnboardingStepRequest,
    OnboardingStepResponse,
    PremiumTierOut,
    RelationshipNudge,
    ResearchInsightOut,
    RetentionPurgeResponse,
    UserProfileOut,
    VoiceCoachResponse,
    VoiceTranscriptRequest,
    WeeklyReadingAssignmentResponse,
    WeeklyReflectionRequest,
    WeeklyReflectionResponse,
)
from app.services.checkin import process_checkin
from app.services.coach import generate_coach_response
from app.services.conversational_checkin import (
    process_conversational_checkin,
    start_checkin,
)
from app.services.conversations import ConversationStore
from app.services.habits import complete_habit, create_habit, get_habits
from app.services.knowledge import (
    get_recently_ingested,
    ingest_manual,
    ingest_pubmed,
    knowledge_stats,
    retrieve_for_context,
    seed_knowledge_base,
)
from app.services.onboarding import (
    TOTAL_STEPS,
    build_persona_context,
    get_or_create_profile,
    get_next_question,
    process_onboarding_step,
)
from app.services.proactive_coach import (
    check_relationship_nudges,
    generate_coach_notebook_entry,
    generate_evening_review_questions,
    generate_morning_brief,
    get_weekly_reading_assignment,
    process_evening_review,
)
from app.services.reflection import save_weekly_reflection
from app.services.research_intel import premium_tiers
from app.services.wisdom import ask_masters, get_contextual_wisdom, seed_wisdom_corpus
from app.services.council import ask_council
from app.security import validate_request_auth


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal
    with SessionLocal() as db:
        seeded = seed_knowledge_base(db)
        if seeded:
            print(f"[startup] Knowledge base seeded with {seeded} items.")
        wisdom_seeded = seed_wisdom_corpus(db)
        if wisdom_seeded:
            print(f"[startup] Spiritual wisdom corpus seeded with {wisdom_seeded} teachings.")
    yield


app = FastAPI(
    title="Coach App API",
    version="6.0.0",
    description=(
        "Personalised AI coaching OS — onboarding, conversational check-ins, "
        "habits, proactive coaching, voice, research, conversation memory, "
        "First Read, 7-Day Trial Closing, and Memory-Aware Coach."
    ),
    lifespan=lifespan,
)

# ── CORS — allow Vercel frontend and local dev ────────────────────────────────
_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://career-huntin.vercel.app",
    "https://career-huntin-git-main-joshijeet02.vercel.app",
]
# Also allow any origin specified via env var (for production flexibility)
_extra = os.getenv("CORS_ORIGINS", "")
if _extra:
    _CORS_ORIGINS.extend([o.strip() for o in _extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conversation_store = ConversationStore()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    try:
        validate_request_auth(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root() -> dict[str, str]:
    return {"status": "running", "docs": "/docs", "version": "3.0.0"}


@app.get("/healthz", tags=["Health"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# ── Onboarding ────────────────────────────────────────────────────────────────

@app.get("/onboarding/status", response_model=OnboardingStatusResponse, tags=["Onboarding"])
def onboarding_status(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> OnboardingStatusResponse:
    profile = get_or_create_profile(db, user_id)
    profile_data = None
    if profile.onboarding_complete:
        profile_data = {
            "full_name": profile.full_name,
            "role": profile.role,
            "organization": profile.organization,
            "biggest_challenge": profile.biggest_challenge,
            "goals_90_days": profile.goals_90_days,
            "core_values": profile.core_values,
            "coaching_style_preference": profile.coaching_style_preference,
        }
    return OnboardingStatusResponse(
        user_id=user_id,
        complete=profile.onboarding_complete,
        step=profile.onboarding_step,
        total_steps=TOTAL_STEPS,
        profile=profile_data,
    )


@app.get("/onboarding/question", tags=["Onboarding"])
def onboarding_question(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> dict:
    profile = get_or_create_profile(db, user_id)
    if profile.onboarding_complete:
        return {"complete": True, "message": "Onboarding already complete."}
    q = get_next_question(profile.onboarding_step)
    if q is None:
        return {"complete": True, "message": "Onboarding already complete."}
    return {
        "complete": False,
        "step": profile.onboarding_step,
        "total_steps": TOTAL_STEPS,
        "question_text": q["question"],
        "hint": q.get("hint", ""),
        "question_key": q["field"],
        "options": q.get("options", []),
        "input_type": q.get("input_type", "multiline"),
        "placeholder": q.get("placeholder", "Type your answer…"),
    }


@app.post("/onboarding/answer", response_model=OnboardingStepResponse, tags=["Onboarding"])
def onboarding_answer(
    payload: OnboardingStepRequest, db: Session = Depends(get_db)
) -> OnboardingStepResponse:
    profile = get_or_create_profile(db, payload.user_id)
    if profile.onboarding_complete:
        raise HTTPException(status_code=400, detail="Onboarding already complete.")
    # Always use the server-side step — ignore any step sent by the client
    current_step = profile.onboarding_step
    next_q, complete, summary = process_onboarding_step(
        db, payload.user_id, current_step, payload.answer
    )
    return OnboardingStepResponse(
        next_question=next_q,
        step=current_step + 1,
        total_steps=TOTAL_STEPS,
        complete=complete,
        profile_summary=summary,
    )


# ── User Profile ──────────────────────────────────────────────────────────────

@app.get("/profile", response_model=UserProfileOut, tags=["Profile"])
def get_profile(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> UserProfileOut:
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Complete onboarding first.")
    return UserProfileOut(
        user_id=profile.user_id,
        full_name=profile.full_name,
        role=profile.role,
        organization=profile.organization,
        biggest_challenge=profile.biggest_challenge,
        core_values=profile.core_values or [],
        goals_90_days=profile.goals_90_days or [],
        coaching_style_preference=profile.coaching_style_preference,
        onboarding_complete=profile.onboarding_complete,
        profile_version=profile.profile_version,
        last_profile_update=profile.last_profile_update,
        energy_baseline=profile.energy_baseline,
        burnout_risk=profile.burnout_risk,
        profile_summary=profile.profile_summary or "",
    )


# ── Daily Check-In (legacy numeric form — kept for backward compatibility) ─────

@app.post("/checkin", response_model=DailyCheckInResponse, tags=["Check-In"])
def daily_checkin(
    payload: DailyCheckInRequest, db: Session = Depends(get_db)
) -> DailyCheckInResponse:
    """Legacy numeric check-in (energy/stress/sleep as numbers). Use /checkin/converse for the conversational version."""
    return process_checkin(db, payload)


# ── Conversational Check-In (the real way) ────────────────────────────────────

@app.get("/checkin/start", response_model=ConversationalCheckInStartResponse, tags=["Check-In"])
def checkin_start(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> ConversationalCheckInStartResponse:
    """
    Opens the daily check-in conversation.
    Returns a warm, personalised opening question.
    The user responds with natural language — no numbers needed.
    """
    return start_checkin(db, user_id)


@app.post("/checkin/converse", response_model=ConversationalCheckInResponse, tags=["Check-In"])
def checkin_converse(
    payload: ConversationalCheckInRequest, db: Session = Depends(get_db)
) -> ConversationalCheckInResponse:
    """
    Processes the user's natural language response to the check-in.

    The coach extracts energy, stress, sleep, and emotional tone from the text.
    If signals are ambiguous, returns status='needs_followup' with a follow-up question.
    If a relationship conflict is detected, routes to relationship coaching mode.

    tone_hint (optional): iOS-side tone analysis result
    ('tired' | 'energized' | 'angry' | 'distressed' | 'neutral')
    """
    return process_conversational_checkin(
        db,
        user_id=payload.user_id,
        user_response=payload.user_response,
        tone_hint=payload.tone_hint,
        is_followup_response=payload.is_followup_response,
        followup_response_text=payload.followup_response_text,
    )


# ── Habits ────────────────────────────────────────────────────────────────────

@app.post("/habits", response_model=HabitsResponse, tags=["Habits"])
def add_habit(
    payload: HabitCreateRequest, db: Session = Depends(get_db)
) -> HabitsResponse:
    create_habit(db, payload)
    return get_habits(db, payload.user_id)


@app.post("/habits/complete", response_model=HabitsResponse, tags=["Habits"])
def mark_habit_complete(
    payload: HabitCompleteRequest, db: Session = Depends(get_db)
) -> HabitsResponse:
    try:
        complete_habit(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return get_habits(db, payload.user_id)


@app.get("/habits", response_model=HabitsResponse, tags=["Habits"])
def list_habits(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> HabitsResponse:
    return get_habits(db, user_id)


# ── Weekly Reflection ─────────────────────────────────────────────────────────

@app.post("/reflection/weekly", response_model=WeeklyReflectionResponse, tags=["Reflection"])
def weekly_reflection(
    payload: WeeklyReflectionRequest, db: Session = Depends(get_db)
) -> WeeklyReflectionResponse:
    """Sunday ritual: 3 answers → coach synthesises the week and issues one binding commitment."""
    return save_weekly_reflection(db, payload)


# ── Coaching ──────────────────────────────────────────────────────────────────

@app.post("/coach/respond", response_model=CoachResponse, tags=["Coaching"])
async def coach_respond(
    payload: CoachRequest, db: Session = Depends(get_db)
) -> CoachResponse:
    """Single-turn personalised coaching response. Memory-aware: coach knows the full user history."""
    profile = db.query(UserProfile).filter_by(user_id=payload.user_id).first()
    # Use rich memory context if available, fall back to thin persona context
    from app.services.memory_context import build_coach_memory_context
    if profile and profile.onboarding_complete:
        user_context = build_coach_memory_context(db, payload.user_id)
    else:
        user_context = build_persona_context(profile) if profile else ""

    user_tags = (profile.core_values or [])[:3] if profile else []
    knowledge_items = retrieve_for_context(db, track=payload.track, user_tags=user_tags, limit=3)
    knowledge_context = "\n".join(
        f"- {item.title} ({item.published_date}): {item.takeaway}" for item in knowledge_items
    )
    full_context = f"{user_context}\nRELEVANT RESEARCH:\n{knowledge_context}" if knowledge_context else user_context

    return await generate_coach_response(payload, user_context=full_context)


@app.post("/coach/conversations/message", response_model=CoachConversationMessageResponse, tags=["Coaching"])
async def coach_conversation_message(
    payload: CoachConversationMessageRequest, db: Session = Depends(get_db)
) -> CoachConversationMessageResponse:
    """Multi-turn coaching with encrypted persistent history, living knowledge, and full memory context."""
    profile = db.query(UserProfile).filter_by(user_id=payload.user_id).first()
    # Use rich memory context if available, fall back to thin persona context
    from app.services.memory_context import build_coach_memory_context
    if profile and profile.onboarding_complete:
        user_context = build_coach_memory_context(db, payload.user_id)
    else:
        user_context = build_persona_context(profile) if profile else ""

    user_tags = (profile.core_values or [])[:3] if profile else []
    knowledge_items = retrieve_for_context(db, track=payload.track, user_tags=user_tags, limit=3)
    knowledge_context = "\n".join(
        f"- {item.title} ({item.published_date}): {item.takeaway}" for item in knowledge_items
    )
    full_context = f"{user_context}\nRELEVANT RESEARCH:\n{knowledge_context}" if knowledge_context else user_context

    merged_context = f"user_message={payload.message}, {payload.context}".strip(", ")
    coach = await generate_coach_response(
        CoachRequest(
            context=merged_context,
            goal=payload.goal,
            track=payload.track,
            user_id=payload.user_id,
        ),
        user_context=full_context,
    )
    model_name = os.getenv("OPENAI_COACH_MODEL", "fallback-local")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        model_name = "fallback-local"

    row = conversation_store.save_turn(
        db,
        user_id=payload.user_id,
        session_id=payload.session_id,
        intent=payload.track,
        user_message=payload.message,
        coach_message=coach.message,
        context=merged_context,
        coach_model=model_name,
    )
    conversation_store.purge_expired(db)
    db.commit()

    return CoachConversationMessageResponse(
        message=coach.message,
        suggested_actions=coach.suggested_actions,
        conversation_id=row.id,
    )


@app.get("/coach/conversations/history", response_model=list[CoachConversationHistoryItem], tags=["Coaching"])
def coach_conversation_history(
    user_id: str = Query(default="default"),
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[CoachConversationHistoryItem]:
    return conversation_store.list_history(db, user_id=user_id, session_id=session_id, limit=limit)


@app.post("/coach/conversations/retention/run", response_model=RetentionPurgeResponse, tags=["Coaching"])
def coach_retention_run(db: Session = Depends(get_db)) -> RetentionPurgeResponse:
    deleted = conversation_store.purge_expired(db)
    db.commit()
    return RetentionPurgeResponse(deleted_count=deleted)


# ── Voice Coaching ────────────────────────────────────────────────────────────

@app.post("/coach/voice", response_model=VoiceCoachResponse, tags=["Voice"])
async def coach_voice(
    payload: VoiceTranscriptRequest, db: Session = Depends(get_db)
) -> VoiceCoachResponse:
    """
    Voice coaching endpoint.

    The iOS app transcribes speech via Whisper (on-device or via API),
    optionally analyses tone via AVAudioEngine, then sends the transcript here.

    The response includes:
    - full_response: the complete coaching message (may include structured formatting)
    - tts_text: a clean, spoken-language version for ElevenLabs / AVSpeechSynthesizer

    Tone hint modifies coaching register:
    - 'tired'     → softer, grounding, energy-focused
    - 'angry'     → calm, de-escalating, empathetic first
    - 'distressed'→ presence first, then practical
    - 'energized' → ambitious, expansive, challenging
    """
    profile = db.query(UserProfile).filter_by(user_id=payload.user_id).first()
    user_context = build_persona_context(profile) if profile else ""

    # Enrich with relevant knowledge
    user_tags = (profile.core_values or [])[:3] if profile else []
    knowledge_items = retrieve_for_context(db, track=payload.track, user_tags=user_tags, limit=2)
    knowledge_context = "\n".join(
        f"- {item.title}: {item.takeaway}" for item in knowledge_items
    )
    full_context = f"{user_context}\nRELEVANT RESEARCH:\n{knowledge_context}" if knowledge_context else user_context

    # Add tone register instruction to context
    tone_instruction = ""
    if payload.tone_hint == "tired":
        tone_instruction = "\n[TONE INSTRUCTION: User sounds tired and low-energy. Lead with grounding and energy recovery before any strategy.]"
    elif payload.tone_hint == "angry":
        tone_instruction = "\n[TONE INSTRUCTION: User sounds agitated or angry. Acknowledge the emotion first. Do not jump to solutions.]"
    elif payload.tone_hint == "distressed":
        tone_instruction = "\n[TONE INSTRUCTION: User sounds emotionally distressed. Be present and warm first. Ask one clarifying question before coaching.]"
    elif payload.tone_hint == "energized":
        tone_instruction = "\n[TONE INSTRUCTION: User sounds energized and positive. Match their energy. Be ambitious and expansive in your coaching.]"

    enriched_context = full_context + tone_instruction

    coach_resp = await generate_coach_response(
        CoachRequest(
            context=payload.transcript + " " + payload.context,
            goal="Respond as a wise, warm executive coach who just heard this from the user. Speak as if in conversation.",
            track=payload.track,
            user_id=payload.user_id,
        ),
        user_context=enriched_context,
    )

    # Build clean TTS text (remove markdown-style formatting)
    import re
    tts_text = re.sub(r"\*\*(.+?)\*\*", r"\1", coach_resp.message)
    tts_text = re.sub(r"#+\s", "", tts_text)
    tts_text = re.sub(r"  \d+\.", " ", tts_text)
    tts_text = tts_text.replace("\n\n", " ").replace("\n", " ").strip()

    # Save to conversation history
    model_name = os.getenv("OPENAI_COACH_MODEL", "fallback-local")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        model_name = "fallback-local"

    row = conversation_store.save_turn(
        db,
        user_id=payload.user_id,
        session_id=payload.session_id,
        intent=payload.track,
        user_message=f"[VOICE] {payload.transcript}",
        coach_message=coach_resp.message,
        context=payload.context,
        coach_model=model_name,
    )
    db.commit()

    return VoiceCoachResponse(
        full_response=coach_resp.message,
        tts_text=tts_text,
        suggested_actions=coach_resp.suggested_actions,
        dominant_track=payload.track,
        relationship_flag=any(
            w in payload.transcript.lower()
            for w in ["wife", "husband", "partner", "fight", "argument", "family"]
        ),
        conversation_id=row.id,
    )


# ── Proactive Coaching ────────────────────────────────────────────────────────

@app.get("/coach/proactive/morning-brief", response_model=MorningBriefResponse, tags=["Proactive"])
def morning_brief(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> MorningBriefResponse:
    """
    The Morning Intelligence Brief — personalised to that exact day.
    Reads yesterday's energy, 7-day trend, last weekly commitment, habit momentum,
    and one insight from the knowledge base.
    Delivered every morning before the day begins.
    """
    result = generate_morning_brief(db, user_id)
    return MorningBriefResponse(**result)


@app.get("/coach/proactive/evening-questions", response_model=EveningReviewQuestionsResponse, tags=["Proactive"])
def evening_review_questions(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> EveningReviewQuestionsResponse:
    """
    The three questions a great coach asks at end of every day.
    Delivered at 8pm. Non-negotiable.
    """
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    result = generate_evening_review_questions(profile)
    return EveningReviewQuestionsResponse(**result)


@app.post("/coach/proactive/evening-review", response_model=EveningReviewResponse, tags=["Proactive"])
def evening_review(
    payload: EveningReviewRequest, db: Session = Depends(get_db)
) -> EveningReviewResponse:
    """
    User answers the three evening questions.
    Coach returns one observation and a tomorrow intention.
    """
    result = process_evening_review(
        db,
        user_id=payload.user_id,
        biggest_win=payload.biggest_win,
        biggest_regret=payload.biggest_regret,
        who_showed_up_for=payload.who_showed_up_for,
    )
    return EveningReviewResponse(**result)


@app.get("/coach/proactive/coach-notebook", response_model=CoachNotebookEntryResponse, tags=["Proactive"])
def coach_notebook(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> CoachNotebookEntryResponse:
    """
    The Coach's Notebook — pattern recognition engine.
    Reads 14 days of check-ins, habits, and reflections.
    Returns 3-5 observations the coach has noticed about this user.
    Updated weekly. This is the feature that makes users say 'it knows me.'
    """
    result = generate_coach_notebook_entry(db, user_id)
    return CoachNotebookEntryResponse(**result)


@app.get("/coach/proactive/relationship-nudges", response_model=list[RelationshipNudge], tags=["Proactive"])
def relationship_nudges(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> list[RelationshipNudge]:
    """
    Proactive relationship maintenance.
    If a key relationship (named in onboarding) has not been mentioned in 10 days,
    the coach sends a nudge: 'You haven't mentioned your partner in 12 days. How are things?'
    """
    nudges = check_relationship_nudges(db, user_id)
    return [RelationshipNudge(**n) for n in nudges]


@app.get("/coach/proactive/reading-assignment", response_model=WeeklyReadingAssignmentResponse, tags=["Proactive"])
def reading_assignment(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> WeeklyReadingAssignmentResponse:
    """
    Weekly reading assignment from the coach.
    Matched to the user's dominant coaching track.
    Includes assignment, key takeaway, personal application, and an accountability question.
    Delivered every Monday.
    """
    result = get_weekly_reading_assignment(db, user_id)
    return WeeklyReadingAssignmentResponse(**result)


# ── Knowledge Base ────────────────────────────────────────────────────────────

@app.get("/coach/knowledge/studying", response_model=list[KnowledgeItemOut], tags=["Knowledge"])
def coach_knowledge_studying(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[KnowledgeItemOut]:
    """What the coach has been reading recently. Show this to users in the app."""
    items = get_recently_ingested(db, days=days, limit=limit)
    return [_ki_out(i) for i in items]


@app.get("/coach/knowledge/relevant", response_model=list[KnowledgeItemOut], tags=["Knowledge"])
def coach_knowledge_relevant(
    track: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[KnowledgeItemOut]:
    """Most relevant items for a given coaching track."""
    items = retrieve_for_context(db, track=track, limit=limit)
    return [_ki_out(i) for i in items]


@app.get("/coach/knowledge/stats", response_model=KnowledgeStatsResponse, tags=["Knowledge"])
def coach_knowledge_stats(db: Session = Depends(get_db)) -> KnowledgeStatsResponse:
    stats = knowledge_stats(db)
    return KnowledgeStatsResponse(**stats)


@app.post("/coach/knowledge/ingest/pubmed", response_model=KnowledgeIngestResponse, tags=["Knowledge"])
async def ingest_from_pubmed(
    max_per_query: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
) -> KnowledgeIngestResponse:
    """Trigger PubMed ingestion manually. Run weekly via scheduler."""
    result = await ingest_pubmed(db, max_per_query=max_per_query)
    return KnowledgeIngestResponse(**result)


@app.post("/coach/knowledge/ingest/manual", response_model=KnowledgeItemOut, tags=["Knowledge"])
def ingest_manual_item(
    payload: KnowledgeIngestManualRequest, db: Session = Depends(get_db)
) -> KnowledgeItemOut:
    """Curator adds a paper, book, or framework manually."""
    item = ingest_manual(
        db,
        title=payload.title,
        takeaway=payload.takeaway,
        application=payload.application,
        source_url=payload.source_url,
        authors=payload.authors,
        published_date=payload.published_date,
        abstract=payload.abstract,
        category=payload.category,
        tags=payload.tags or None,
        relevance_score=payload.relevance_score,
        source=payload.source,
    )
    return _ki_out(item)


# ── Premium & Intelligence ────────────────────────────────────────────────────

@app.get("/coach/intelligence/brief", response_model=list[ResearchInsightOut], tags=["Intelligence"])
def coach_intelligence_brief(
    track: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[ResearchInsightOut]:
    """Legacy-compatible research brief endpoint."""
    items = retrieve_for_context(db, track=track, limit=limit)
    return [
        ResearchInsightOut(
            id=item.external_id,
            title=item.title,
            published_date=item.published_date,
            category=item.category,
            takeaway=item.takeaway,
            application=item.application,
            source_url=item.source_url,
        )
        for item in items
    ]


@app.get("/coach/premium/tiers", response_model=list[PremiumTierOut], tags=["Intelligence"])
def coach_premium_tiers() -> list[PremiumTierOut]:
    return premium_tiers()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ki_out(item) -> KnowledgeItemOut:
    return KnowledgeItemOut(
        id=item.id,
        external_id=item.external_id,
        source=item.source,
        title=item.title,
        authors=item.authors,
        published_date=item.published_date,
        category=item.category,
        takeaway=item.takeaway,
        application=item.application,
        source_url=item.source_url,
        tags=item.tags or [],
        relevance_score=item.relevance_score,
        ingested_at=item.ingested_at,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# V2 ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

from app.schemas import (
    AchievementOut, ConflictPrepListItem, ConflictPrepRequest, ConflictPrepResponse,
    CrisisCheckRequest, CrisisCheckResponse, DecisionPatternResponse,
    DecisionPremortemQuestionsResponse, DecisionReviewRequest, DecisionReviewResponse,
    FinalDecisionRequest, HealthDataRequest, HealthDataResponse, HealthSummaryResponse,
    LogDecisionRequest, LogDecisionResponse, MilestoneUpdateRequest, MilestoneUpdateResponse,
    MonthlyReportResponse, SprintDashboardResponse, SprintRetrospectiveResponse,
)
from app.services.sprint_dashboard import (
    generate_sprint_retrospective, get_sprint_dashboard,
    initialize_sprint_for_user, update_milestone,
)
from app.services.decision_coach import (
    get_decision_pattern_analysis, list_pending_reviews,
    log_decision, record_final_decision, run_decision_review, start_decision_premortem,
)
from app.services.conflict_prep import (
    generate_conflict_prep, get_conflict_prep, list_conflict_preps,
)
from app.services.crisis_mode import detect_crisis_signal, generate_crisis_response
from app.services.monthly_report import generate_monthly_report
from app.services.healthkit import (
    get_health_context_for_coaching, get_recent_health_summary, upsert_health_data,
)
from app.services.achievements import (
    check_consistency_achievements, get_all_achievements, get_uncelebrated_achievements,
)
from app.services.bilingual import detect_language, get_language_instruction, update_language_preference


# ── 90-Day Sprint Dashboard ───────────────────────────────────────────────────

@app.post("/sprint/initialize", tags=["Sprint"])
def sprint_initialize(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> dict:
    """
    Call once after onboarding to generate 12 weeks of milestones for each goal.
    Normally triggered automatically when onboarding completes.
    """
    count = initialize_sprint_for_user(db, user_id)
    return {"milestones_created": count, "message": f"90-Day Sprint initialized with {count} milestones."}


@app.get("/sprint/dashboard", response_model=SprintDashboardResponse, tags=["Sprint"])
def sprint_dashboard(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> SprintDashboardResponse:
    """
    Full 90-Day Sprint dashboard: current week milestones, progress per goal,
    12-week progress bars, and sprint health score.
    """
    result = get_sprint_dashboard(db, user_id)
    return SprintDashboardResponse(**result)


@app.post("/sprint/milestone", response_model=MilestoneUpdateResponse, tags=["Sprint"])
def sprint_milestone_update(
    payload: MilestoneUpdateRequest, db: Session = Depends(get_db)
) -> MilestoneUpdateResponse:
    """
    User reports on a specific week's milestone.
    Coach assesses on_track / at_risk / complete and responds.
    """
    result = update_milestone(
        db,
        user_id=payload.user_id,
        goal_index=payload.goal_index,
        week_number=payload.week_number,
        user_update=payload.user_update,
        progress_pct=payload.progress_pct,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return MilestoneUpdateResponse(**result)


@app.get("/sprint/retrospective", response_model=SprintRetrospectiveResponse, tags=["Sprint"])
def sprint_retrospective(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> SprintRetrospectiveResponse:
    """Full 90-day Sprint Retrospective — achievement rates, pattern observations, next sprint brief."""
    result = generate_sprint_retrospective(db, user_id)
    return SprintRetrospectiveResponse(**result)


# ── Decision Coach ────────────────────────────────────────────────────────────

@app.get("/coach/decision/premortem-questions", response_model=DecisionPremortemQuestionsResponse, tags=["Decisions"])
def decision_premortem_questions(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> DecisionPremortemQuestionsResponse:
    """The 5 questions every leader should answer before making a major decision."""
    result = start_decision_premortem(db, user_id)
    return DecisionPremortemQuestionsResponse(**result)


@app.post("/coach/decision/log", response_model=LogDecisionResponse, tags=["Decisions"])
def decision_log(
    payload: LogDecisionRequest, db: Session = Depends(get_db)
) -> LogDecisionResponse:
    """
    Log a major decision with pre-mortem data.
    Coach returns a recommendation and schedules a 30-day review.
    """
    result = log_decision(
        db,
        user_id=payload.user_id,
        decision_title=payload.decision_title,
        decision_description=payload.decision_description,
        options_considered=payload.options_considered,
        premortem_failure_modes=payload.premortem_failure_modes,
        gut_says=payload.gut_says,
    )
    return LogDecisionResponse(**result)


@app.post("/coach/decision/final", tags=["Decisions"])
def decision_final(payload: FinalDecisionRequest, db: Session = Depends(get_db)) -> dict:
    """Record what was actually decided (separate from the pre-mortem log)."""
    return record_final_decision(db, payload.decision_id, payload.user_id, payload.final_decision)


@app.post("/coach/decision/review", response_model=DecisionReviewResponse, tags=["Decisions"])
def decision_review(
    payload: DecisionReviewRequest, db: Session = Depends(get_db)
) -> DecisionReviewResponse:
    """30-day review: what happened vs. what was feared. Coach writes a pattern observation."""
    result = run_decision_review(db, payload.decision_id, payload.user_id, payload.actual_outcome)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return DecisionReviewResponse(**result)


@app.get("/coach/decision/pending-reviews", tags=["Decisions"])
def decision_pending_reviews(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> list[dict]:
    """Decisions past their 30-day review date that haven't been reviewed yet."""
    return list_pending_reviews(db, user_id)


@app.get("/coach/decision/pattern-analysis", response_model=DecisionPatternResponse, tags=["Decisions"])
def decision_pattern_analysis(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> DecisionPatternResponse:
    """After 3+ decisions logged: the coach identifies your decision-making patterns."""
    result = get_decision_pattern_analysis(db, user_id)
    return DecisionPatternResponse(**result)


# ── Conflict Preparation ──────────────────────────────────────────────────────

@app.post("/coach/conflict-prep", response_model=ConflictPrepResponse, tags=["Conflict Prep"])
def conflict_prep_generate(
    payload: ConflictPrepRequest, db: Session = Depends(get_db)
) -> ConflictPrepResponse:
    """
    Generate a full conversation preparation script for a difficult interaction.
    Types: feedback / negotiation / repair / performance / boundary / apology
    """
    result = generate_conflict_prep(
        db,
        user_id=payload.user_id,
        conversation_type=payload.conversation_type,
        other_person=payload.other_person,
        relationship_to_user=payload.relationship_to_user,
        situation_description=payload.situation_description,
        desired_outcome=payload.desired_outcome,
        user_fear=payload.user_fear,
    )
    return ConflictPrepResponse(**result)


@app.get("/coach/conflict-prep/{prep_id}", tags=["Conflict Prep"])
def conflict_prep_get(
    prep_id: int,
    user_id: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieve a saved conversation prep script."""
    result = get_conflict_prep(db, prep_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Prep script not found.")
    return result


@app.get("/coach/conflict-preps", response_model=list[ConflictPrepListItem], tags=["Conflict Prep"])
def conflict_preps_list(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> list[ConflictPrepListItem]:
    """List all past conflict prep scripts for this user."""
    return [ConflictPrepListItem(**p) for p in list_conflict_preps(db, user_id)]


# ── Crisis Mode ───────────────────────────────────────────────────────────────

@app.post("/coach/crisis", response_model=CrisisCheckResponse, tags=["Crisis"])
def crisis_check(
    payload: CrisisCheckRequest, db: Session = Depends(get_db)
) -> CrisisCheckResponse:
    """
    Emergency coaching endpoint. Activated when:
    - User says 'I'm done', 'I want to quit', 'I'm falling apart'
    - Energy drops to 2 or below
    - User explicitly calls this endpoint

    For acute risk signals, provides mental health professional referrals.
    This endpoint is NOT a clinical intervention — it is a coaching tool that
    always directs to professional support when signals are acute.
    """
    signal = detect_crisis_signal(payload.message, energy=payload.energy)
    if signal["severity"] == "none":
        return CrisisCheckResponse(severity="none")
    result = generate_crisis_response(
        db, payload.user_id, payload.message, signal["severity"], payload.energy
    )
    return CrisisCheckResponse(**result)


# ── Monthly Report ────────────────────────────────────────────────────────────

@app.get("/coach/report/monthly", response_model=MonthlyReportResponse, tags=["Reports"])
def monthly_report(
    user_id: str = Query(default="default"),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MonthlyReportResponse:
    """
    Full monthly coaching report: energy trends, habit rates, sprint progress,
    decisions, reflections, coach observations, and next month's focus.
    The premium deliverable users look forward to every month.
    """
    result = generate_monthly_report(db, user_id, year=year, month=month)
    return MonthlyReportResponse(**result)


# ── HealthKit ─────────────────────────────────────────────────────────────────

@app.post("/health/data", response_model=HealthDataResponse, tags=["Health"])
def health_data_ingest(
    payload: HealthDataRequest, db: Session = Depends(get_db)
) -> HealthDataResponse:
    """
    Accepts HealthKit data from iOS (sent as a background task, no user friction).
    Stores sleep, HRV, resting HR, steps, calories, mindful minutes.
    Returns a coaching note based on the objective data.
    When available, this data enriches every morning brief and coaching response.
    """
    from datetime import date as _date
    data_date = payload.data_date or _date.today().strftime("%Y-%m-%d")
    result = upsert_health_data(
        db,
        user_id=payload.user_id,
        data_date=data_date,
        sleep_hours=payload.sleep_hours,
        sleep_quality_score=payload.sleep_quality_score,
        hrv_ms=payload.hrv_ms,
        resting_hr=payload.resting_hr,
        steps=payload.steps,
        active_calories=payload.active_calories,
        mindful_minutes=payload.mindful_minutes,
    )
    return HealthDataResponse(**result)


@app.get("/health/summary", response_model=HealthSummaryResponse, tags=["Health"])
def health_summary(
    user_id: str = Query(default="default"),
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
) -> HealthSummaryResponse:
    """7-30 day HealthKit summary: sleep averages, HRV trend, steps, mindful minutes."""
    result = get_recent_health_summary(db, user_id, days=days)
    return HealthSummaryResponse(**result)


# ── Achievements ──────────────────────────────────────────────────────────────

@app.get("/achievements", response_model=list[AchievementOut], tags=["Achievements"])
def achievements_all(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> list[AchievementOut]:
    """Full achievement history — for the profile screen."""
    return [AchievementOut(**a) for a in get_all_achievements(db, user_id)]


@app.get("/achievements/uncelebrated", response_model=list[AchievementOut], tags=["Achievements"])
def achievements_uncelebrated(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> list[AchievementOut]:
    """
    Fetch achievements that haven't been shown to the user yet.
    Called by morning brief to surface celebrations.
    Marks them as celebrated after fetching.
    """
    return [AchievementOut(**a) for a in get_uncelebrated_achievements(db, user_id)]


# ── Calendar Integration (V4) ──────────────────────────────────────────────────
from app.services.calendar_coach import (
    analyze_meeting_density,
    generate_pre_meeting_brief,
    get_calendar_context_for_coaching,
    get_post_meeting_prompt,
    get_todays_calendar_brief,
    save_post_meeting_note,
    sync_calendar_events,
    toggle_calendar_integration,
)
from app.schemas import (
    CalendarSyncRequest,
    CalendarSyncResponse,
    TodayCalendarResponse,
    PreMeetingBriefResponse,
    PostMeetingPromptResponse,
    PostMeetingNoteRequest,
    PostMeetingNoteResponse,
    MeetingDensityResponse,
    CalendarSettingsRequest,
    CalendarSettingsResponse,
)


@app.post("/calendar/sync", response_model=CalendarSyncResponse, tags=["Calendar"])
def calendar_sync(payload: CalendarSyncRequest, db: Session = Depends(get_db)) -> CalendarSyncResponse:
    """
    iOS pushes the next 7 days of calendar events here (daily background task).
    Architecture: iOS handles all OAuth. This endpoint only receives structured event data.
    Upserts by external_event_id — safe to call as frequently as needed.

    The coach uses this data for:
    - Pre-meeting briefs (30 min before high-stakes events)
    - Post-meeting reflection prompts
    - Morning brief calendar context
    - Weekly meeting density analysis
    """
    events_dicts = [e.dict() for e in payload.events]
    result = sync_calendar_events(
        db,
        user_id=payload.user_id,
        events=events_dicts,
        provider=payload.provider,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return CalendarSyncResponse(**result)


@app.get("/calendar/today", response_model=TodayCalendarResponse, tags=["Calendar"])
def calendar_today(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> TodayCalendarResponse:
    """
    Today's coaching-relevant meetings with coach context.
    Included in morning brief when calendar integration is enabled.
    Flags back-to-back meetings, high-stakes events, and meeting overload.
    """
    result = get_todays_calendar_brief(db, user_id)
    return TodayCalendarResponse(**result)


@app.get(
    "/calendar/pre-meeting/{event_id}",
    response_model=PreMeetingBriefResponse,
    tags=["Calendar"],
)
def calendar_pre_meeting_brief(
    event_id: int,
    user_id: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> PreMeetingBriefResponse:
    """
    Generate a personalised pre-meeting coaching brief for an upcoming event.
    Call this 30 minutes before the meeting starts (iOS background task triggers it).

    The brief includes:
    - User's current energy and HRV context
    - Known attendee notes (from key_relationships in their profile)
    - Meeting-type-specific mindset anchor
    - One tactical recommendation
    - One thing NOT to do
    """
    result = generate_pre_meeting_brief(db, user_id, event_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return PreMeetingBriefResponse(**result)


@app.get(
    "/calendar/post-meeting/{event_id}",
    response_model=PostMeetingPromptResponse,
    tags=["Calendar"],
)
def calendar_post_meeting_prompt(
    event_id: int,
    user_id: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> PostMeetingPromptResponse:
    """
    Get the post-meeting reflection prompt for a completed event.
    Call this 30 minutes after the meeting ends (iOS background task).
    The prompt is calibrated to the meeting type (high-stakes / 1on1 / large group).
    """
    result = get_post_meeting_prompt(db, user_id, event_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return PostMeetingPromptResponse(**result)


@app.post(
    "/calendar/post-meeting/{event_id}",
    response_model=PostMeetingNoteResponse,
    tags=["Calendar"],
)
def calendar_save_post_meeting_note(
    event_id: int,
    payload: PostMeetingNoteRequest,
    db: Session = Depends(get_db),
) -> PostMeetingNoteResponse:
    """
    Save the user's post-meeting reflection note. Returns coach synthesis.
    The coach reads the note and generates a pattern observation:
    regret signals, unresolved tensions, wins worth registering.
    Over time, these accumulate into a meeting performance journal.
    """
    result = save_post_meeting_note(db, payload.user_id, event_id, payload.note)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return PostMeetingNoteResponse(**result)


@app.get("/calendar/density", response_model=MeetingDensityResponse, tags=["Calendar"])
def calendar_meeting_density(
    user_id: str = Query(default="default"),
    days: int = Query(default=14, ge=7, le=30),
    db: Session = Depends(get_db),
) -> MeetingDensityResponse:
    """
    Analyse meeting density over the past N days (default: 14).
    Correlates meeting load with energy check-in scores.
    Detects back-to-back meetings, heavy days (5+ meetings), and energy impact.

    Inspired by Paul Graham's Manager's Schedule / Maker's Schedule framework.
    The coach uses this data to recommend calendar restructuring.
    """
    result = analyze_meeting_density(db, user_id, days=days)
    return MeetingDensityResponse(**result)


@app.post("/calendar/settings", response_model=CalendarSettingsResponse, tags=["Calendar"])
def calendar_settings(
    payload: CalendarSettingsRequest, db: Session = Depends(get_db)
) -> CalendarSettingsResponse:
    """
    Toggle calendar integration on or off. Set the provider (apple / google).
    Called from iOS Settings screen when user flips the calendar sync toggle.
    When disabled, no new events will be processed (historical events are retained).
    """
    result = toggle_calendar_integration(
        db,
        user_id=payload.user_id,
        enabled=payload.enabled,
        provider=payload.provider,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return CalendarSettingsResponse(**result)


# ── V5: Commitment Tracker ────────────────────────────────────────────────────
from app.services.commitment_tracker import (
    check_commitment,
    create_commitment,
    get_commitment_history,
    get_open_commitments,
)
from app.schemas import (
    CommitmentCreateRequest,
    CommitmentCreateResponse,
    CommitmentCheckInRequest,
    CommitmentCheckInResponse,
    OpenCommitmentsResponse,
    CommitmentHistoryResponse,
)


@app.post("/commitments", response_model=CommitmentCreateResponse, tags=["Commitments"])
def commitment_create(
    payload: CommitmentCreateRequest, db: Session = Depends(get_db)
) -> CommitmentCreateResponse:
    """
    Create a tracked commitment. Every commitment made in the app
    (evening review, conflict prep, decision log, or direct) ends up here.
    The coach follows up on every single one.
    """
    result = create_commitment(
        db,
        user_id=payload.user_id,
        commitment_text=payload.commitment_text,
        due_date=payload.due_date,
        source=payload.source,
        source_id=payload.source_id,
    )
    return CommitmentCreateResponse(**result)


@app.post("/commitments/{commitment_id}/check-in", response_model=CommitmentCheckInResponse, tags=["Commitments"])
def commitment_check_in(
    commitment_id: int,
    payload: CommitmentCheckInRequest,
    db: Session = Depends(get_db),
) -> CommitmentCheckInResponse:
    """
    Report back on a commitment: kept / missed / partial / deferred.
    The coach responds with a non-judgmental observation.
    Kept commitments feed into the achievement engine.
    Missed commitments trigger a pattern inquiry.
    """
    result = check_commitment(
        db,
        user_id=payload.user_id,
        commitment_id=commitment_id,
        status=payload.status,
        user_note=payload.user_note,
        deferred_to=payload.deferred_to,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return CommitmentCheckInResponse(**result)


@app.get("/commitments/open", response_model=OpenCommitmentsResponse, tags=["Commitments"])
def commitments_open(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> OpenCommitmentsResponse:
    """
    All open commitments: overdue, due today, and upcoming (7 days).
    Included in the morning brief to surface accountability.
    Overdue commitments are prioritised — the coach does not let them disappear.
    """
    result = get_open_commitments(db, user_id)
    return OpenCommitmentsResponse(**result)


@app.get("/commitments/history", response_model=CommitmentHistoryResponse, tags=["Commitments"])
def commitments_history(
    user_id: str = Query(default="default"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CommitmentHistoryResponse:
    """
    Full commitment history with completion rate and pattern analysis.
    After 5+ closed commitments, the coach identifies patterns in what
    the user consistently keeps vs. consistently misses.
    """
    result = get_commitment_history(db, user_id, limit=limit)
    return CommitmentHistoryResponse(**result)


# ── V5: Energy Pattern Intelligence ──────────────────────────────────────────
from app.services.energy_patterns import (
    analyse_energy_patterns,
    get_peak_performance_window,
)
from app.schemas import (
    EnergyPatternResponse,
    PeakPerformanceWindowResponse,
)


@app.get("/insights/energy-patterns", response_model=EnergyPatternResponse, tags=["Insights"])
def energy_patterns(
    user_id: str = Query(default="default"),
    days: int = Query(default=60, ge=14, le=180),
    db: Session = Depends(get_db),
) -> EnergyPatternResponse:
    """
    Deep energy pattern analysis across 60-180 days of check-in data.
    Returns: peak/trough day of week, energy stability score, recovery speed,
    habit-energy correlations (which habits actually move your energy),
    sleep-energy correlation (from HealthKit), and trend direction.
    Requires minimum 14 check-ins. Full analysis unlocks at 30+.
    """
    result = analyse_energy_patterns(db, user_id, days=days)
    if not result.get("available"):
        return EnergyPatternResponse(
            available=False,
            check_in_count=result.get("check_in_count", 0),
            message=result.get("message", ""),
            minimum_required=14,
        )
    return EnergyPatternResponse(**result)


@app.get("/insights/peak-performance-window", response_model=PeakPerformanceWindowResponse, tags=["Insights"])
def peak_performance_window(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> PeakPerformanceWindowResponse:
    """
    Quick summary of peak performance window — best day, best habit, trend.
    One-line version included in morning brief when data is available.
    """
    result = get_peak_performance_window(db, user_id)
    return PeakPerformanceWindowResponse(**result)


# ── V5: 30/60/90-Day Re-calibration ──────────────────────────────────────────
from app.services.recalibration import (
    check_recalibration_due,
    process_recalibration_answer,
)
from app.schemas import (
    RecalibrationDueResponse,
    RecalibrationAnswerRequest,
    RecalibrationAnswerResponse,
)


@app.get("/recalibration/status", response_model=RecalibrationDueResponse, tags=["Recalibration"])
def recalibration_status(
    user_id: str = Query(default="default"), db: Session = Depends(get_db)
) -> RecalibrationDueResponse:
    """
    Check whether a recalibration milestone (30 / 60 / 90 days) is due.
    Called on app open — if a milestone is due, the iOS app surfaces
    the re-interview flow before the morning brief.
    Returns the questions if a milestone is due.
    """
    result = check_recalibration_due(db, user_id)
    return RecalibrationDueResponse(**result)


@app.post("/recalibration/answer", response_model=RecalibrationAnswerResponse, tags=["Recalibration"])
def recalibration_answer(
    payload: RecalibrationAnswerRequest, db: Session = Depends(get_db)
) -> RecalibrationAnswerResponse:
    """
    Submit one answer to the re-calibration interview.
    Call repeatedly until complete=True.
    When complete, the UserProfile is updated and the coach generates a synthesis
    of what has changed and what it means for the next coaching period.
    """
    result = process_recalibration_answer(
        db,
        user_id=payload.user_id,
        milestone_days=payload.milestone_days,
        question_id=payload.question_id,
        answer=payload.answer,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return RecalibrationAnswerResponse(**result)


# ── V5: Quarterly 90-Day Retrospective ───────────────────────────────────────
from app.services.quarterly_retrospective import generate_quarterly_retrospective
from app.schemas import QuarterlyRetrospectiveResponse


@app.get("/coach/report/quarterly", response_model=QuarterlyRetrospectiveResponse, tags=["Reports"])
def quarterly_retrospective(
    user_id: str = Query(default="default"),
    sprint_end_date: str | None = Query(default=None, description="YYYY-MM-DD, defaults to today"),
    db: Session = Depends(get_db),
) -> QuarterlyRetrospectiveResponse:
    """
    Full 90-day coaching retrospective — the premium end-of-sprint document.

    Five sections:
      I.   The Numbers — energy arc, habit rates, commitment integrity, decisions
      II.  The Story — coach's narrative of the quarter, pivotal moments, what was avoided
      III. The Wins — named wins, milestones, the underrated win
      IV.  The Lessons — what stuck, what didn't, recurring obstacles
      V.   The Bridge — priorities for the next sprint, what to stop, what to protect

    Written to be read, shared with a mentor, and kept as a record of growth.
    This is the document a $500/month coaching client expects.
    """
    result = generate_quarterly_retrospective(db, user_id, sprint_end_date=sprint_end_date)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return QuarterlyRetrospectiveResponse(**result)


# ── V6: First Read, Trial Closing, Memory Context ────────────────────────────
from app.services.first_read import generate_first_read, mark_first_read_delivered
from app.services.trial_closing import generate_trial_closing_report
from app.services.memory_context import build_coach_memory_context, get_context_summary
from app.schemas import (
    FirstReadResponse,
    FirstReadDeliveredResponse,
    TrialClosingReportResponse,
    MemoryContextResponse,
    MemoryContextSummaryResponse,
)


@app.get("/coach/first-read", response_model=FirstReadResponse, tags=["Retention"])
async def get_first_read(
    user_id: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> FirstReadResponse:
    """
    The First Read — the #1 retention feature.

    Generated once, delivered once, after onboarding is complete.
    A deep personality synthesis of the user based on their intake data:
    opening observation, undervalued strength, blind spot, relationship pattern,
    one-sentence portrait, and coaching intention.

    Written in the coach's voice. No bullet points. Flowing prose.
    This is the moment the user thinks: 'This coach actually sees me.'

    Call this endpoint to generate (or retrieve cached) the First Read.
    Use POST /coach/first-read/delivered to mark it as shown.
    """
    result = await generate_first_read(db, user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return FirstReadResponse(**result)


@app.post("/coach/first-read/delivered", response_model=FirstReadDeliveredResponse, tags=["Retention"])
def mark_first_read_as_delivered(
    user_id: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> FirstReadDeliveredResponse:
    """
    Mark the First Read as delivered (shown to user).

    Call this after the frontend has displayed the First Read to the user.
    Used to track whether the user has seen their synthesis.
    """
    mark_first_read_delivered(db, user_id)
    return FirstReadDeliveredResponse(marked_delivered=True)


@app.get("/coach/trial-closing", response_model=TrialClosingReportResponse, tags=["Retention"])
def get_trial_closing_report(
    user_id: str = Query(default="default"),
    trial_days: int = Query(default=7, description="Trial length in days (default 7)"),
    force_regenerate: bool = Query(default=False, description="Force fresh generation"),
    db: Session = Depends(get_db),
) -> TrialClosingReportResponse:
    """
    7-Day Trial Closing Report — the conversion moment built into the product.

    Not a marketing email. A coach-voiced, data-rich retrospective of the trial period:
      Opening    — what the coach saw in 7 days (specific to this user)
      The Data   — hard numbers: check-ins, habits, energy arc, commitments
      The Insight — the single most important thing the coach learned
      The Gap    — what is still unresolved; what month two can do
      The Offer  — one concrete sentence: what the coach will deliver in month two

    Generated once and cached. Call with force_regenerate=true to refresh.
    """
    result = generate_trial_closing_report(db, user_id, trial_days=trial_days, force_regenerate=force_regenerate)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return TrialClosingReportResponse(**result)


@app.get("/coach/memory-context", response_model=MemoryContextResponse, tags=["Coach"])
def get_memory_context(
    user_id: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> MemoryContextResponse:
    """
    The full memory context string injected into every coaching conversation.

    Returns the exact text that is prepended to the coach's system prompt —
    the briefing that makes the coach feel like it genuinely remembers the user.

    Includes: profile, recent energy, habits, open commitments,
    First Read findings, stressors, relationships, milestone progress.

    Primarily for debugging and transparency. The /coach/ask endpoint
    uses this automatically.
    """
    context = build_coach_memory_context(db, user_id)
    return MemoryContextResponse(
        memory_context=context,
        character_count=len(context),
    )


@app.get("/coach/memory-summary", response_model=MemoryContextSummaryResponse, tags=["Coach"])
def get_memory_summary(
    user_id: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> MemoryContextSummaryResponse:
    """
    Lightweight summary of what the coach's memory contains for this user.

    Returns counts and a 'memory richness' label:
      early       — fewer than 3 days of data
      developing  — 7+ days, some check-ins
      established — 30+ days with habits and First Read
      deep        — full picture with milestones and extended history

    Useful for showing users how much context the coach has accumulated.
    """
    summary = get_context_summary(db, user_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    return MemoryContextSummaryResponse(**summary)


# ── Push Notifications ────────────────────────────────────────────────────────
import os as _os
from app.services.notifications import (
    delete_subscription,
    get_subscription_count,
    save_subscription,
    send_evening_notifications,
    send_morning_notifications,
)

_NOTIFICATION_SECRET = _os.getenv("NOTIFICATION_SECRET", "")
_VAPID_PUBLIC_KEY = _os.getenv("VAPID_PUBLIC_KEY", "")


@app.get("/push/vapid-public-key", tags=["Push"])
def get_vapid_public_key():
    """Return the VAPID public key so the frontend can subscribe."""
    return {"public_key": _VAPID_PUBLIC_KEY}


@app.post("/push/subscribe", tags=["Push"])
def push_subscribe(payload: dict, db: Session = Depends(get_db)):
    """
    Register (or refresh) a push subscription for a user device.
    Body: { user_id, endpoint, p256dh, auth, user_agent? }
    """
    user_id = payload.get("user_id", "default")
    endpoint = payload.get("endpoint", "")
    p256dh = payload.get("p256dh", "")
    auth = payload.get("auth", "")
    user_agent = payload.get("user_agent", "")

    if not endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="endpoint, p256dh, and auth are required")

    sub = save_subscription(db, user_id, endpoint, p256dh, auth, user_agent)
    count = get_subscription_count(db, user_id)
    return {"subscribed": True, "subscription_id": sub.id, "total_devices": count}


@app.post("/push/unsubscribe", tags=["Push"])
def push_unsubscribe(payload: dict, db: Session = Depends(get_db)):
    """Remove a push subscription (user turned off notifications)."""
    endpoint = payload.get("endpoint", "")
    if not endpoint:
        raise HTTPException(status_code=400, detail="endpoint required")
    deleted = delete_subscription(db, endpoint)
    return {"unsubscribed": deleted}


@app.post("/push/send-morning", tags=["Push"])
def trigger_morning_push(request: Request, db: Session = Depends(get_db)):
    """
    Send morning coaching nudge to all subscribers.
    Protected by NOTIFICATION_SECRET bearer token.
    Call this from an external cron at 8 AM IST (2:30 AM UTC).
    """
    if _NOTIFICATION_SECRET:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if token != _NOTIFICATION_SECRET:
            raise HTTPException(status_code=401, detail="Invalid secret")
    result = send_morning_notifications(db)
    return result


@app.post("/push/send-evening", tags=["Push"])
def trigger_evening_push(request: Request, db: Session = Depends(get_db)):
    """
    Send evening reflection reminder to all subscribers.
    Protected by NOTIFICATION_SECRET bearer token.
    Call this from an external cron at 7 PM IST (1:30 PM UTC).
    """
    if _NOTIFICATION_SECRET:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if token != _NOTIFICATION_SECRET:
            raise HTTPException(status_code=401, detail="Invalid secret")
    result = send_evening_notifications(db)
    return result


# ── Spiritual Wisdom ──────────────────────────────────────────────────────────

@app.get("/wisdom/daily", tags=["Wisdom"])
def wisdom_daily(user_id: str = Query(...), db: Session = Depends(get_db)):
    """
    Return today's contextual wisdom teaching for a user.
    Picks deterministically by date so the same entry shows all day,
    but rotates daily based on the user's recent check-in state.
    """
    entry = get_contextual_wisdom(user_id, db)
    if not entry:
        return {"wisdom": None}
    return {
        "wisdom": {
            "id": entry.id,
            "master": entry.master,
            "tradition": entry.tradition,
            "era": entry.era,
            "quote": entry.quote,
            "source": entry.source,
            "themes": entry.themes,
            "reflection": entry.reflection,
            "is_scripture": entry.is_scripture,
        }
    }


@app.post("/wisdom/ask", tags=["Wisdom"])
async def wisdom_ask(payload: dict, db: Session = Depends(get_db)):
    """
    Ask the Masters — synthesize wisdom from the corpus in response to any question.
    Body: { user_id: str, question: str }
    Returns: { synthesis: str, citations: [...], theme: str }
    """
    user_id = payload.get("user_id", "default")
    question = payload.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    result = await ask_masters(question, user_id, db)
    return result


@app.get("/wisdom/corpus", tags=["Wisdom"])
def wisdom_corpus(db: Session = Depends(get_db)):
    """
    Return a summary of all masters and scriptures in the wisdom corpus.
    Used to display the 'Meet the Masters' section in the frontend.
    """
    entries = db.query(SpiritualWisdom).filter(SpiritualWisdom.active == True).all()
    # Aggregate by master
    masters: dict[str, dict] = {}
    for e in entries:
        if e.master not in masters:
            masters[e.master] = {
                "master": e.master,
                "tradition": e.tradition,
                "era": e.era,
                "is_scripture": e.is_scripture,
                "count": 0,
            }
        masters[e.master]["count"] += 1
    return {"masters": list(masters.values()), "total_teachings": len(entries)}


# ── The Council ───────────────────────────────────────────────────────────────

@app.post("/council/ask", tags=["Council"])
async def council_ask(body: dict, db: Session = Depends(get_db)):
    """
    The Council: four simultaneous voices (Sage, Strategist, Heart, Scientist)
    respond together to a single question. Returns a structured response with
    all four voice perspectives plus a unified synthesis.
    """
    user_id = str(body.get("user_id", ""))
    question = str(body.get("question", "")).strip()
    history = body.get("history", [])
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    result = await ask_council(question, user_id, history, db)
    return result
