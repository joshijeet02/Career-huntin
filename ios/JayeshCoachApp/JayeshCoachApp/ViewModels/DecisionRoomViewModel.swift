import Foundation

final class DecisionRoomViewModel: ObservableObject {
    @Published var activeCanvas = DecisionCanvas()
    @Published private(set) var qualityScore: Int = 0
    @Published private(set) var prompts: [String] = []
    @Published private(set) var recentDecisions: [DecisionCanvas] = []

    private let engine: DecisionEngine

    init(engine: DecisionEngine) {
        self.engine = engine
        self.prompts = engine.preMortemPrompts()
        self.recentDecisions = engine.decisions
        recalculate()
    }

    func seedTemplate(for topic: String) {
        activeCanvas = engine.createTemplate(topic: topic)
        recalculate()
    }

    func save() {
        engine.save(activeCanvas)
        recentDecisions = engine.decisions
        recalculate()
    }

    func recalculate() {
        qualityScore = engine.qualityScore(for: activeCanvas)
    }
}
