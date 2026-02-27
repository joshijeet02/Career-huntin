import SwiftUI

struct OnboardingInterviewView: View {
    @StateObject private var viewModel = OnboardingInterviewViewModel()
    let onComplete: (CoachUserProfile) -> Void

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()

                VStack(spacing: 12) {
                    header
                    interviewPane
                    if viewModel.isComplete {
                        completionPanel
                    } else {
                        composer
                    }
                }
                .padding(12)
            }
            .navigationTitle("Coach Setup")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Personal Calibration Interview")
                .font(.coachTitle)
                .foregroundStyle(Color.brandPrimary)
            Text("This 5-10 minute interview helps the coach adapt to your pressure patterns, priorities, and communication style.")
                .font(.coachBody)
                .foregroundStyle(.secondary)

            ProgressView(value: viewModel.progress)
                .tint(Color.brandPrimary)
            HStack {
                Text(viewModel.progressTitle)
                Spacer()
                Text(viewModel.timeEstimate)
            }
            .font(.coachCaption)
            .foregroundStyle(.secondary)
        }
        .padding(14)
        .coachCardSurface()
    }

    private var interviewPane: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 10) {
                    ForEach(viewModel.turns) { turn in
                        HStack {
                            if turn.speaker == .coach {
                                turnBubble(text: turn.text, isCoach: true)
                                Spacer(minLength: 50)
                            } else {
                                Spacer(minLength: 50)
                                turnBubble(text: turn.text, isCoach: false)
                            }
                        }
                        .id(turn.id)
                    }
                }
                .padding(.horizontal, 6)
                .padding(.vertical, 12)
            }
            .scrollIndicators(.hidden)
            .onChange(of: viewModel.turns.count) { _, _ in
                if let last = viewModel.turns.last {
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(Color.white.opacity(0.55))
                    .overlay(
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(Color.white.opacity(0.7), lineWidth: 1)
                    )
            )
        }
    }

    private var composer: some View {
        VStack(alignment: .leading, spacing: 10) {
            if !viewModel.quickReplies.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(viewModel.quickReplies, id: \.self) { option in
                            Button(option) {
                                viewModel.submitCurrentAnswer(override: option)
                            }
                            .buttonStyle(CoachSecondaryButtonStyle())
                        }
                    }
                    .padding(.vertical, 2)
                }
            }

            TextField(viewModel.currentQuestion?.placeholder ?? "Type your answer", text: $viewModel.draftAnswer, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .lineLimit(1...4)

            HStack(spacing: 8) {
                Button("Skip") {
                    viewModel.skipCurrentQuestion()
                }
                .buttonStyle(CoachSecondaryButtonStyle())

                Button("Continue") {
                    viewModel.submitCurrentAnswer()
                }
                .buttonStyle(CoachPrimaryButtonStyle())
            }
        }
        .padding(12)
        .coachCardSurface()
    }

    private var completionPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let profile = viewModel.completedProfile {
                Text("Profile ready for \(profile.name)")
                    .font(.coachHeadline)
                    .foregroundStyle(Color.brandPrimary)
                Text("\(profile.role) • \(profile.organization)")
                    .font(.coachCaption)
                    .foregroundStyle(.secondary)
                Text("Mission focus: \(profile.missionPriorities.prefix(3).joined(separator: " | "))")
                    .font(.coachBody)
            }

            Button("Start My Coach OS") {
                guard let profile = viewModel.completedProfile else { return }
                onComplete(profile)
            }
            .buttonStyle(CoachPrimaryButtonStyle())
        }
        .padding(12)
        .coachCardSurface()
    }

    private func turnBubble(text: String, isCoach: Bool) -> some View {
        Text(text)
            .font(.coachBody)
            .foregroundStyle(isCoach ? Color.brandInk : .white)
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(
                        isCoach
                        ? AnyShapeStyle(Color.white.opacity(0.88))
                        : AnyShapeStyle(
                            LinearGradient(
                                colors: [Color.brandPrimary, Color.brandMoss],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(isCoach ? Color.brandPrimary.opacity(0.08) : Color.clear, lineWidth: 1)
            )
    }
}
