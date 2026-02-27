import Foundation

final class ReflectionViewModel: ObservableObject {
    @Published var leadershipWin: String = ""
    @Published var relationshipWin: String = ""
    @Published var topLesson: String = ""
    @Published var oneCommitment: String = ""
    @Published private(set) var history: [WeeklyReflection] = []

    private let store: LocalStore
    private let file = "reflections.json"
    private let profile: JayeshProfile

    init(store: LocalStore, profile: JayeshProfile) {
        self.store = store
        self.profile = profile
        self.history = store.load([WeeklyReflection].self, from: file) ?? []
    }

    func save() {
        let reflection = WeeklyReflection(
            leadershipWin: leadershipWin,
            relationshipWin: relationshipWin,
            topLesson: topLesson,
            oneCommitment: oneCommitment
        )
        history.insert(reflection, at: 0)
        store.save(history, to: file)

        leadershipWin = ""
        relationshipWin = ""
        topLesson = ""
        oneCommitment = ""
    }

    func missionPrompt() -> String {
        let priority = profile.missionPriorities.first ?? "community impact"
        return "Which leadership action most advanced \(priority.lowercased()) this week?"
    }
}
