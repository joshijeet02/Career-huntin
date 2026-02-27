import SwiftUI

struct CopilotView: View {
    @ObservedObject var viewModel: CopilotViewModel
    @State private var didAppear = false

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()
                ScrollView {
                    VStack(spacing: 14) {
                        CoachCard(title: "AI Copilot") {
                            Text(viewModel.brief.headline)
                                .font(.coachBody)
                            if viewModel.brief.priorities.isEmpty {
                                Text("Tap Generate to get schedule-aware coaching actions.")
                                    .foregroundStyle(.secondary)
                                    .font(.coachCaption)
                            } else {
                                ForEach(viewModel.brief.priorities, id: \.self) { item in
                                    Text("- \(item)")
                                        .font(.coachBody)
                                }
                            }
                        }

                        CoachCard(title: "Relationship Nudge") {
                            Text(viewModel.brief.relationshipNudge.isEmpty ? "No recommendation yet." : viewModel.brief.relationshipNudge)
                                .font(.coachBody)
                        }

                        CoachCard(title: "Schedule Protection") {
                            Text(viewModel.brief.scheduleProtection.isEmpty ? "No recommendation yet." : viewModel.brief.scheduleProtection)
                                .font(.coachBody)
                        }

                        CoachCard(title: "Risk Alert") {
                            Text(viewModel.brief.riskAlert.isEmpty ? "No alert yet." : viewModel.brief.riskAlert)
                                .font(.coachBody)
                        }

                        CoachCard(title: "Remote AI Settings") {
                            TextField("Coach endpoint", text: $viewModel.endpoint)
                                .textFieldStyle(.roundedBorder)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                            SecureField("API token", text: $viewModel.token)
                                .textFieldStyle(.roundedBorder)

                            HStack(spacing: 8) {
                                Button("Save") { viewModel.saveConfig() }
                                    .buttonStyle(CoachSecondaryButtonStyle())
                                Button(viewModel.isLoading ? "Generating..." : "Generate") {
                                    Task { await viewModel.generateBrief() }
                                }
                                .buttonStyle(CoachPrimaryButtonStyle())
                                .disabled(viewModel.isLoading)
                            }
                        }
                    }
                    .padding(16)
                    .opacity(didAppear ? 1 : 0)
                    .offset(y: didAppear ? 0 : 8)
                }
                .scrollIndicators(.hidden)
            }
            .navigationTitle("Copilot")
            .onAppear {
                withAnimation(.easeOut(duration: 0.3)) {
                    didAppear = true
                }
            }
        }
    }
}
