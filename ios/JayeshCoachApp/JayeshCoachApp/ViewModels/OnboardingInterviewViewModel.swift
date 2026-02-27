import Foundation

@MainActor
final class OnboardingInterviewViewModel: ObservableObject {
    @Published var turns: [OnboardingTurn] = []
    @Published var draftAnswer: String = ""
    @Published private(set) var currentIndex: Int = 0
    @Published private(set) var answers: [String: String] = [:]
    @Published private(set) var completedProfile: CoachUserProfile?

    let questions: [OnboardingQuestion]

    init(questions: [OnboardingQuestion] = .interviewFlow) {
        self.questions = questions
        bootstrap()
    }

    var currentQuestion: OnboardingQuestion? {
        guard currentIndex < questions.count else { return nil }
        return questions[currentIndex]
    }

    var quickReplies: [String] {
        currentQuestion?.quickReplies ?? []
    }

    var isComplete: Bool {
        completedProfile != nil
    }

    var progress: Double {
        guard !questions.isEmpty else { return 1.0 }
        return Double(currentIndex) / Double(questions.count)
    }

    var progressTitle: String {
        "Question \(min(currentIndex + 1, questions.count)) of \(questions.count)"
    }

    var timeEstimate: String {
        let remaining = max(questions.count - currentIndex, 0)
        let minMinutes = max(remaining / 2, 1)
        let maxMinutes = max(remaining, 1)
        return "\(minMinutes)-\(maxMinutes) min left"
    }

    func submitCurrentAnswer(override: String? = nil) {
        guard let question = currentQuestion else { return }
        let candidate = (override ?? draftAnswer).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !candidate.isEmpty else { return }

        answers[question.id] = candidate
        turns.append(OnboardingTurn(speaker: .user, text: candidate))
        draftAnswer = ""

        moveToNextQuestion()
    }

    func skipCurrentQuestion() {
        guard currentQuestion != nil else { return }
        turns.append(OnboardingTurn(speaker: .user, text: "Skip for now"))
        moveToNextQuestion()
    }

    private func bootstrap() {
        turns.append(
            OnboardingTurn(
                speaker: .coach,
                text: "Welcome. For the next 5-10 minutes, I will calibrate your executive + relationship coaching system. Precise answers give better outcomes."
            )
        )
        if let first = currentQuestion {
            turns.append(OnboardingTurn(speaker: .coach, text: first.prompt))
        }
    }

    private func moveToNextQuestion() {
        if currentIndex + 1 < questions.count {
            currentIndex += 1
            if let next = currentQuestion {
                turns.append(OnboardingTurn(speaker: .coach, text: next.prompt))
            }
            return
        }
        completedProfile = CoachUserProfile.fromInterview(answers)
        turns.append(
            OnboardingTurn(
                speaker: .coach,
                text: "Calibration complete. I now have enough signal to personalize your 1M / 3M / 6M / 1Y coaching system."
            )
        )
    }
}
