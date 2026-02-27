import SwiftUI

struct ReflectionView: View {
    @ObservedObject var viewModel: ReflectionViewModel
    @State private var didAppear = false

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()
                ScrollView {
                    VStack(spacing: 14) {
                        CoachCard(title: "Weekly Reflection") {
                            Text(viewModel.missionPrompt())
                                .font(.coachBody)
                                .foregroundStyle(.secondary)

                            Group {
                                TextField("Leadership win", text: $viewModel.leadershipWin)
                                TextField("Relationship win", text: $viewModel.relationshipWin)
                                TextField("Top lesson", text: $viewModel.topLesson)
                                TextField("One commitment", text: $viewModel.oneCommitment)
                            }
                            .textFieldStyle(.roundedBorder)

                            Button("Save Reflection") {
                                viewModel.save()
                            }
                            .buttonStyle(CoachPrimaryButtonStyle())
                        }

                        CoachCard(title: "History") {
                            if viewModel.history.isEmpty {
                                Text("No reflections yet")
                                    .foregroundStyle(.secondary)
                            } else {
                                ForEach(viewModel.history.prefix(8)) { reflection in
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text(reflection.leadershipWin)
                                            .font(.coachHeadline)
                                        Text(reflection.oneCommitment)
                                            .font(.coachCaption)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    }
                    .padding(16)
                    .opacity(didAppear ? 1 : 0)
                    .offset(y: didAppear ? 0 : 8)
                }
                .scrollIndicators(.hidden)
            }
            .navigationTitle("Reflect")
            .onAppear {
                withAnimation(.easeOut(duration: 0.3)) {
                    didAppear = true
                }
            }
        }
    }
}
