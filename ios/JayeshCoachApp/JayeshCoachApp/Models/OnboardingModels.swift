import Foundation

enum OnboardingSpeaker {
    case coach
    case user
}

struct OnboardingTurn: Identifiable {
    let id = UUID()
    let speaker: OnboardingSpeaker
    let text: String
}

struct OnboardingQuestion: Identifiable {
    let id: String
    let prompt: String
    let placeholder: String
    let quickReplies: [String]
}

extension OnboardingQuestion {
    static let interviewFlow: [OnboardingQuestion] = [
        OnboardingQuestion(
            id: "name",
            prompt: "What should I call you while we work together?",
            placeholder: "Your name",
            quickReplies: []
        ),
        OnboardingQuestion(
            id: "role",
            prompt: "What is your current role?",
            placeholder: "e.g. CEO, Founder, VP Operations",
            quickReplies: ["CEO", "Founder", "Managing Director", "Senior Leader"]
        ),
        OnboardingQuestion(
            id: "organization",
            prompt: "What organization, company, or venture are you leading right now?",
            placeholder: "Organization name",
            quickReplies: []
        ),
        OnboardingQuestion(
            id: "footprint",
            prompt: "Where does your work operate today?",
            placeholder: "Geographies, communities, or markets",
            quickReplies: ["India-wide", "Global", "Regional", "Remote-first"]
        ),
        OnboardingQuestion(
            id: "scale",
            prompt: "How would you describe your current scale and responsibility?",
            placeholder: "Team size, stakeholder load, or mission scale",
            quickReplies: ["Early-stage team", "Scaling team", "Large stakeholder network"]
        ),
        OnboardingQuestion(
            id: "goals_12m",
            prompt: "List your top 3 outcomes for the next 12 months (comma-separated).",
            placeholder: "Outcome 1, Outcome 2, Outcome 3",
            quickReplies: []
        ),
        OnboardingQuestion(
            id: "strategic_focus",
            prompt: "What strategic themes must stay non-negotiable this year?",
            placeholder: "Decision quality, stakeholder trust, execution cadence",
            quickReplies: ["Execution rhythm", "Team leadership", "Fundraising/partnerships", "Personal sustainability"]
        ),
        OnboardingQuestion(
            id: "relationship_pattern",
            prompt: "When conflict appears in close relationships, what pattern do you want to improve?",
            placeholder: "e.g. reactive tone, delayed repair, poor listening",
            quickReplies: ["Better listening", "Faster repair", "Calmer tone", "Clear boundaries"]
        ),
        OnboardingQuestion(
            id: "languages",
            prompt: "Which languages should I use with you?",
            placeholder: "English, Hindi, etc.",
            quickReplies: ["English", "English + Hindi", "Hindi", "English + Gujarati"]
        ),
        OnboardingQuestion(
            id: "coach_tone",
            prompt: "What coaching style helps you perform best?",
            placeholder: "Direct, calm, challenging, reflective",
            quickReplies: ["Direct", "Calm", "Challenging", "Balanced"]
        )
    ]
}
