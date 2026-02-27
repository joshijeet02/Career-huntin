import SwiftUI

struct DashboardView: View {
    @ObservedObject var viewModel: DashboardViewModel

    @State private var energy = 6.0
    @State private var stress = 5.0
    @State private var sleep = 7.0
    @State private var didAppear = false

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()

                ScrollView {
                    VStack(spacing: 16) {
                        hero
                        strategicTimelineCard
                        adaptiveFocusCard
                        calendarCard
                        energyCard

                        ForEach(Array(viewModel.brief.enumerated()), id: \.element.id) { index, item in
                            CoachCard(title: item.title) {
                                Text(item.detail)
                                    .font(.coachBody)
                            }
                            .opacity(didAppear ? 1 : 0)
                            .offset(y: didAppear ? 0 : 8)
                            .animation(
                                .spring(response: 0.45, dampingFraction: 0.86).delay(0.06 * Double(index)),
                                value: didAppear
                            )
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 24)
                }
                .scrollIndicators(.hidden)
            }
            .navigationTitle("Leadership OS")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        viewModel.refresh()
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .foregroundStyle(Color.brandPrimary)
                    }
                }
            }
            .onAppear {
                viewModel.refresh()
                withAnimation(.easeOut(duration: 0.35)) {
                    didAppear = true
                }
            }
        }
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(viewModel.leaderName)
                .font(.coachDisplay)
                .foregroundStyle(.white)
            Text(viewModel.leaderRoleOrganization)
                .font(.coachCaption)
                .foregroundStyle(Color.white.opacity(0.82))

            HStack(spacing: 10) {
                CoachStatChip(label: "Executive", value: "\(viewModel.executiveScore)%")
                CoachStatChip(label: "Relationship", value: "\(viewModel.relationshipScore)%")
                CoachStatChip(label: "Burnout", value: viewModel.burnoutRisk)
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(
                colors: [Color.brandPrimary, Color.brandMoss, Color.brandAccent],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        )
        .shadow(color: Color.brandPrimary.opacity(0.22), radius: 16, x: 0, y: 8)
    }

    private var strategicTimelineCard: some View {
        CoachCard(title: "1M / 3M / 6M / 1Y Growth System") {
            if viewModel.strategicTimeline.isEmpty {
                Text("Timeline is being generated.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(viewModel.strategicTimeline) { goal in
                    HStack(alignment: .top, spacing: 10) {
                        Circle()
                            .fill(Color.brandAccent)
                            .frame(width: 8, height: 8)
                            .padding(.top, 5)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(goal.horizon.title)
                                .font(.coachCaption)
                                .foregroundStyle(Color.brandMoss)
                            Text(goal.objective)
                                .font(.coachBody)
                        }
                    }
                }
            }
        }
    }

    private var adaptiveFocusCard: some View {
        CoachCard(title: "Adaptive Focus") {
            Text(viewModel.todayAdaptiveFocus)
                .font(.coachHeadline)
                .foregroundStyle(Color.brandInk)
        }
    }

    private var energyCard: some View {
        CoachCard(title: "Burnout Sentinel") {
            VStack(alignment: .leading, spacing: 12) {
                sliderRow(label: "Energy", value: $energy, range: 1...10, step: 1)
                sliderRow(label: "Stress", value: $stress, range: 1...10, step: 1)
                sliderRow(label: "Sleep", value: $sleep, range: 3...10, step: 0.5)

                Button("Log Today") {
                    viewModel.logEnergy(energy: Int(energy), stress: Int(stress), sleepHours: sleep)
                }
                .buttonStyle(CoachPrimaryButtonStyle())
            }
        }
    }

    private var calendarCard: some View {
        CoachCard(title: "Calendar Intelligence") {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("Connected")
                        .font(.coachCaption)
                        .foregroundStyle(.secondary)
                    Text(viewModel.calendarConnected ? "Yes" : "No")
                        .font(.coachHeadline)
                    Spacer()
                    Text("Load \(viewModel.scheduleInsights.loadScore)")
                        .font(.coachHeadline)
                        .foregroundStyle(Color.brandPrimary)
                }

                Text(
                    "Meetings \(viewModel.scheduleInsights.meetingCount) | Hours \(String(format: "%.1f", viewModel.scheduleInsights.totalMeetingHours)) | Free block \(viewModel.scheduleInsights.longestFreeBlockMinutes)m"
                )
                .font(.coachCaption)
                .foregroundStyle(.secondary)

                Text(viewModel.scheduleProtection)
                    .font(.coachBody)

                Button(viewModel.isSyncingCalendar ? "Syncing..." : "Connect & Sync Calendar") {
                    Task { await viewModel.connectAndSyncCalendar() }
                }
                .buttonStyle(CoachSecondaryButtonStyle())
                .disabled(viewModel.isSyncingCalendar)

                if !viewModel.calendarEvents.isEmpty {
                    VStack(alignment: .leading, spacing: 5) {
                        ForEach(viewModel.calendarEvents.prefix(4)) { event in
                            Text("\(event.startDate.formatted(date: .omitted, time: .shortened))  \(event.title)")
                                .font(.coachCaption)
                                .foregroundStyle(Color.brandInk.opacity(0.86))
                        }
                    }
                    .padding(.top, 2)
                }
            }
        }
    }

    private func sliderRow(
        label: String,
        value: Binding<Double>,
        range: ClosedRange<Double>,
        step: Double
    ) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(label)
                    .font(.coachCaption)
                Spacer()
                Text(step == 1 ? String(Int(value.wrappedValue)) : String(format: "%.1f", value.wrappedValue))
                    .font(.coachCaption)
                    .foregroundStyle(.secondary)
            }
            Slider(value: value, in: range, step: step)
                .tint(Color.brandPrimary)
        }
    }
}
