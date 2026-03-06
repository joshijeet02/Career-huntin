from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Onboarding ──────────────────────────────────────────────────────────────

class OnboardingStepRequest(BaseModel):
    user_id: str
    question_key: str = ""
    step: int = -1          # optional — server uses profile.onboarding_step instead
    answer: str
    session_id: str = "onboarding"


class OnboardingStepResponse(BaseModel):
    next_question: str | None
    step: int
    total_steps: int
    complete: bool
    profile_summary: str | None = None


class OnboardingStatusResponse(BaseModel):
    user_id: str
    complete: bool
    step: int
    total_steps: int
    profile: dict[str, Any] | None = None


# ── User Profile ──────────────────────────────────────────────────────────────

class UserProfileOut(BaseModel):
    user_id: str
    full_name: str
    role: str
    organization: str
    biggest_challenge: str
    core_values: list[str]
    goals_90_days: list[dict[str, Any]]
    coaching_style_preference: str
    onboarding_complete: bool
    profile_version: int
    last_profile_update: datetime
    energy_baseline: float
    burnout_risk: str
    profile_summary: str = ""
    wisdom_preferences: list[str] = Field(default_factory=list)


class WisdomPreferencesUpdate(BaseModel):
    user_id: str = "default"
    traditions: list[str]


# ── Daily Check-In ────────────────────────────────────────────────────────────

class DailyCheckInRequest(BaseModel):
    user_id: str = "default"
    energy: float = Field(..., ge=1, le=10, description="Energy level 1-10")
    stress: float = Field(..., ge=1, le=10, description="Stress level 1-10")
    sleep_quality: float = Field(7.0, ge=1, le=10)
    mood_note: str = ""


class DailyCheckInResponse(BaseModel):
    check_in_date: str
    burnout_risk: str
    consecutive_low_energy_days: int
    coach_response: str
    alert: str | None = None   # populated when risk is high


# ── Habits ─────────────────────────────────────────────────────────────────────

class HabitCreateRequest(BaseModel):
    user_id: str = "default"
    name: str
    track: str = "general"
    target_frequency: str = "daily"


class HabitCompleteRequest(BaseModel):
    user_id: str = "default"
    habit_id: int
    note: str = ""


class HabitOut(BaseModel):
    id: int
    name: str
    track: str
    target_frequency: str
    current_streak: int
    total_completions: int


class HabitsResponse(BaseModel):
    habits: list[HabitOut]
    completion_rate_7d: float   # 0.0 – 1.0


# ── Weekly Reflection ─────────────────────────────────────────────────────────

class WeeklyReflectionRequest(BaseModel):
    user_id: str = "default"
    biggest_win: str
    biggest_lesson: str
    one_commitment_next_week: str


class WeeklyReflectionResponse(BaseModel):
    week_start: str
    coach_synthesis: str


# ── Coaching ──────────────────────────────────────────────────────────────────

class CoachRequest(BaseModel):
    context: str
    goal: str = "Guide with practical coaching actions."
    track: str = "general"
    user_id: str = "default"


class CoachResponse(BaseModel):
    message: str
    suggested_actions: list[str] = Field(default_factory=list)


class CoachConversationMessageRequest(BaseModel):
    user_id: str = "default"
    session_id: str = "default"
    message: str
    context: str = ""
    goal: str = "Guide with practical coaching actions."
    track: str = "general"


class CoachConversationMessageResponse(BaseModel):
    message: str
    suggested_actions: list[str] = Field(default_factory=list)
    conversation_id: int


class CouncilSynthesisRequest(BaseModel):
    user_id: str = "default"
    days_to_analyze: int = 30


class CouncilSynthesisResponse(BaseModel):
    markdown_report: str
    generated_at: datetime
    days_analyzed: int


class CoachConversationHistoryItem(BaseModel):
    id: int
    user_id: str
    session_id: str
    intent: str
    user_message: str
    coach_message: str
    created_at: datetime


class RetentionPurgeResponse(BaseModel):
    deleted_count: int


# ── Knowledge Base ────────────────────────────────────────────────────────────

class KnowledgeItemOut(BaseModel):
    id: int
    external_id: str
    source: str
    title: str
    authors: str
    published_date: str
    category: str
    takeaway: str
    application: str
    source_url: str
    tags: list[str]
    relevance_score: float
    ingested_at: datetime


class KnowledgeIngestManualRequest(BaseModel):
    title: str
    takeaway: str
    application: str
    source_url: str = ""
    authors: str = ""
    published_date: str = ""
    abstract: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    relevance_score: float = 1.5
    source: str = "manual"


class KnowledgeIngestResponse(BaseModel):
    added: int
    skipped: int
    errors: int


class KnowledgeStatsResponse(BaseModel):
    total_items: int
    by_source: dict[str, int]
    by_category: dict[str, int]
    last_ingested_at: str | None


# ── Research & Intelligence (legacy-compatible) ───────────────────────────────

class ResearchInsightOut(BaseModel):
    id: str
    title: str
    published_date: str
    category: str
    takeaway: str
    application: str
    source_url: str


class PremiumFeatureOut(BaseModel):
    name: str
    description: str
    delivery_frequency: str
    evidence_ids: list[str] = Field(default_factory=list)


class PremiumTierOut(BaseModel):
    tier_name: str
    price_usd_per_month: int
    ideal_for: str
    features: list[PremiumFeatureOut] = Field(default_factory=list)


# ── Conversational Check-In ───────────────────────────────────────────────────

class ConversationalCheckInStartResponse(BaseModel):
    opening_question: str
    already_checked_in_today: bool
    check_in_date: str


class ConversationalCheckInRequest(BaseModel):
    user_id: str = "default"
    user_response: str
    tone_hint: str | None = None   # "tired" | "energized" | "angry" | "distressed" | "neutral"
    is_followup_response: bool = False
    followup_response_text: str | None = None


class ConversationalCheckInResponse(BaseModel):
    status: str                    # "complete" | "needs_followup"
    followup_question: str | None = None
    check_in_date: str
    energy: float
    stress: float
    sleep_quality: float
    burnout_risk: str | None = None
    coach_response: str | None = None
    alert: str | None = None
    dominant_track: str = "leadership"
    relationship_flag: bool = False


# ── Proactive Coach ───────────────────────────────────────────────────────────

class MorningBriefResponse(BaseModel):
    brief_text: str
    points: list[str]
    generated_at: str
    user_id: str


class EveningReviewQuestionsResponse(BaseModel):
    intro: str
    questions: list[str]
    closing_note: str


class EveningReviewRequest(BaseModel):
    user_id: str = "default"
    biggest_win: str
    biggest_regret: str
    who_showed_up_for: str


class EveningReviewResponse(BaseModel):
    coach_observation: str
    tomorrow_intention: str
    logged_at: str


class CoachNotebookEntryResponse(BaseModel):
    entry_text: str
    patterns: list[str]
    generated_at: str
    user_id: str


class RelationshipNudge(BaseModel):
    relationship: str
    nudge: str
    priority: str   # "high" | "medium"


class WeeklyReadingAssignmentResponse(BaseModel):
    assignment: str
    source_url: str | None = None
    track: str
    knowledge_item_id: int | None = None


# ── Voice ─────────────────────────────────────────────────────────────────────

class VoiceTranscriptRequest(BaseModel):
    """
    The iOS app sends the Whisper-transcribed text here, along with
    the tone_hint derived from iOS audio analysis (AVAudioEngine).
    The backend never handles raw audio — transcription happens on-device or
    in the iOS layer to minimize latency and cost.
    """
    user_id: str = "default"
    transcript: str
    tone_hint: str | None = None    # iOS-detected: "tired"|"energized"|"angry"|"distressed"|"neutral"
    session_id: str = "voice"
    context: str = ""               # optional additional context
    track: str = "general"


class VoiceCoachResponse(BaseModel):
    """
    Response to a voice message. The `tts_text` field is the exact text
    that should be spoken aloud (may differ from `full_response` which
    can include structured formatting). The iOS app passes tts_text to
    ElevenLabs / AVSpeechSynthesizer.
    """
    full_response: str
    tts_text: str                   # clean, spoken-language version for TTS
    suggested_actions: list[str] = Field(default_factory=list)
    dominant_track: str = "general"
    relationship_flag: bool = False
    conversation_id: int | None = None

# ── 90-Day Sprint Dashboard ───────────────────────────────────────────────────

class SprintDashboardResponse(BaseModel):
    status: str
    current_sprint_week: int | None = None
    sprint_health_pct: int | None = None
    goals: list[dict[str, Any]] = Field(default_factory=list)
    user_id: str
    message: str | None = None


class MilestoneUpdateRequest(BaseModel):
    user_id: str = "default"
    goal_index: int
    week_number: int
    user_update: str
    progress_pct: int = Field(..., ge=0, le=100)


class MilestoneUpdateResponse(BaseModel):
    goal_index: int
    week_number: int
    status: str
    progress_pct: int
    coach_response: str


# ── Big Goals ─────────────────────────────────────────────────────────────────

class BigGoalCreateRequest(BaseModel):
    user_id: str = "default"
    title: str
    description: str = ""
    target_date: str | None = None # YYYY-MM-DD
    category: str = "growth"

class BigGoalOut(BaseModel):
    id: int
    user_id: str
    title: str
    description: str
    target_date: str | None
    status: str
    category: str
    progress_pct: int
    vision_statement: str = ""

class BigGoalUpdateResponse(BaseModel):
    goal_id: int
    status: str
    progress_pct: int
    coach_response: str


class SprintRetrospectiveResponse(BaseModel):
    retrospective_text: str
    goals_summary: dict[str, Any]
    user_id: str
    generated_at: str


# ── Decision Coach ────────────────────────────────────────────────────────────

class DecisionPremortemQuestionsResponse(BaseModel):
    intro: str
    questions: list[str]


class LogDecisionRequest(BaseModel):
    user_id: str = "default"
    decision_title: str
    decision_description: str = ""
    options_considered: list[str] = Field(default_factory=list)
    premortem_failure_modes: list[str] = Field(default_factory=list)
    gut_says: str = ""


class LogDecisionResponse(BaseModel):
    decision_id: int
    coach_recommendation: str
    review_date: str
    message: str


class FinalDecisionRequest(BaseModel):
    user_id: str = "default"
    decision_id: int
    final_decision: str


class DecisionReviewRequest(BaseModel):
    user_id: str = "default"
    decision_id: int
    actual_outcome: str


class DecisionReviewResponse(BaseModel):
    coach_review_observation: str
    decision_id: int
    reviewed_at: str


class DecisionPatternResponse(BaseModel):
    pattern_analysis: str | None = None
    decisions_logged: int
    message: str | None = None


# ── Conflict Preparation ──────────────────────────────────────────────────────

class ConflictPrepRequest(BaseModel):
    user_id: str = "default"
    conversation_type: str = "feedback"
    other_person: str
    relationship_to_user: str
    situation_description: str
    desired_outcome: str
    user_fear: str = ""


class ConflictPrepResponse(BaseModel):
    prep_id: int
    full_prep_script: str
    opening_line: str
    key_points: list[str]
    what_not_to_say: list[str]
    closing_line: str
    mindset_anchor: str
    framework: str


class ConflictPrepListItem(BaseModel):
    prep_id: int
    prep_date: str
    conversation_type: str
    other_person: str
    relationship_to_user: str


# ── Crisis Mode ───────────────────────────────────────────────────────────────

class CrisisCheckRequest(BaseModel):
    user_id: str = "default"
    message: str
    energy: float | None = None


class CrisisCheckResponse(BaseModel):
    severity: str
    response: str | None = None
    professional_support_recommended: bool = False
    one_action: str | None = None
    follow_up_tomorrow: bool = False


# ── Monthly Report ────────────────────────────────────────────────────────────

class MonthlyReportResponse(BaseModel):
    user_id: str
    month: str
    report_text: str
    data: dict[str, Any]
    generated_at: str


# ── HealthKit ─────────────────────────────────────────────────────────────────

class HealthDataRequest(BaseModel):
    user_id: str = "default"
    data_date: str | None = None
    sleep_hours: float | None = None
    sleep_quality_score: float | None = None
    hrv_ms: float | None = None
    resting_hr: float | None = None
    steps: int | None = None
    active_calories: int | None = None
    mindful_minutes: int | None = None


class HealthDataResponse(BaseModel):
    data_date: str
    coaching_note: str
    stored: bool


class HealthSummaryResponse(BaseModel):
    available: bool
    days_with_data: int | None = None
    avg_sleep_hours: float | None = None
    avg_hrv_ms: float | None = None
    avg_resting_hr: float | None = None
    avg_steps: int | None = None
    total_mindful_minutes: int | None = None
    low_sleep_days: int | None = None


# ── Achievements ──────────────────────────────────────────────────────────────

class AchievementOut(BaseModel):
    achievement_id: int
    title: str
    achievement_type: str
    achievement_date: str
    coach_message: str


# ── Calendar ──────────────────────────────────────────────────────────────────

class CalendarAttendee(BaseModel):
    name: str = ""
    email: str = ""


class CalendarEventIn(BaseModel):
    """Single event pushed from iOS during a sync."""
    external_event_id: str
    title: str
    start_datetime: str          # ISO: YYYY-MM-DDTHH:MM:SS
    end_datetime: str
    attendees: list[CalendarAttendee] = []
    location: str = ""
    description: str = ""
    is_all_day: bool = False


class CalendarSyncRequest(BaseModel):
    user_id: str = "default"
    provider: str = "apple"      # "apple" | "google"
    events: list[CalendarEventIn]


class CalendarSyncResponse(BaseModel):
    synced: int
    created: int
    updated: int
    provider: str


class CalendarEventSummary(BaseModel):
    id: int
    title: str
    start_time: str
    end_time: str
    event_type: str
    attendee_count: int
    location: str = ""


class TodayCalendarResponse(BaseModel):
    meeting_count: int
    high_stakes_count: int
    back_to_back_count: int = 0
    coach_note: str
    events: list[CalendarEventSummary]


class PreMeetingBriefResponse(BaseModel):
    event_id: int
    event_title: str
    start_datetime: str
    brief: str
    event_type: str


class PostMeetingPromptResponse(BaseModel):
    event_id: int
    event_title: str
    prompt: str


class PostMeetingNoteRequest(BaseModel):
    user_id: str = "default"
    note: str


class PostMeetingNoteResponse(BaseModel):
    event_id: int
    event_title: str
    coach_synthesis: str


class DailyMeetingBreakdown(BaseModel):
    date: str
    meeting_count: int
    total_meeting_minutes: int
    back_to_back_pairs: int
    energy: float | None = None


class MeetingDensityResponse(BaseModel):
    available: bool
    days_analysed: int
    days_with_meetings: int = 0
    avg_meetings_per_day: float = 0.0
    total_back_to_back_incidents: int = 0
    heavy_days_count: int = 0
    avg_energy_on_heavy_days: float | None = None
    avg_energy_on_light_days: float | None = None
    coach_analysis: str = ""
    daily_breakdown: list[DailyMeetingBreakdown] = []
    message: str = ""


class CalendarSettingsRequest(BaseModel):
    user_id: str = "default"
    enabled: bool
    provider: str = ""           # "apple" | "google" | ""


class CalendarSettingsResponse(BaseModel):
    calendar_integration_enabled: bool
    calendar_provider: str
    message: str


# ── Commitment Tracker ────────────────────────────────────────────────────────

class CommitmentCreateRequest(BaseModel):
    user_id: str = "default"
    commitment_text: str
    due_date: str              # YYYY-MM-DD
    source: str = "direct"
    source_id: int | None = None
    parent_goal_id: int | None = None
    parent_milestone_id: int | None = None


class CommitmentCreateResponse(BaseModel):
    commitment_id: int
    commitment_text: str
    due_date: str
    status: str
    source: str
    coach_acknowledgement: str


class CommitmentCheckInRequest(BaseModel):
    user_id: str = "default"
    status: str                # kept / missed / partial / deferred
    user_note: str = ""
    deferred_to: str = ""      # YYYY-MM-DD


class CommitmentCheckInResponse(BaseModel):
    commitment_id: int
    commitment_text: str
    status: str
    coach_response: str
    pattern_note: str | None = None


class CommitmentItem(BaseModel):
    id: int
    commitment_text: str
    due_date: str
    source: str
    days_overdue: int = 0
    parent_goal_id: int | None = None
    parent_milestone_id: int | None = None


class OpenCommitmentsResponse(BaseModel):
    overdue: list[CommitmentItem]
    due_today: list[CommitmentItem]
    upcoming_7_days: list[CommitmentItem]
    total_open: int
    coach_accountability_note: str


class CommitmentHistoryItem(BaseModel):
    id: int
    commitment_text: str
    due_date: str
    status: str
    source: str
    user_completion_note: str
    coach_followup_message: str


class CommitmentHistoryResponse(BaseModel):
    total: int
    open: int
    kept: int
    missed: int
    deferred: int
    completion_rate_pct: float
    pattern_note: str | None = None
    commitments: list[CommitmentHistoryItem]


# ── Energy Patterns ───────────────────────────────────────────────────────────

class DayOfWeekEnergy(BaseModel):
    available: bool
    by_day: dict[str, float] = {}
    peak_day: str = ""
    peak_avg_energy: float = 0.0
    trough_day: str = ""
    trough_avg_energy: float = 0.0
    gap: float = 0.0
    coach_note: str = ""


class EnergyStability(BaseModel):
    available: bool
    avg_energy: float = 0.0
    avg_daily_swing: float = 0.0
    stability_score: int = 0
    stability_label: str = ""
    coach_note: str = ""


class EnergyRecovery(BaseModel):
    available: bool
    low_energy_events: int = 0
    avg_recovery_days: float = 0.0
    coach_note: str = ""
    note: str = ""


class HabitCorrelation(BaseModel):
    habit_id: int
    habit_name: str
    avg_energy_after_completion: float
    avg_energy_after_miss: float
    energy_impact: float
    coach_note: str | None = None


class SleepEnergyCorrelation(BaseModel):
    available: bool
    sample_pairs: int = 0
    energy_by_sleep_duration: dict[str, float] = {}
    optimal_sleep_window: str = ""
    coach_note: str = ""


class EnergyTrend(BaseModel):
    available: bool
    direction: str = ""
    estimated_30_day_change: float = 0.0
    current_avg: float = 0.0
    coach_note: str = ""


class EnergyPatternResponse(BaseModel):
    available: bool
    check_in_count: int = 0
    days_analysed: int = 0
    minimum_required: int = 14
    message: str = ""
    coach_insight: str = ""
    day_of_week: DayOfWeekEnergy | None = None
    stability: EnergyStability | None = None
    recovery: EnergyRecovery | None = None
    habit_correlations: list[HabitCorrelation] = []
    sleep_energy_correlation: SleepEnergyCorrelation | None = None
    trend: EnergyTrend | None = None


class PeakPerformanceWindowResponse(BaseModel):
    available: bool
    peak_day: str = ""
    peak_avg_energy: float | None = None
    trough_day: str = ""
    top_energy_habit: str | None = None
    trend_direction: str = ""
    one_line_summary: str = ""


# ── Recalibration ─────────────────────────────────────────────────────────────

class RecalibrationQuestion(BaseModel):
    id: str
    question: str


class RecalibrationDueResponse(BaseModel):
    due: bool
    milestone_days: int | None = None
    days_since_onboarding: int | None = None
    questions: list[RecalibrationQuestion] = []
    coach_intro: str = ""


class RecalibrationAnswerRequest(BaseModel):
    user_id: str = "default"
    milestone_days: int
    question_id: str
    answer: str


class RecalibrationAnswerResponse(BaseModel):
    complete: bool
    question_id: str = ""
    question: str = ""
    answered: int = 0
    total: int = 0
    coach_synthesis: str = ""
    profile_updated: bool = False
    profile_changes_summary: list[str] = []


# ── Quarterly Retrospective ───────────────────────────────────────────────────

class RetrospectiveSections(BaseModel):
    numbers: str
    story: str
    wins: str
    lessons: str
    bridge: str


class RetrospectiveStats(BaseModel):
    check_in_count: int
    habit_count: int
    decision_count: int
    commitment_count: int
    reflection_count: int
    achievement_count: int


class QuarterlyRetrospectiveResponse(BaseModel):
    user_id: str
    full_name: str
    period_start: str
    period_end: str
    period_label: str
    full_retrospective: str
    sections: RetrospectiveSections
    stats: RetrospectiveStats


# ── First Read ────────────────────────────────────────────────────────────────

class FirstReadResponse(BaseModel):
    full_text: str
    opening_observation: str = ""
    undervalued_strength: str = ""
    blind_spot: str = ""
    relationship_pattern: str = ""
    one_sentence: str = ""
    coach_intention: str = ""
    model_used: str = ""
    delivered: bool = False
    cached: bool = False


class FirstReadDeliveredResponse(BaseModel):
    marked_delivered: bool


# ── Trial Closing Report ──────────────────────────────────────────────────────

class TrialClosingSections(BaseModel):
    opening: str
    data: str
    insight: str
    gap: str
    offer: str


class TrialClosingStats(BaseModel):
    trial_days: int
    check_in_count: int
    habit_count: int
    habit_completion_rate: int
    best_habit: str | None = None
    commitments_made: int
    commitments_kept_rate: int
    avg_energy: float
    energy_direction: str


class TrialClosingReportResponse(BaseModel):
    full_text: str
    sections: TrialClosingSections | None = None
    stats: TrialClosingStats | None = None
    trial_day_count: int = 7
    check_in_count: int = 0
    avg_energy: float = 0.0
    cached: bool = False


# ── Memory Context ────────────────────────────────────────────────────────────

class MemoryContextResponse(BaseModel):
    memory_context: str
    character_count: int


class MemoryContextSummaryResponse(BaseModel):
    user_name: str
    days_since_onboarding: int
    profile_version: int
    recent_checkins_14d: int
    open_commitments: int
    active_habits: int
    has_first_read: bool
    milestones_completed: list[int]
    memory_richness: str
