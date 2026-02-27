import Foundation

@MainActor
final class CopilotViewModel: ObservableObject {
    @Published var endpoint: String = ""
    @Published var token: String = ""
    @Published private(set) var brief = CopilotBrief(
        headline: "No briefing generated yet",
        priorities: [],
        relationshipNudge: "",
        scheduleProtection: "",
        riskAlert: ""
    )
    @Published private(set) var isLoading = false

    private let engine: CopilotEngine
    private let dashboardVM: DashboardViewModel

    init(engine: CopilotEngine, dashboardVM: DashboardViewModel) {
        self.engine = engine
        self.dashboardVM = dashboardVM
    }

    func saveConfig() {
        guard !endpoint.isEmpty, !token.isEmpty else { return }
        engine.configure(endpoint: endpoint, token: token)
    }

    func generateBrief() async {
        isLoading = true
        defer { isLoading = false }

        brief = await engine.generateBrief(
            schedule: dashboardVM.scheduleInsights,
            executiveScore: dashboardVM.executiveScore,
            relationshipScore: dashboardVM.relationshipScore,
            burnoutRisk: dashboardVM.burnoutRisk
        )
    }
}
