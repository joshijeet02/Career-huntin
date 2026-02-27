import Foundation

final class CopilotEngine {
    private let profile: JayeshProfile
    private let orchestrator: AIOrchestrator
    private let keychain: KeychainStore
    private let serviceName = "JayeshCoach"

    private var apiToken: String? {
        keychain.load(service: serviceName, account: "api_token")
    }

    private var endpoint: String? {
        UserDefaults.standard.string(forKey: "coach_endpoint")
    }

    init(profile: JayeshProfile, orchestrator: AIOrchestrator = AIOrchestrator(), keychain: KeychainStore) {
        self.profile = profile
        self.orchestrator = orchestrator
        self.keychain = keychain
    }

    func configure(endpoint: String, token: String) {
        UserDefaults.standard.set(endpoint, forKey: "coach_endpoint")
        keychain.save(value: token, service: serviceName, account: "api_token")
    }

    func hasRemoteConfig() -> Bool {
        guard let endpoint, let token = apiToken else { return false }
        return !endpoint.isEmpty && !token.isEmpty
    }

    func generateBrief(
        schedule: DailyScheduleInsights,
        executiveScore: Int,
        relationshipScore: Int,
        burnoutRisk: String
    ) async -> CopilotBrief {
        let fallback = localBrief(
            schedule: schedule,
            executiveScore: executiveScore,
            relationshipScore: relationshipScore,
            burnoutRisk: burnoutRisk
        )

        guard hasRemoteConfig(), let endpoint else {
            return fallback
        }

        let context = "CEO=\(profile.name), Org=\(profile.organization), footprint=\(profile.operatingFootprint), scale=\(profile.communityScale), meetingCount=\(schedule.meetingCount), meetingHours=\(String(format: "%.1f", schedule.totalMeetingHours)), loadScore=\(schedule.loadScore), execScore=\(executiveScore), relScore=\(relationshipScore), burnoutRisk=\(burnoutRisk)"
        let request = CoachRequest(
            context: context,
            goal: "Produce concise daily coaching actions for leadership and relationship quality.",
            track: .executive
        )

        do {
            let remote = try await orchestrator.coach(request: request, endpoint: endpoint, token: apiToken ?? "")
            let first = remote.suggestedActions.first ?? fallback.scheduleProtection
            return CopilotBrief(
                headline: remote.message,
                priorities: Array(remote.suggestedActions.prefix(3)),
                relationshipNudge: relationshipNudge(score: relationshipScore),
                scheduleProtection: first,
                riskAlert: riskAlert(burnoutRisk: burnoutRisk, schedule: schedule)
            )
        } catch {
            return fallback
        }
    }

    private func localBrief(
        schedule: DailyScheduleInsights,
        executiveScore: Int,
        relationshipScore: Int,
        burnoutRisk: String
    ) -> CopilotBrief {
        let topPriority = executiveScore < 70
            ? "Run one 20-minute strategic review: mission outcomes, bottleneck, owner, deadline."
            : "Protect execution quality: remove one blocker for your leadership team today."

        let stakeholderPriority = schedule.loadScore > 70
            ? "Convert one low-value meeting into an async update to recover focus time."
            : "Use your biggest free block for donor or ecosystem partnership follow-through."

        let relationshipPriority = relationshipScore < 65
            ? "Do a 10-minute repair-oriented check-in: appreciation + one unresolved issue."
            : "Maintain connection with one specific appreciation before day-end."

        return CopilotBrief(
            headline: "Today's coaching brief for \(profile.name)",
            priorities: [topPriority, stakeholderPriority, relationshipPriority],
            relationshipNudge: relationshipNudge(score: relationshipScore),
            scheduleProtection: schedule.loadScore > 75
                ? "Calendar overload detected. Add one no-meeting focus block and decline one low-leverage slot."
                : "Schedule load is manageable. Guard a 60-minute strategy block before evening.",
            riskAlert: riskAlert(burnoutRisk: burnoutRisk, schedule: schedule)
        )
    }

    private func relationshipNudge(score: Int) -> String {
        if score < 60 {
            return "Lead with a soft startup in difficult conversations: 'I feel... I need... I value us.'"
        }
        return "Reinforce trust with specific appreciation and one attentive 10-minute conversation."
    }

    private func riskAlert(burnoutRisk: String, schedule: DailyScheduleInsights) -> String {
        if burnoutRisk == "High" || schedule.loadScore > 80 {
            return "High strain risk. Reduce meeting load and delegate one decision by noon."
        }
        return "Risk is controlled. Keep sleep and recovery protected tonight."
    }
}
