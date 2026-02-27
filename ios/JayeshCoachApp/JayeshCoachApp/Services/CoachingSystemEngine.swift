import Foundation

final class CoachingSystemEngine {
    private let profile: JayeshProfile
    private let store: LocalStore
    private let file = "coaching_operating_state.json"

    private(set) var state: CoachingOperatingState

    init(profile: JayeshProfile, store: LocalStore) {
        self.profile = profile
        self.store = store
        self.state = store.load(CoachingOperatingState.self, from: file) ?? .empty
        bootstrapIfNeeded()
    }

    func timelineGoals() -> [HorizonGoal] {
        GoalHorizon.allCases
            .compactMap { state.goalsByHorizon[$0.rawValue] }
            .sorted { $0.horizon.order < $1.horizon.order }
    }

    func currentPlan() -> DailyAdaptivePlan? {
        state.latestPlan
    }

    func pendingDiscoveryQuestion() -> String? {
        state.discovery.currentQuestion
    }

    func processTurn(
        userText: String,
        intent: CoachIntent,
        schedule: DailyScheduleInsights,
        burnoutRisk: String
    ) -> GoalGuidanceResult {
        maybeCaptureDiscoveryAnswer(userText)
        let question = nextDiscoveryQuestion()
        applyPersonalizationSignals(from: userText, intent: intent)

        let mood = inferMood(userText: userText, burnoutRisk: burnoutRisk)
        let plan = buildAdaptivePlan(mood: mood, schedule: schedule)
        state.latestPlan = plan
        state.lastInteractionAt = .now
        persist()

        return GoalGuidanceResult(timeline: timelineGoals(), plan: plan, discoveryQuestion: question)
    }

    func onAppActive(schedule: DailyScheduleInsights, burnoutRisk: String) -> [String] {
        state.lastAppOpenAt = .now
        if state.latestPlan == nil {
            let plan = buildAdaptivePlan(mood: inferMood(userText: "", burnoutRisk: burnoutRisk), schedule: schedule)
            state.latestPlan = plan
        }
        persist()
        return nudgeMessages()
    }

    private func bootstrapIfNeeded() {
        if state.goalsByHorizon.isEmpty {
            state.goalsByHorizon = defaultGoals(profile: profile)
        }
        if state.discovery.pendingHorizons.isEmpty,
           state.discovery.questionHistory.isEmpty,
           state.discovery.answerHistory.isEmpty {
            state.discovery.pendingHorizons = GoalHorizon.allCases
        }
        persist()
    }

    private func defaultGoals(profile: JayeshProfile) -> [String: HorizonGoal] {
        let month1 = HorizonGoal(
            horizon: .month1,
            objective: "Create clarity and emotional steadiness under high workload.",
            measurableOutcomes: [
                "Protect 1 strategic focus block on at least 5 days per week",
                "Reduce reactive conflicts by using repair-first responses",
                "Close each day with top-3 priority review"
            ],
            systemDesign: [
                "Morning mission reset (10 min)",
                "Midday schedule triage",
                "Night reflection + relationship repair loop"
            ],
            confidence: 60
        )

        let month3 = HorizonGoal(
            horizon: .month3,
            objective: "Run a high-trust leadership cadence across team and stakeholders.",
            measurableOutcomes: [
                "Weekly decision quality review with owners and deadlines",
                "Delegation score improves to reduce CEO bottlenecks",
                "Relationship stability remains strong during pressure cycles"
            ],
            systemDesign: [
                "Weekly strategy review ritual",
                "Stakeholder feedforward loop",
                "Conflict-prep and repair scripts"
            ],
            confidence: 55
        )

        let month6 = HorizonGoal(
            horizon: .month6,
            objective: "Institutionalize scalable execution and personal sustainability.",
            measurableOutcomes: [
                "Leadership pipeline handles key decisions without overload",
                "Calendar load is intentionally shaped, not reactive",
                "Burnout high-risk windows drop materially"
            ],
            systemDesign: [
                "Decision operating system across team",
                "Sustainable work rhythm and recovery guardrails",
                "Quarterly relationship health review"
            ],
            confidence: 50
        )

        let year1 = HorizonGoal(
            horizon: .year1,
            objective: "Build a mission-multiplier leadership system for long-term \(profile.organization) community impact.",
            measurableOutcomes: [
                "Leadership culture runs with clarity and trust",
                "Mission priorities show consistent execution progress",
                "Personal relationships and health remain intact under scale"
            ],
            systemDesign: [
                "Annual strategy map tied to mission outcomes",
                "Leadership standards and coaching cadence",
                "Personal operating manual for high-pressure years"
            ],
            confidence: 45
        )

        return [
            GoalHorizon.month1.rawValue: month1,
            GoalHorizon.month3.rawValue: month3,
            GoalHorizon.month6.rawValue: month6,
            GoalHorizon.year1.rawValue: year1
        ]
    }

    private func maybeCaptureDiscoveryAnswer(_ userText: String) {
        guard let question = state.discovery.currentQuestion else { return }
        let words = userText.split(separator: " ").count
        guard words >= 5 else { return }

        if let completed = state.discovery.pendingHorizons.first {
            state.discovery.pendingHorizons.removeFirst()
            state.discovery.questionHistory.append(question)
            state.discovery.answerHistory.append(userText)
            refineGoal(for: completed, using: userText)
            state.discovery.currentQuestion = nil
        }
    }

    private func nextDiscoveryQuestion() -> String? {
        guard let horizon = state.discovery.pendingHorizons.first else {
            state.discovery.currentQuestion = nil
            return nil
        }
        let question: String
        switch horizon {
        case .month1:
            question = "For the next 30 days, what situation drains your energy most that we must stabilize first?"
        case .month3:
            question = "Over 3 months, where would stronger leadership rhythm create the biggest mission acceleration?"
        case .month6:
            question = "If we look 6 months ahead, which capability must your team own so you are not the bottleneck?"
        case .year1:
            question = "At 1 year, what should people say has changed in your leadership and relationships because of this system?"
        }
        state.discovery.currentQuestion = question
        return question
    }

    private func refineGoal(for horizon: GoalHorizon, using answer: String) {
        guard var goal = state.goalsByHorizon[horizon.rawValue] else { return }
        let distilled = answer
            .split(separator: " ")
            .prefix(18)
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !distilled.isEmpty else { return }

        let personalized = "Personalized focus: \(distilled)."
        if !goal.systemDesign.contains(personalized) {
            goal.systemDesign.append(personalized)
            goal.confidence = min(goal.confidence + 10, 95)
        }
        state.goalsByHorizon[horizon.rawValue] = goal
    }

    private func applyPersonalizationSignals(from text: String, intent: CoachIntent) {
        let lowered = text.lowercased()
        if lowered.contains("argument") || lowered.contains("friend") || lowered.contains("conflict") {
            addOutcome(horizon: .month1, outcome: "Use a repair-first script within 24 hours of personal conflict")
        }
        if lowered.contains("team") || lowered.contains("board") || lowered.contains("donor") {
            addOutcome(horizon: .month3, outcome: "Strengthen weekly stakeholder communication cadence with clear asks")
        }
        if intent == .wellbeing {
            addOutcome(horizon: .month6, outcome: "Maintain recovery windows during peak execution periods")
        }
    }

    private func addOutcome(horizon: GoalHorizon, outcome: String) {
        guard var goal = state.goalsByHorizon[horizon.rawValue] else { return }
        if !goal.measurableOutcomes.contains(outcome) {
            goal.measurableOutcomes.append(outcome)
            goal.confidence = min(goal.confidence + 5, 95)
            state.goalsByHorizon[horizon.rawValue] = goal
        }
    }

    private func inferMood(userText: String, burnoutRisk: String) -> MoodBand {
        let lowered = userText.lowercased()
        if lowered.contains("upset") || lowered.contains("angry") || lowered.contains("hurt") || burnoutRisk == "High" {
            return .fragile
        }
        if lowered.contains("tired") || lowered.contains("drained") || lowered.contains("stressed") {
            return .low
        }
        if lowered.contains("great") || lowered.contains("energized") || lowered.contains("excellent") {
            return .high
        }
        return .steady
    }

    private func buildAdaptivePlan(mood: MoodBand, schedule: DailyScheduleInsights) -> DailyAdaptivePlan {
        let focus = state.discovery.pendingHorizons.first ?? .month1
        let outcome = state.goalsByHorizon[focus.rawValue]?.measurableOutcomes.first ?? "Move one mission-critical priority forward"

        let primary: String
        let minimum: String
        let pivot: String

        if mood == .fragile {
            primary = "Regulate first: 2-minute breathing + send one calm repair message, then do one small high-value task."
            minimum = "Write and send one 2-line repair or appreciation message."
            pivot = "If day stays turbulent, reduce to one non-negotiable task and defer the rest."
        } else if schedule.loadScore >= 75 {
            primary = "Schedule overload mode: convert one meeting to async and execute one 20-minute task tied to \(outcome.lowercased())."
            minimum = "Protect a 10-minute strategic block before next meeting."
            pivot = "If interruptions continue, complete only one decisive communication and one delegation."
        } else if mood == .high {
            primary = "Use high-energy window for deep strategic progress on \(outcome.lowercased())."
            minimum = "Finish one meaningful deliverable in a 25-minute sprint."
            pivot = "If energy drops, switch to concise decision documentation and owner assignment."
        } else {
            primary = "Advance \(outcome.lowercased()) with one focused 30-minute execution block."
            minimum = "Do one 8-minute action that keeps momentum alive."
            pivot = "If day becomes chaotic, cut plan to top 1 action and complete it before evening."
        }

        let accountability = "Tonight, answer: Did today's actions move the \(focus.title) objective forward?"

        return DailyAdaptivePlan(
            generatedAt: .now,
            horizonFocus: focus,
            moodBand: mood,
            primaryAction: primary,
            minimumAction: minimum,
            pivotAction: pivot,
            accountabilityPrompt: accountability
        )
    }

    private func nudgeMessages() -> [String] {
        let plan = state.latestPlan
        let fallback = [
            "You are busy, so keep this small: take 5 minutes for today's highest-leverage action.",
            "Midday reset: if your day is packed, choose one task and complete only that now.",
            "Day-end check: send one appreciation or repair message before closing the day."
        ]
        guard let plan else { return fallback }

        return [
            "\(plan.horizonFocus.title) focus: \(plan.primaryAction)",
            "If today is heavy, still do this minimum: \(plan.minimumAction)",
            "Pivot reminder: \(plan.pivotAction)"
        ]
    }

    private func persist() {
        store.save(state, to: file)
    }
}
