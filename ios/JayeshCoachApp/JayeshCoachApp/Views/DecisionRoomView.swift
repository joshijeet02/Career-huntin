import SwiftUI

struct DecisionRoomView: View {
    @ObservedObject var viewModel: DecisionRoomViewModel
    @State private var didAppear = false

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()
                ScrollView {
                    VStack(spacing: 14) {
                        CoachCard(title: "Decision Quality") {
                            HStack {
                                Text("Score")
                                Spacer()
                                Text("\(viewModel.qualityScore)%")
                                    .font(.coachHeadline)
                            }
                            ProgressView(value: Double(viewModel.qualityScore), total: 100)
                                .tint(Color.brandAccent)
                        }

                        CoachCard(title: "Canvas") {
                            Group {
                                TextField("Decision topic", text: $viewModel.activeCanvas.topic)
                                TextField("Desired impact", text: $viewModel.activeCanvas.desiredImpact)
                                TextField("Final decision", text: $viewModel.activeCanvas.decision)
                            }
                            .textFieldStyle(.roundedBorder)

                            HStack {
                                Button("Seed Template") {
                                    viewModel.seedTemplate(
                                        for: viewModel.activeCanvas.topic.isEmpty ? "Strategic Partnership" : viewModel.activeCanvas.topic
                                    )
                                }
                                .buttonStyle(CoachSecondaryButtonStyle())

                                Button("Save") { viewModel.save() }
                                    .buttonStyle(CoachPrimaryButtonStyle())
                            }
                        }

                        CoachCard(title: "Pre-mortem") {
                            ForEach(viewModel.prompts, id: \.self) { prompt in
                                Text("- \(prompt)")
                                    .font(.coachBody)
                            }
                        }

                        CoachCard(title: "Recent Decisions") {
                            if viewModel.recentDecisions.isEmpty {
                                Text("No decisions logged yet.")
                                    .foregroundStyle(.secondary)
                            } else {
                                ForEach(viewModel.recentDecisions.prefix(5)) { item in
                                    VStack(alignment: .leading) {
                                        Text(item.topic.isEmpty ? "Untitled" : item.topic)
                                            .font(.coachHeadline)
                                        Text(item.decision.isEmpty ? "Pending" : item.decision)
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
            .navigationTitle("Decision Room")
            .onChange(of: viewModel.activeCanvas.topic) { _, _ in viewModel.recalculate() }
            .onChange(of: viewModel.activeCanvas.desiredImpact) { _, _ in viewModel.recalculate() }
            .onChange(of: viewModel.activeCanvas.decision) { _, _ in viewModel.recalculate() }
            .onAppear {
                withAnimation(.easeOut(duration: 0.3)) {
                    didAppear = true
                }
            }
        }
    }
}
