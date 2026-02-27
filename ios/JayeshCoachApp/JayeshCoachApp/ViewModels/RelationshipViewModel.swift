import Foundation

final class RelationshipViewModel: ObservableObject {
    @Published var gratitude: String = ""
    @Published var unresolvedTopic: String = ""
    @Published var repairPhrase: String = ""
    @Published var prepTopic: String = ""

    @Published private(set) var prepPrompts: [String] = []
    @Published private(set) var checkins: [RelationshipCheckin] = []
    @Published private(set) var healthScore: Int = 50

    private let engine: RelationshipEngine

    init(engine: RelationshipEngine) {
        self.engine = engine
        self.checkins = engine.checkins
        self.healthScore = engine.weeklyHealthScore()
    }

    func generatePrep() {
        prepPrompts = engine.prepConversationPrompt(topic: prepTopic.isEmpty ? "a sensitive issue" : prepTopic)
    }

    func saveCheckin() {
        let item = RelationshipCheckin(gratitude: gratitude, unresolvedTopic: unresolvedTopic, repairPhrase: repairPhrase)
        engine.save(item)
        checkins = engine.checkins
        healthScore = engine.weeklyHealthScore()
        gratitude = ""
        unresolvedTopic = ""
        repairPhrase = ""
    }
}
