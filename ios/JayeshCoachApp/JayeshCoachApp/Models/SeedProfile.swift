import Foundation

struct CoachUserProfile: Codable, Hashable {
    let name: String
    let role: String
    let organization: String
    let operatingFootprint: String
    let communityScale: String
    let missionPriorities: [String]
    let preferredLanguage: [String]
    let strategicThemes: [String]
    let relationshipValues: [String]
    let coachTone: String
    let interviewCompletedAt: Date?
    let interviewAnswers: [String: String]
}

typealias JayeshProfile = CoachUserProfile

extension CoachUserProfile {
    static let seed = CoachUserProfile(
        name: "Mr. Jayesh Joshi",
        role: "CEO",
        organization: "VAAGDHARA",
        operatingFootprint: "Tribal tri-junction of Rajasthan, Gujarat, and Madhya Pradesh",
        communityScale: "130000+ tribal families across 1168 villages",
        missionPriorities: [
            "Tribal community empowerment",
            "Livelihood resilience",
            "Child rights and nutrition",
            "Local governance participation"
        ],
        preferredLanguage: ["English", "Hindi"],
        strategicThemes: [
            "Long-term ecosystem partnerships",
            "Community-first implementation",
            "Leadership pipeline and succession",
            "Sustainable organizational growth"
        ],
        relationshipValues: [
            "Respectful communication",
            "Repair after conflict",
            "Consistency under stress",
            "Daily appreciation"
        ],
        coachTone: "Direct and calm accountability",
        interviewCompletedAt: nil,
        interviewAnswers: [:]
    )

    static func fromInterview(_ answers: [String: String]) -> CoachUserProfile {
        let name = value(for: "name", in: answers, fallback: "Leader")
        let role = value(for: "role", in: answers, fallback: "Executive")
        let organization = value(for: "organization", in: answers, fallback: "Mission-Driven Organization")
        let footprint = value(
            for: "footprint",
            in: answers,
            fallback: "Distributed teams and stakeholders across multiple contexts"
        )
        let scale = value(for: "scale", in: answers, fallback: "Multi-stakeholder high-accountability environment")
        let mission = list(
            for: "goals_12m",
            in: answers,
            fallback: [
                "Improve leadership clarity",
                "Strengthen execution consistency",
                "Increase strategic impact"
            ]
        )
        let languages = list(for: "languages", in: answers, fallback: ["English"])
        let strategicThemes = list(
            for: "strategic_focus",
            in: answers,
            fallback: [
                "Decision quality under pressure",
                "Focused calendar protection",
                "Stakeholder trust"
            ]
        )
        let relationshipValues = list(
            for: "relationship_pattern",
            in: answers,
            fallback: [
                "Repair quickly after conflict",
                "Listen before reacting",
                "Speak with clarity under pressure"
            ]
        )
        let tone = value(for: "coach_tone", in: answers, fallback: "Direct and practical")

        return CoachUserProfile(
            name: name,
            role: role,
            organization: organization,
            operatingFootprint: footprint,
            communityScale: scale,
            missionPriorities: mission,
            preferredLanguage: languages,
            strategicThemes: strategicThemes,
            relationshipValues: relationshipValues,
            coachTone: tone,
            interviewCompletedAt: .now,
            interviewAnswers: answers
        )
    }

    var interviewCompleted: Bool {
        interviewCompletedAt != nil
    }

    private static func value(for key: String, in answers: [String: String], fallback: String) -> String {
        let text = answers[key]?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return text.isEmpty ? fallback : text
    }

    private static func list(for key: String, in answers: [String: String], fallback: [String]) -> [String] {
        let raw = answers[key]?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if raw.isEmpty {
            return fallback
        }
        let delimiters = CharacterSet(charactersIn: ",;|")
        let components = raw
            .components(separatedBy: delimiters)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        return components.isEmpty ? fallback : Array(components.prefix(6))
    }
}

enum CoachProfileRepository {
    private static let profileFile = "coach_user_profile.json"

    static func load(store: LocalStore = LocalStore()) -> CoachUserProfile {
        store.load(CoachUserProfile.self, from: profileFile) ?? .seed
    }

    static func save(_ profile: CoachUserProfile, store: LocalStore = LocalStore()) {
        store.save(profile, to: profileFile)
    }

    static func needsOnboarding(store: LocalStore = LocalStore()) -> Bool {
        !load(store: store).interviewCompleted
    }
}
