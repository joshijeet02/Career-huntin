import Foundation

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published private(set) var brief: [DailyBriefItem] = []
    @Published private(set) var executiveScore: Int = 0
    @Published private(set) var relationshipScore: Int = 0
    @Published private(set) var burnoutRisk: String = "Moderate"
    @Published private(set) var burnoutIntervention: String = ""

    @Published private(set) var calendarConnected = false
    @Published private(set) var isSyncingCalendar = false
    @Published private(set) var calendarEvents: [CalendarEventSummary] = []
    @Published private(set) var scheduleInsights: DailyScheduleInsights = .empty
    @Published private(set) var scheduleProtection = "Connect calendar to get schedule protection recommendations."

    @Published private(set) var strategicTimeline: [HorizonGoal] = []
    @Published private(set) var todayAdaptiveFocus = "Open Coach and complete one high-leverage action."

    private let profile: JayeshProfile
    private let habitEngine: HabitEngine
    private let burnoutEngine: BurnoutSentinel
    private let relationshipEngine: RelationshipEngine
    private let calendarService: CalendarService
    private let scheduleIntel: ScheduleIntelligence
    private let reminderEngine: ReminderEngine
    private let coachingSystem: CoachingSystemEngine

    var leaderName: String { profile.name }
    var leaderRoleOrganization: String { "\(profile.role) • \(profile.organization)" }

    init(
        profile: JayeshProfile,
        habitEngine: HabitEngine,
        burnoutEngine: BurnoutSentinel,
        relationshipEngine: RelationshipEngine,
        calendarService: CalendarService,
        scheduleIntel: ScheduleIntelligence,
        reminderEngine: ReminderEngine,
        coachingSystem: CoachingSystemEngine
    ) {
        self.profile = profile
        self.habitEngine = habitEngine
        self.burnoutEngine = burnoutEngine
        self.relationshipEngine = relationshipEngine
        self.calendarService = calendarService
        self.scheduleIntel = scheduleIntel
        self.reminderEngine = reminderEngine
        self.coachingSystem = coachingSystem
        refresh()
    }

    func refresh() {
        habitEngine.resetWeeklyIfNeeded()
        executiveScore = habitEngine.weeklyScore(track: .executive)
        relationshipScore = relationshipEngine.weeklyHealthScore()
        burnoutRisk = burnoutEngine.riskBand()
        burnoutIntervention = burnoutEngine.intervention()

        strategicTimeline = coachingSystem.timelineGoals()
        todayAdaptiveFocus = coachingSystem.currentPlan()?.primaryAction ?? todayAdaptiveFocus

        brief = [
            DailyBriefItem(title: "Mission Priority", detail: profile.missionPriorities.first ?? "Community outcomes"),
            DailyBriefItem(title: "Leadership Habit", detail: habitEngine.profileAwareTip()),
            DailyBriefItem(title: "Relationship Action", detail: relationshipEngine.appreciationPrompt()),
            DailyBriefItem(title: "Energy Protocol", detail: burnoutIntervention),
            DailyBriefItem(title: "Schedule Protection", detail: scheduleProtection),
            DailyBriefItem(title: "Adaptive Focus", detail: todayAdaptiveFocus)
        ]
    }

    func logEnergy(energy: Int, stress: Int, sleepHours: Double) {
        burnoutEngine.log(EnergyCheckin(date: .now, energy: energy, stress: stress, sleepHours: sleepHours))
        refresh()
    }

    func onAppBecameActive() {
        Task { @MainActor in
            await reminderEngine.requestPermission()
            let nudges = coachingSystem.onAppActive(schedule: scheduleInsights, burnoutRisk: burnoutRisk)
            reminderEngine.scheduleThreeDailyNudges(messages: nudges)
            refresh()
        }
    }

    func connectAndSyncCalendar() async {
        isSyncingCalendar = true
        defer { isSyncingCalendar = false }

        let granted = await calendarService.requestAccess()
        calendarConnected = granted
        guard granted else {
            scheduleProtection = "Calendar access denied. Enable calendar permission in iPhone settings."
            refresh()
            return
        }
        await reminderEngine.requestPermission()
        syncCalendar()
    }

    func syncCalendar() {
        calendarEvents = calendarService.eventsForToday()
        scheduleInsights = scheduleIntel.analyze(events: calendarEvents)
        scheduleProtection = scheduleIntel.protectionSuggestion(for: scheduleInsights)
        let nudges = coachingSystem.onAppActive(schedule: scheduleInsights, burnoutRisk: burnoutRisk)
        reminderEngine.scheduleThreeDailyNudges(messages: nudges)
        refresh()
    }
}
