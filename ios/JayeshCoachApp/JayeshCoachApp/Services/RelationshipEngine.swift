import Foundation

final class RelationshipEngine {
    private let profile: JayeshProfile
    private let store: LocalStore
    private let file = "relationship_checkins.json"

    private(set) var checkins: [RelationshipCheckin]

    init(profile: JayeshProfile, store: LocalStore) {
        self.profile = profile
        self.store = store
        self.checkins = store.load([RelationshipCheckin].self, from: file) ?? []
    }

    func save(_ checkin: RelationshipCheckin) {
        checkins.insert(checkin, at: 0)
        persist()
    }

    func weeklyHealthScore() -> Int {
        let last7 = checkins.filter { $0.date >= Calendar.current.date(byAdding: .day, value: -7, to: .now) ?? .distantPast }
        guard !last7.isEmpty else { return 50 }
        let gratitudePoints = min(last7.filter { !$0.gratitude.isEmpty }.count * 10, 40)
        let repairPoints = min(last7.filter { !$0.repairPhrase.isEmpty }.count * 10, 40)
        let unresolvedPenalty = last7.filter { !$0.unresolvedTopic.isEmpty }.count * 5
        return max(0, min(100, gratitudePoints + repairPoints + 20 - unresolvedPenalty))
    }

    func prepConversationPrompt(topic: String) -> [String] {
        [
            "Intent: What do I want to protect in this relationship while discussing \(topic)?",
            "Trigger map: Which words or tone may escalate this?",
            "Soft start: Start with 'I feel... I need... I value us.'",
            "Repair line: 'I want us on the same side. Can we restart this calmly?'"
        ]
    }

    func appreciationPrompt() -> String {
        let value = profile.relationshipValues.randomElement() ?? "respect"
        return "Name one specific moment today where they showed \(value.lowercased())."
    }

    private func persist() {
        store.save(checkins, to: file)
    }
}
