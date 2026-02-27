import Foundation

enum CoachRole: String, Codable {
    case user
    case coach
}

enum CoachIntent: String, Codable {
    case leadership
    case relationship
    case wellbeing
    case strategy
    case general
}

struct CoachMessage: Codable, Identifiable {
    let id: UUID
    let date: Date
    let role: CoachRole
    let intent: CoachIntent
    let text: String

    init(id: UUID = UUID(), date: Date = .now, role: CoachRole, intent: CoachIntent, text: String) {
        self.id = id
        self.date = date
        self.role = role
        self.intent = intent
        self.text = text
    }
}

struct CoachMemoryProfile: Codable {
    var languagePreference: String
    var recurringThemes: [String: Int]
    var dominantIntentCounts: [String: Int]
    var lastUpdated: Date

    static let initial = CoachMemoryProfile(
        languagePreference: "en-hi",
        recurringThemes: [:],
        dominantIntentCounts: [:],
        lastUpdated: .now
    )
}

enum CoachVoice: String, CaseIterable, Identifiable {
    case male = "Male"
    case female = "Female"

    var id: String { rawValue }
}
