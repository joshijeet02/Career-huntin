import SwiftUI

struct HabitLabView: View {
    @ObservedObject var viewModel: HabitLabViewModel
    @State private var didAppear = false

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()

                ScrollView {
                    VStack(spacing: 14) {
                        CoachCard(title: "Weekly Scores") {
                            HStack(spacing: 10) {
                                CoachStatChip(label: "Executive", value: "\(viewModel.execScore)%")
                                CoachStatChip(label: "Relationship", value: "\(viewModel.relationScore)%")
                            }
                        }

                        CoachCard(title: "Habits") {
                            if viewModel.habits.isEmpty {
                                Text("No habits configured yet.")
                                    .foregroundStyle(.secondary)
                            } else {
                                ForEach(viewModel.habits) { habit in
                                    VStack(alignment: .leading, spacing: 7) {
                                        Text(habit.title)
                                            .font(.coachHeadline)
                                        Text(habit.prompt)
                                            .font(.coachBody)
                                            .foregroundStyle(.secondary)
                                        HStack {
                                            Text("\(habit.completions)/\(habit.targetPerWeek) this week")
                                                .font(.coachCaption)
                                            Spacer()
                                            Button("Complete") {
                                                viewModel.complete(habit)
                                            }
                                            .buttonStyle(CoachSecondaryButtonStyle())
                                        }
                                    }
                                    .padding(10)
                                    .coachCardSurface()
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
            .navigationTitle("Habit Lab")
            .onAppear {
                viewModel.refresh()
                withAnimation(.easeOut(duration: 0.3)) {
                    didAppear = true
                }
            }
        }
    }
}
