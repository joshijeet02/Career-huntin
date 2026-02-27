import Foundation

@MainActor
final class AppContainer: ObservableObject {
    let profile: JayeshProfile
    let store: LocalStore
    let keychain = KeychainStore()
    let speechService = SpeechCoachService()

    init(profile: JayeshProfile, store: LocalStore = LocalStore()) {
        self.profile = profile
        self.store = store
    }

    lazy var habitEngine = HabitEngine(profile: profile, store: store)
    lazy var decisionEngine = DecisionEngine(profile: profile, store: store)
    lazy var relationshipEngine = RelationshipEngine(profile: profile, store: store)
    lazy var burnoutEngine = BurnoutSentinel(store: store)
    lazy var calendarService = CalendarService()
    lazy var scheduleIntel = ScheduleIntelligence()
    lazy var reminderEngine = ReminderEngine()
    lazy var copilotEngine = CopilotEngine(profile: profile, keychain: keychain)
    lazy var coachConversationClient = CoachConversationClient(keychain: keychain)
    lazy var memoryEngine = EvolutionMemoryEngine(store: store)
    lazy var unifiedCoachEngine = UnifiedCoachEngine(profile: profile, memoryEngine: memoryEngine)
    lazy var coachingSystemEngine = CoachingSystemEngine(profile: profile, store: store)

    lazy var dashboardVM = DashboardViewModel(
        profile: profile,
        habitEngine: habitEngine,
        burnoutEngine: burnoutEngine,
        relationshipEngine: relationshipEngine,
        calendarService: calendarService,
        scheduleIntel: scheduleIntel,
        reminderEngine: reminderEngine,
        coachingSystem: coachingSystemEngine
    )

    lazy var decisionVM = DecisionRoomViewModel(engine: decisionEngine)
    lazy var relationshipVM = RelationshipViewModel(engine: relationshipEngine)
    lazy var habitsVM = HabitLabViewModel(engine: habitEngine)
    lazy var reflectionVM = ReflectionViewModel(store: store, profile: profile)
    lazy var copilotVM = CopilotViewModel(engine: copilotEngine, dashboardVM: dashboardVM)
    lazy var coachConsoleVM = CoachConsoleViewModel(
        coachEngine: unifiedCoachEngine,
        coachingSystem: coachingSystemEngine,
        dashboardVM: dashboardVM,
        speechService: speechService,
        conversationClient: coachConversationClient
    )
}
