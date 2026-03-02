from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserProfile(Base, TimestampMixin):
    """Created during onboarding interview. Powers all personalisation."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Identity
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    organization: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    organization_type: Mapped[str] = mapped_column(String(128), default="")

    # Context from onboarding interview
    biggest_challenge: Mapped[str] = mapped_column(Text, default="")
    key_relationships: Mapped[list] = mapped_column(JSON, default=list)
    core_values: Mapped[list] = mapped_column(JSON, default=list)
    goals_90_days: Mapped[list] = mapped_column(JSON, default=list)
    current_stressors: Mapped[list] = mapped_column(JSON, default=list)
    coaching_style_preference: Mapped[str] = mapped_column(String(128), default="direct")
    preferred_language: Mapped[str] = mapped_column(String(32), default="en")

    # Onboarding state
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0)
    onboarding_answers_raw: Mapped[dict] = mapped_column(JSON, default=dict)
    profile_summary: Mapped[str] = mapped_column(Text, default="")  # saved at onboarding completion

    # Evolving profile
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    last_profile_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Behavioural signals — updated over time from check-ins
    energy_baseline: Mapped[float] = mapped_column(Float, default=7.0)   # rolling avg 1-10
    burnout_risk: Mapped[str] = mapped_column(String(32), default="low")  # low / moderate / high
    consecutive_low_energy_days: Mapped[int] = mapped_column(Integer, default=0)

    # Calendar integration (optional — toggled by user in iOS settings)
    calendar_integration_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    calendar_provider: Mapped[str] = mapped_column(String(64), default="")   # "google" | "apple" | ""
    calendar_last_synced: Mapped[str] = mapped_column(String(32), default="")  # ISO datetime of last sync


class CoachConversation(Base, TimestampMixin):
    """Encrypted conversation turns. Retention-controlled."""

    __tablename__ = "coach_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    intent: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="general")
    user_message_enc: Mapped[str] = mapped_column(Text, nullable=False)
    coach_message_enc: Mapped[str] = mapped_column(Text, nullable=False)
    context_enc: Mapped[str] = mapped_column(Text, nullable=False)
    coach_model: Mapped[str] = mapped_column(String(128), nullable=False, default="fallback-local")
    retention_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class DailyCheckIn(Base, TimestampMixin):
    """30-second daily check-in powering the Burnout Sentinel."""

    __tablename__ = "daily_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    check_in_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    energy: Mapped[float] = mapped_column(Float, nullable=False)        # 1-10
    stress: Mapped[float] = mapped_column(Float, nullable=False)        # 1-10
    sleep_quality: Mapped[float] = mapped_column(Float, default=7.0)    # 1-10
    mood_note: Mapped[str] = mapped_column(Text, default="")
    coach_response: Mapped[str] = mapped_column(Text, default="")


class HabitRecord(Base, TimestampMixin):
    """A single keystone habit the user is tracking."""

    __tablename__ = "habit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    track: Mapped[str] = mapped_column(String(64), default="general")   # leadership / relationship / wellbeing
    target_frequency: Mapped[str] = mapped_column(String(32), default="daily")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class HabitCompletion(Base, TimestampMixin):
    """One completion entry per habit per day."""

    __tablename__ = "habit_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    habit_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    completion_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, default="")


class WeeklyReflection(Base, TimestampMixin):
    """Sunday reflection ritual stored per user per week."""

    __tablename__ = "weekly_reflections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    week_start: Mapped[str] = mapped_column(String(10), nullable=False)   # YYYY-MM-DD (Monday)
    biggest_win: Mapped[str] = mapped_column(Text, default="")
    biggest_lesson: Mapped[str] = mapped_column(Text, default="")
    one_commitment_next_week: Mapped[str] = mapped_column(Text, default="")
    coach_synthesis: Mapped[str] = mapped_column(Text, default="")        # AI summary of the week


class KnowledgeItem(Base, TimestampMixin):
    """
    The coach's living knowledge base.
    Replaces the hardcoded CATALOG in research_intel.py.
    Fed by automated PubMed ingestion and manual additions.
    """

    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)   # pubmed / manual / book / framework
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    authors: Mapped[str] = mapped_column(String(512), default="")
    published_date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    takeaway: Mapped[str] = mapped_column(Text, nullable=False)           # one-line coaching insight
    application: Mapped[str] = mapped_column(Text, nullable=False)        # how the coach uses it
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)                # ["leadership","burnout",…]
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)    # curator quality signal
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GoalMilestone(Base, TimestampMixin):
    """
    Weekly milestones auto-generated from the user's 90-day goals (set in onboarding).
    Tracks progress toward each goal, week by week.
    Powers the 90-Day Sprint Dashboard.
    """

    __tablename__ = "goal_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    goal_index: Mapped[int] = mapped_column(Integer, nullable=False)          # 0, 1, 2 (up to 3 goals)
    goal_text: Mapped[str] = mapped_column(Text, nullable=False)
    goal_track: Mapped[str] = mapped_column(String(64), default="leadership")  # leadership / relationships / energy
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)          # 1-12 (12 weeks = 90 days)
    week_start: Mapped[str] = mapped_column(String(10), nullable=False)        # YYYY-MM-DD
    milestone_description: Mapped[str] = mapped_column(Text, default="")       # coach-generated milestone
    status: Mapped[str] = mapped_column(String(32), default="pending")         # pending / on_track / at_risk / complete
    user_update: Mapped[str] = mapped_column(Text, default="")                 # what user reported
    coach_response: Mapped[str] = mapped_column(Text, default="")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)              # 0-100


class DecisionLog(Base, TimestampMixin):
    """
    Every major decision the user discusses with the coach.
    Pre-mortem run at decision time. Review run 30 days later.
    One of the most powerful features: the coach shows you patterns in HOW you decide.
    """

    __tablename__ = "decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    decision_date: Mapped[str] = mapped_column(String(10), nullable=False)     # YYYY-MM-DD
    decision_title: Mapped[str] = mapped_column(String(512), nullable=False)
    decision_description: Mapped[str] = mapped_column(Text, default="")
    options_considered: Mapped[list] = mapped_column(JSON, default=list)       # list of strings
    premortem_failure_modes: Mapped[list] = mapped_column(JSON, default=list)  # what could go wrong
    gut_says: Mapped[str] = mapped_column(Text, default="")
    coach_recommendation: Mapped[str] = mapped_column(Text, default="")
    final_decision: Mapped[str] = mapped_column(Text, default="")
    review_date: Mapped[str] = mapped_column(String(10), nullable=False)       # YYYY-MM-DD (decision_date + 30 days)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    actual_outcome: Mapped[str] = mapped_column(Text, default="")
    coach_review_observation: Mapped[str] = mapped_column(Text, default="")


class ConflictPrep(Base, TimestampMixin):
    """
    Pre-conversation coaching session for a difficult interaction.
    Boss meeting, board presentation, conflict with spouse, negotiation.
    The coach prepares the user: what to say, what not to say, how to open, how to close.
    """

    __tablename__ = "conflict_preps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prep_date: Mapped[str] = mapped_column(String(10), nullable=False)
    conversation_type: Mapped[str] = mapped_column(String(128), default="")     # difficult_conversation / negotiation / feedback / repair
    other_person: Mapped[str] = mapped_column(String(255), default="")
    relationship_to_user: Mapped[str] = mapped_column(String(128), default="")  # boss / partner / board / team
    situation_description: Mapped[str] = mapped_column(Text, default="")
    user_desired_outcome: Mapped[str] = mapped_column(Text, default="")
    user_fear: Mapped[str] = mapped_column(Text, default="")
    coach_opening_line: Mapped[str] = mapped_column(Text, default="")
    coach_key_points: Mapped[list] = mapped_column(JSON, default=list)
    coach_what_not_to_say: Mapped[list] = mapped_column(JSON, default=list)
    coach_closing_move: Mapped[str] = mapped_column(Text, default="")
    coach_mindset_anchor: Mapped[str] = mapped_column(Text, default="")         # one calming reminder to carry in
    full_prep_script: Mapped[str] = mapped_column(Text, default="")


class HealthData(Base, TimestampMixin):
    """
    HealthKit / wearable data received from iOS.
    Enriches the coaching context with objective physiological data.
    Fields are nullable — the coach works with whatever data is available.
    """

    __tablename__ = "health_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    data_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100 from HealthKit
    hrv_ms: Mapped[float | None] = mapped_column(Float, nullable=True)               # heart rate variability
    resting_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mindful_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coaching_note: Mapped[str] = mapped_column(Text, default="")                     # coach's reading of this data


class Achievement(Base, TimestampMixin):
    """
    Milestone celebrations.
    The coach actively notices and celebrates meaningful moments —
    7-day habit streaks, 30-day consistency, goal completions, recovery from a burnout week.
    Real coaches celebrate. Most apps don't.
    """

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    achievement_date: Mapped[str] = mapped_column(String(10), nullable=False)
    achievement_type: Mapped[str] = mapped_column(String(128), nullable=False)  # habit_streak / goal_complete / recovery / consistency
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    coach_message: Mapped[str] = mapped_column(Text, nullable=False)
    data_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)             # the numbers that triggered this
    celebrated: Mapped[bool] = mapped_column(Boolean, default=False)            # shown to user yet?


class CalendarEvent(Base, TimestampMixin):
    """
    Calendar events synced from iOS (EventKit / Google Calendar SDK).
    Architecture: iOS handles all OAuth. The app pushes the next 7 days of events
    to this endpoint daily. The backend enriches them with coaching context.

    The coach uses calendar data to:
      - Generate pre-meeting briefs (30 min before a significant meeting)
      - Send post-meeting reflection prompts (30 min after)
      - Analyse meeting density (manager vs. maker schedule health)
      - Reference upcoming events in morning brief
      - Correlate meeting-heavy days with energy dips in monthly report

    Privacy: Calendar data is stored per user, never aggregated.
    If the user disables calendar sync, new events stop arriving.
    Historical events are retained (the coach remembers past meetings).
    """

    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_event_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)  # ID from calendar provider
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    start_datetime: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # ISO: YYYY-MM-DDTHH:MM:SS
    end_datetime: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    attendees: Mapped[list] = mapped_column(JSON, default=list)          # list of {"name": ..., "email": ...}
    calendar_provider: Mapped[str] = mapped_column(String(64), default="")  # "google" | "apple"
    event_type: Mapped[str] = mapped_column(String(64), default="meeting")  # meeting / focus / personal / travel / 1on1 / board
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    is_coaching_relevant: Mapped[bool] = mapped_column(Boolean, default=True)   # coach flags high-stakes meetings

    # Coaching annotations — generated by calendar_coach.py
    pre_meeting_brief: Mapped[str] = mapped_column(Text, default="")            # generated 30 min before
    pre_brief_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    post_meeting_prompt: Mapped[str] = mapped_column(Text, default="")          # sent 30 min after
    post_prompt_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    user_post_meeting_note: Mapped[str] = mapped_column(Text, default="")       # user's reflection
    coach_post_meeting_synthesis: Mapped[str] = mapped_column(Text, default="") # coach's reading of the note


class Commitment(Base, TimestampMixin):
    """
    Every commitment the user makes — tracked, followed-up, closed.

    This is the feature that separates coaching from advice.
    A real coach remembers every promise you made to yourself.
    "Last Monday you said you'd have the difficult conversation with Arjun by Wednesday.
     It's Thursday. Your coach is asking: did you?"

    Commitments are created automatically from:
      - Evening review ("one commitment next week")
      - Weekly reflection ("one commitment next week")
      - Conflict prep sessions ("follow up with X by date Y")
      - Decision logs ("next step is...")
      - Direct conversation with the coach

    The commitment lifecycle:
      open → checked_in → kept | missed | partial

    The coach checks open commitments in every morning brief and
    evening review. Kept commitments feed the achievement engine.
    Missed commitments trigger a non-judgmental coach inquiry.
    """

    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    commitment_text: Mapped[str] = mapped_column(Text, nullable=False)           # what the user committed to
    due_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    source: Mapped[str] = mapped_column(String(64), default="direct")            # direct / evening_review / reflection / conflict_prep / decision / morning_brief
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)        # FK to the originating record (optional)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)  # open / kept / missed / partial / deferred
    user_completion_note: Mapped[str] = mapped_column(Text, default="")          # what the user reported
    coach_followup_message: Mapped[str] = mapped_column(Text, default="")        # coach's response when checked
    checked_at: Mapped[str | None] = mapped_column(String(32), nullable=True)    # ISO datetime of check-in
    deferred_to: Mapped[str] = mapped_column(String(10), default="")             # YYYY-MM-DD if deferred


class RecalibrationSession(Base, TimestampMixin):
    """
    30/60/90-day profile re-calibration sessions.
    The coach re-interviews the user at key milestones to deepen understanding.

    At 30 days: "A month has passed. A lot has changed. Let's recalibrate."
    At 60 days: Energy, relationship, and goal recalibration.
    At 90 days: Full re-interview — new goals, updated challenges, evolved values.

    Answers update the UserProfile directly (goals_90_days, biggest_challenge, etc.).
    Each session is stored here for the coach's longitudinal memory.
    """

    __tablename__ = "recalibration_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    milestone_days: Mapped[int] = mapped_column(Integer, nullable=False)         # 30 / 60 / 90
    session_date: Mapped[str] = mapped_column(String(10), nullable=False)        # YYYY-MM-DD
    questions_asked: Mapped[list] = mapped_column(JSON, default=list)            # list of question strings
    answers_raw: Mapped[dict] = mapped_column(JSON, default=dict)                # question → answer
    coach_synthesis: Mapped[str] = mapped_column(Text, default="")               # what changed, what evolved
    profile_changes: Mapped[dict] = mapped_column(JSON, default=dict)            # which profile fields were updated


class FirstRead(Base, TimestampMixin):
    """
    The coach's initial deep synthesis of a new client — generated once,
    immediately after onboarding is complete.

    This is the single highest-leverage retention feature in the product.
    If the user reads this and thinks 'how did it know that about me?'
    they will pay. Every time.

    Written in coach voice. Five sections:
      1. Opening Observation — who is this person under pressure?
      2. The Undervalued Strength — what they showed but may not see
      3. The Likely Blind Spot — what gets in the way for people like them
      4. The Relationship Pattern — what their key relationships reveal
      5. The One Sentence — the most telling thing they said, interpreted
      6. What Your Coach Intends — how the coaching will be structured for them

    Not a summary. A diagnosis.
    Surfaced prominently in the morning brief on day one.
    Accessible anytime from the profile screen.
    """

    __tablename__ = "first_reads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    generated_at: Mapped[str] = mapped_column(String(32), nullable=False)  # ISO datetime
    full_text: Mapped[str] = mapped_column(Text, nullable=False)           # the full document
    opening_observation: Mapped[str] = mapped_column(Text, default="")
    undervalued_strength: Mapped[str] = mapped_column(Text, default="")
    blind_spot: Mapped[str] = mapped_column(Text, default="")
    relationship_pattern: Mapped[str] = mapped_column(Text, default="")
    one_sentence: Mapped[str] = mapped_column(Text, default="")            # the key quote + interpretation
    coach_intention: Mapped[str] = mapped_column(Text, default="")
    model_used: Mapped[str] = mapped_column(String(128), default="fallback")
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)        # shown to user yet?


class TrialClosingReport(Base, TimestampMixin):
    """
    The 7-day trial closing report — the product's conversion moment.

    Generated when the 7-day trial ends (or on demand).
    This is NOT a marketing email. It is a coaching document.
    The coach writes a personal note about what it observed in 7 days,
    what was built, what's still open, and what the next 30 days would look like.

    The goal: make leaving feel like a genuine loss.
    Not because of dark patterns — because the user has actually built something
    worth keeping in 7 days.
    """

    __tablename__ = "trial_closing_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    generated_at: Mapped[str] = mapped_column(String(32), nullable=False)
    trial_day_count: Mapped[int] = mapped_column(Integer, default=7)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    check_in_count: Mapped[int] = mapped_column(Integer, default=0)
    habit_count: Mapped[int] = mapped_column(Integer, default=0)
    open_commitment_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_energy: Mapped[float | None] = mapped_column(Float, nullable=True)


# ── Calendar settings stored on UserProfile ─────────────────────────────────
# These fields are added as a mixin to avoid rewriting UserProfile.
# In practice, SQLAlchemy will add them in the same table.
# The iOS app handles OAuth — we never store tokens in this DB.
# We only store the user's intent (enabled / provider) and last sync time.


class SpiritualWisdom(Base, TimestampMixin):
    """
    Curated corpus of teachings from great spiritual masters and sacred scriptures.
    Powers the Spiritual Intelligence feature — contextual wisdom matched to the user's
    current life situation, and the 'Ask the Masters' deep-dive interface.

    Sources span 22 traditions across 2,500 years:
    Bhagavad Gita, Bible, Quran, Ramayana, Vivekananda, Yogananda, Ramana Maharshi,
    Buddha, Mahavira, Kabir, Rumi, Shankaracharya, Marcus Aurelius, Laozi, and more.
    """

    __tablename__ = "spiritual_wisdom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    master: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tradition: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    era: Mapped[str] = mapped_column(String(128), default="")            # e.g. "1st century BCE", "1863–1902"
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(512), default="")         # book / chapter / verse
    themes: Mapped[list] = mapped_column(JSON, default=list)             # leadership, ego, discipline, etc.
    reflection: Mapped[str] = mapped_column(Text, default="")            # one-line coaching context
    is_scripture: Mapped[bool] = mapped_column(Boolean, default=False)   # True for Gita, Bible, Quran, Ramayana
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PushSubscription(Base, TimestampMixin):
    """Web Push subscription for a user device. One row per browser/device."""

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)   # browser public key
    auth: Mapped[str] = mapped_column(Text, nullable=False)     # auth secret
    user_agent: Mapped[str] = mapped_column(Text, default="")
    # Track what was last sent so we don't double-send on restart
    last_morning_sent: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD
    last_evening_sent: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD
