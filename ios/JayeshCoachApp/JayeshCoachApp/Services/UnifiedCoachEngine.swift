import Foundation

final class UnifiedCoachEngine {
    private let profile: JayeshProfile
    private let memoryEngine: EvolutionMemoryEngine

    init(profile: JayeshProfile, memoryEngine: EvolutionMemoryEngine) {
        self.profile = profile
        self.memoryEngine = memoryEngine
    }

    func detectIntent(_ text: String) -> CoachIntent {
        let lowered = text.lowercased()
        if lowered.contains("argument") || lowered.contains("friend") || lowered.contains("wife") || lowered.contains("relationship") || lowered.contains("hurt") {
            return .relationship
        }
        if lowered.contains("stress") || lowered.contains("tired") || lowered.contains("burnout") || lowered.contains("upset") {
            return .wellbeing
        }
        if lowered.contains("decision") || lowered.contains("board") || lowered.contains("donor") || lowered.contains("team") {
            return .leadership
        }
        if lowered.contains("strategy") || lowered.contains("plan") || lowered.contains("priority") || lowered.contains("impact") {
            return .strategy
        }
        return .general
    }

    func respond(to userText: String, schedule: DailyScheduleInsights, burnoutRisk: String) -> CoachMessage {
        let intent = detectIntent(userText)
        let reply = buildReply(intent: intent, userText: userText, schedule: schedule, burnoutRisk: burnoutRisk)
        return CoachMessage(role: .coach, intent: intent, text: reply)
    }

    private func buildReply(intent: CoachIntent, userText: String, schedule: DailyScheduleInsights, burnoutRisk: String) -> String {
        let centering = "Breathe for 2 slow cycles, then return to disciplined focus."
        let reframe = "One calm, high-quality move now is better than emotional overreaction."
        switch intent {
        case .relationship:
            return structuredReply(
                center: centering,
                reframe: reframe,
                actions: [
                    "Send one repair line: 'I value this relationship and I want a calm reset.'",
                    "Write 3 bullets now: what I felt, what I needed, what I regret saying.",
                    "In the next talk: acknowledge, own your part, request reset."
                ],
                accountability: "What exact repair message will you send in the next 10 minutes?",
                evidence: "Repair attempts strengthen relationship resilience (Gottman research)."
            )
        case .wellbeing:
            return structuredReply(
                center: centering,
                reframe: "Your energy is a leadership asset, not a luxury.",
                actions: [
                    "Take a 10-minute reset walk and hydrate now.",
                    "Cancel or defer one low-leverage commitment today.",
                    "Because burnout risk is \(burnoutRisk.lowercased()), lock one recovery block before sleep."
                ],
                accountability: "Which meeting or task will you remove today to reduce overload?",
                evidence: "Burnout is a chronic stress risk that requires operational fixes (WHO ICD-11)."
            )
        case .leadership:
            return structuredReply(
                center: centering,
                reframe: "Leadership quality is decision quality multiplied by execution consistency.",
                actions: [
                    "Run a 20-minute decision reset: decision, 3 options, 3 risks.",
                    "Assign owner and deadline to the next critical action.",
                    "Schedule load is \(schedule.loadScore); keep only mission-linked meetings."
                ],
                accountability: "What one decision will you close before the next 2 hours?",
                evidence: "Behavior-focused executive coaching improves outcomes (meta-analysis 2023)."
            )
        case .strategy:
            return structuredReply(
                center: centering,
                reframe: "Strategy wins when priorities are few and execution ownership is clear.",
                actions: [
                    "Pick one mission metric, one bottleneck, and one owner for today.",
                    "Use your \(schedule.longestFreeBlockMinutes)-minute free block for strategic work only.",
                    "Send one crisp stakeholder update with ask + deadline."
                ],
                accountability: "Which single strategic outcome must move today, no matter what?",
                evidence: "High-pressure nonprofit contexts reward risk-aware strategic cadence (Urban 2025)."
            )
        case .general:
            return structuredReply(
                center: centering,
                reframe: reframe,
                actions: [
                    "Share this in 4 lines: what happened, what you felt, what you need, ideal outcome.",
                    "Name one action you can complete in 10 minutes.",
                    "If day is heavy, do only the minimum viable action and report back."
                ],
                accountability: "What is your next 10-minute action starting now?",
                evidence: "Stable cues and small consistent actions strengthen habit trajectories (2023-2024 habit research)."
            )
        }
    }

    func saveTurnPair(user: CoachMessage, coach: CoachMessage) {
        memoryEngine.append(user)
        memoryEngine.append(coach)
    }

    func history() -> [CoachMessage] {
        memoryEngine.messages
    }

    func memorySnapshot() -> CoachMemoryProfile {
        memoryEngine.memory
    }

    func recentMemoryThemes(limit: Int = 5) -> [String] {
        memoryEngine.recentThemes(limit: limit)
    }

    private func structuredReply(
        center: String,
        reframe: String,
        actions: [String],
        accountability: String,
        evidence: String
    ) -> String {
        var lines = [
            "Coach mode: \(profile.coachTone)",
            "Center: \(center)",
            "Reframe: \(reframe)",
            "Action path:"
        ]
        for action in actions.prefix(5) {
            lines.append("- \(action)")
        }
        lines.append("Accountability question: \(accountability)")
        lines.append("Evidence spotlight: \(evidence)")
        return lines.joined(separator: "\n")
    }
}
