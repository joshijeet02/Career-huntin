import Foundation

enum CoachingTrack: String, Codable, CaseIterable, Identifiable {
    case executive
    case relationship

    var id: String { rawValue }
}

struct DailyHabit: Codable, Identifiable, Hashable {
    let id: UUID
    let title: String
    let prompt: String
    let track: CoachingTrack
    let targetPerWeek: Int
    var completions: Int

    init(id: UUID = UUID(), title: String, prompt: String, track: CoachingTrack, targetPerWeek: Int, completions: Int = 0) {
        self.id = id
        self.title = title
        self.prompt = prompt
        self.track = track
        self.targetPerWeek = targetPerWeek
        self.completions = completions
    }
}

struct DailyBriefItem: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let detail: String
}

struct EnergyCheckin: Codable {
    let date: Date
    let energy: Int
    let stress: Int
    let sleepHours: Double
}

struct DecisionCanvas: Codable, Identifiable {
    let id: UUID
    var topic: String
    var desiredImpact: String
    var options: [String]
    var assumptions: [String]
    var risks: [String]
    var decision: String
    var dueDate: Date

    init(id: UUID = UUID(), topic: String = "", desiredImpact: String = "", options: [String] = [], assumptions: [String] = [], risks: [String] = [], decision: String = "", dueDate: Date = .now) {
        self.id = id
        self.topic = topic
        self.desiredImpact = desiredImpact
        self.options = options
        self.assumptions = assumptions
        self.risks = risks
        self.decision = decision
        self.dueDate = dueDate
    }
}

struct RelationshipCheckin: Codable, Identifiable {
    let id: UUID
    let date: Date
    let gratitude: String
    let unresolvedTopic: String
    let repairPhrase: String

    init(id: UUID = UUID(), date: Date = .now, gratitude: String, unresolvedTopic: String, repairPhrase: String) {
        self.id = id
        self.date = date
        self.gratitude = gratitude
        self.unresolvedTopic = unresolvedTopic
        self.repairPhrase = repairPhrase
    }
}

struct WeeklyReflection: Codable, Identifiable {
    let id: UUID
    let date: Date
    let leadershipWin: String
    let relationshipWin: String
    let topLesson: String
    let oneCommitment: String

    init(id: UUID = UUID(), date: Date = .now, leadershipWin: String, relationshipWin: String, topLesson: String, oneCommitment: String) {
        self.id = id
        self.date = date
        self.leadershipWin = leadershipWin
        self.relationshipWin = relationshipWin
        self.topLesson = topLesson
        self.oneCommitment = oneCommitment
    }
}
