import Foundation

final class DecisionEngine {
    private let profile: JayeshProfile
    private let store: LocalStore
    private let file = "decisions.json"

    private(set) var decisions: [DecisionCanvas]

    init(profile: JayeshProfile, store: LocalStore) {
        self.profile = profile
        self.store = store
        self.decisions = store.load([DecisionCanvas].self, from: file) ?? []
    }

    func save(_ canvas: DecisionCanvas) {
        if let idx = decisions.firstIndex(where: { $0.id == canvas.id }) {
            decisions[idx] = canvas
        } else {
            decisions.insert(canvas, at: 0)
        }
        persist()
    }

    func createTemplate(topic: String) -> DecisionCanvas {
        DecisionCanvas(
            topic: topic,
            desiredImpact: "Advance mission outcomes for \(profile.organization)",
            options: ["Option A", "Option B", "Option C"],
            assumptions: ["Which assumption must be true?"],
            risks: ["If this fails, what is harmed most?"],
            decision: "",
            dueDate: Calendar.current.date(byAdding: .day, value: 7, to: .now) ?? .now
        )
    }

    func qualityScore(for canvas: DecisionCanvas) -> Int {
        var score = 0
        if !canvas.topic.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { score += 15 }
        if !canvas.desiredImpact.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { score += 20 }
        if canvas.options.count >= 3 { score += 20 }
        if canvas.assumptions.count >= 2 { score += 15 }
        if canvas.risks.count >= 2 { score += 15 }
        if !canvas.decision.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { score += 15 }
        return min(score, 100)
    }

    func preMortemPrompts() -> [String] {
        [
            "Imagine this decision failed in 12 months. What caused it?",
            "What field-level signal will warn us early?",
            "What stakeholder perspective is still missing?",
            "What is the smallest reversible experiment this week?"
        ]
    }

    private func persist() {
        store.save(decisions, to: file)
    }
}
