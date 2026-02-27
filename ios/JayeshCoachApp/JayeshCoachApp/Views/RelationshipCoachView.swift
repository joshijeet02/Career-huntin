import SwiftUI

struct RelationshipCoachView: View {
    @ObservedObject var viewModel: RelationshipViewModel
    @State private var didAppear = false

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()
                ScrollView {
                    VStack(spacing: 14) {
                        CoachCard(title: "Relationship Health") {
                            HStack {
                                Text("Weekly score")
                                Spacer()
                                Text("\(viewModel.healthScore)%")
                                    .font(.coachHeadline)
                            }
                            ProgressView(value: Double(viewModel.healthScore), total: 100)
                                .tint(Color.brandAccent)
                        }

                        CoachCard(title: "Conflict Prep") {
                            TextField("Conversation topic", text: $viewModel.prepTopic)
                                .textFieldStyle(.roundedBorder)
                            Button("Generate") {
                                viewModel.generatePrep()
                            }
                            .buttonStyle(CoachPrimaryButtonStyle())

                            ForEach(viewModel.prepPrompts, id: \.self) { line in
                                Text("- \(line)")
                                    .font(.coachBody)
                            }
                        }

                        CoachCard(title: "Daily Check-in") {
                            Group {
                                TextField("Gratitude line", text: $viewModel.gratitude)
                                TextField("Unresolved topic", text: $viewModel.unresolvedTopic)
                                TextField("Repair phrase", text: $viewModel.repairPhrase)
                            }
                            .textFieldStyle(.roundedBorder)

                            Button("Save Check-in") {
                                viewModel.saveCheckin()
                            }
                            .buttonStyle(CoachPrimaryButtonStyle())
                        }

                        CoachCard(title: "Recent Entries") {
                            if viewModel.checkins.isEmpty {
                                Text("No check-ins yet")
                                    .foregroundStyle(.secondary)
                            } else {
                                ForEach(viewModel.checkins.prefix(5)) { item in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(item.gratitude.isEmpty ? "No gratitude entered" : item.gratitude)
                                            .font(.coachBody)
                                        if !item.repairPhrase.isEmpty {
                                            Text("Repair: \(item.repairPhrase)")
                                                .font(.coachCaption)
                                                .foregroundStyle(.secondary)
                                        }
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
            .navigationTitle("Relationship Coach")
            .onAppear {
                withAnimation(.easeOut(duration: 0.3)) {
                    didAppear = true
                }
            }
        }
    }
}
