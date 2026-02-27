import Foundation

@MainActor
final class CoachConsoleViewModel: ObservableObject {
    @Published var draftText: String = ""
    @Published private(set) var messages: [CoachMessage] = []
    @Published private(set) var isListening = false
    @Published private(set) var isBusy = false
    @Published var selectedVoice: CoachVoice = .male
    @Published private(set) var speechReady = false

    @Published private(set) var timelineGoals: [HorizonGoal] = []
    @Published private(set) var adaptivePlan: DailyAdaptivePlan?
    @Published private(set) var pendingDiscoveryQuestion: String?
    @Published private(set) var researchBriefs: [ResearchBriefItem] = []

    @Published var backendEndpoint: String = ""
    @Published var backendAPIKey: String = ""

    private let coachEngine: UnifiedCoachEngine
    private let coachingSystem: CoachingSystemEngine
    private let dashboardVM: DashboardViewModel
    private let speechService: SpeechCoachService
    private let conversationClient: CoachConversationClient
    private let userID = "jayesh"
    private let sessionID: String

    init(
        coachEngine: UnifiedCoachEngine,
        coachingSystem: CoachingSystemEngine,
        dashboardVM: DashboardViewModel,
        speechService: SpeechCoachService,
        conversationClient: CoachConversationClient
    ) {
        self.coachEngine = coachEngine
        self.coachingSystem = coachingSystem
        self.dashboardVM = dashboardVM
        self.speechService = speechService
        self.conversationClient = conversationClient

        let storedSession = UserDefaults.standard.string(forKey: "coach_session_id")
        if let storedSession {
            self.sessionID = storedSession
        } else {
            let newID = UUID().uuidString
            UserDefaults.standard.set(newID, forKey: "coach_session_id")
            self.sessionID = newID
        }

        let config = conversationClient.loadConfig()
        self.backendEndpoint = config.endpoint
        self.backendAPIKey = config.apiKey

        self.messages = coachEngine.history()
        self.timelineGoals = coachingSystem.timelineGoals()
        self.adaptivePlan = coachingSystem.currentPlan()
        self.pendingDiscoveryQuestion = coachingSystem.pendingDiscoveryQuestion()

        if messages.isEmpty {
            messages = [
                CoachMessage(
                    role: .coach,
                    intent: .general,
                    text: "I am your personal coach. We will build your 1-month, 3-month, 6-month, and 1-year growth system together. Talk in English or Hindi, and I will adapt to your mood and your schedule."
                )
            ]
        }
    }

    func saveBackendConfig() {
        let endpoint = backendEndpoint.trimmingCharacters(in: .whitespacesAndNewlines)
        let key = backendAPIKey.trimmingCharacters(in: .whitespacesAndNewlines)
        conversationClient.saveConfig(endpoint: endpoint, apiKey: key)
        Task { @MainActor in
            await refreshResearchBriefs()
        }
    }

    func sendMessage() {
        let text = draftText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        isBusy = true
        let userIntent = coachEngine.detectIntent(text)
        let userMessage = CoachMessage(role: .user, intent: userIntent, text: text)
        messages.append(userMessage)
        draftText = ""

        Task { @MainActor in
            let coachReply = await buildCoachReply(for: text, intent: userIntent)
            messages.append(coachReply)
            coachEngine.saveTurnPair(user: userMessage, coach: coachReply)
            isBusy = false
        }
    }

    func prepareSpeech() async {
        speechReady = await speechService.requestPermissions()
        await refreshResearchBriefs()
    }

    func toggleListening() {
        if isListening {
            speechService.stopListening()
            isListening = false
            return
        }

        do {
            try speechService.startListening { [weak self] text in
                Task { @MainActor in
                    self?.draftText = text
                }
            }
            isListening = true
        } catch {
            isListening = false
        }
    }

    func speakLastResponse() {
        guard let last = messages.last(where: { $0.role == .coach }) else { return }
        speechService.speak(last.text, voice: selectedVoice)
    }

    private func buildCoachReply(for text: String, intent: CoachIntent) async -> CoachMessage {
        let baseReply = coachEngine.respond(
            to: text,
            schedule: dashboardVM.scheduleInsights,
            burnoutRisk: dashboardVM.burnoutRisk
        )

        let guidance = coachingSystem.processTurn(
            userText: text,
            intent: intent,
            schedule: dashboardVM.scheduleInsights,
            burnoutRisk: dashboardVM.burnoutRisk
        )

        timelineGoals = guidance.timeline
        adaptivePlan = guidance.plan
        pendingDiscoveryQuestion = guidance.discoveryQuestion

        let context = [
            "scheduleLoad=\(dashboardVM.scheduleInsights.loadScore)",
            "meetingCount=\(dashboardVM.scheduleInsights.meetingCount)",
            "meetingHours=\(String(format: "%.1f", dashboardVM.scheduleInsights.totalMeetingHours))",
            "longestFreeBlockMinutes=\(dashboardVM.scheduleInsights.longestFreeBlockMinutes)",
            "calendarSummary=\(calendarSummaryString())",
            "memoryThemes=\(memoryThemesString())",
            "burnoutRisk=\(dashboardVM.burnoutRisk)",
            "horizonFocus=\(guidance.plan.horizonFocus.rawValue)",
            "mood=\(guidance.plan.moodBand.rawValue)"
        ].joined(separator: ", ")

        var coreMessage = baseReply.text
        var remoteActions: [String] = []
        if !backendEndpoint.isEmpty && !backendAPIKey.isEmpty {
            do {
                let remote = try await conversationClient.sendMessage(
                    userID: userID,
                    sessionID: sessionID,
                    message: text,
                    context: context,
                    intent: intent
                )
                coreMessage = remote.message
                remoteActions = Array(remote.suggestedActions.prefix(3))
            } catch {
                coreMessage = baseReply.text
            }
        }

        let composedText = composeCoachMessage(baseReply: coreMessage, remoteActions: remoteActions, guidance: guidance)
        return CoachMessage(role: .coach, intent: intent, text: composedText)
    }

    private func composeCoachMessage(baseReply: String, remoteActions: [String], guidance: GoalGuidanceResult) -> String {
        var lines = [baseReply]

        if !remoteActions.isEmpty {
            lines.append("")
            lines.append("AI actions:")
            for action in remoteActions {
                lines.append("- \(action)")
            }
        }

        lines.append("")
        lines.append("Immediate move: \(guidance.plan.primaryAction)")
        lines.append("Minimum if day is chaotic: \(guidance.plan.minimumAction)")
        lines.append("Pivot if mood drops: \(guidance.plan.pivotAction)")
        lines.append("Accountability tonight: \(guidance.plan.accountabilityPrompt)")

        if let question = guidance.discoveryQuestion {
            lines.append("")
            lines.append("Quick calibration question: \(question)")
        }

        return lines.joined(separator: "\n")
    }

    private func refreshResearchBriefs() async {
        guard !backendEndpoint.isEmpty, !backendAPIKey.isEmpty else {
            researchBriefs = []
            return
        }
        do {
            researchBriefs = try await conversationClient.fetchResearchBrief(limit: 5)
        } catch {
            researchBriefs = []
        }
    }

    private func calendarSummaryString() -> String {
        let events = dashboardVM.calendarEvents.prefix(5).map { event in
            let time = event.startDate.formatted(date: .omitted, time: .shortened)
            return "\(time)-\(event.title)"
        }
        if events.isEmpty {
            return "none"
        }
        return events.joined(separator: " | ")
    }

    private func memoryThemesString() -> String {
        let themes = coachEngine.recentMemoryThemes(limit: 5)
        if themes.isEmpty {
            return "none"
        }
        return themes.joined(separator: "|")
    }
}
