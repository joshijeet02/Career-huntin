import Foundation

enum GoalHorizon: String, Codable, CaseIterable, Identifiable {
    case month1
    case month3
    case month6
    case year1

    var id: String { rawValue }

    var title: String {
        switch self {
        case .month1: return "1 Month"
        case .month3: return "3 Months"
        case .month6: return "6 Months"
        case .year1: return "1 Year"
        }
    }

    var order: Int {
        switch self {
        case .month1: return 1
        case .month3: return 2
        case .month6: return 3
        case .year1: return 4
        }
    }
}

enum MoodBand: String, Codable {
    case fragile
    case low
    case steady
    case high
}

struct HorizonGoal: Codable, Identifiable, Hashable {
    let horizon: GoalHorizon
    var objective: String
    var measurableOutcomes: [String]
    var systemDesign: [String]
    var confidence: Int

    var id: String { horizon.rawValue }
}

struct GoalDiscoveryState: Codable {
    var pendingHorizons: [GoalHorizon]
    var currentQuestion: String?
    var questionHistory: [String]
    var answerHistory: [String]
}

struct DailyAdaptivePlan: Codable {
    let generatedAt: Date
    let horizonFocus: GoalHorizon
    let moodBand: MoodBand
    let primaryAction: String
    let minimumAction: String
    let pivotAction: String
    let accountabilityPrompt: String
}

struct CoachingOperatingState: Codable {
    var goalsByHorizon: [String: HorizonGoal]
    var discovery: GoalDiscoveryState
    var lastInteractionAt: Date?
    var lastAppOpenAt: Date?
    var latestPlan: DailyAdaptivePlan?

    static let empty = CoachingOperatingState(
        goalsByHorizon: [:],
        discovery: GoalDiscoveryState(
            pendingHorizons: GoalHorizon.allCases,
            currentQuestion: nil,
            questionHistory: [],
            answerHistory: []
        ),
        lastInteractionAt: nil,
        lastAppOpenAt: nil,
        latestPlan: nil
    )
}

struct GoalGuidanceResult {
    let timeline: [HorizonGoal]
    let plan: DailyAdaptivePlan
    let discoveryQuestion: String?
}
