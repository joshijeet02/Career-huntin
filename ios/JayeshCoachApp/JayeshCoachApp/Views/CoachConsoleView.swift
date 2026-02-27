import SwiftUI

struct CoachConsoleView: View {
    @ObservedObject var viewModel: CoachConsoleViewModel
    @State private var didAppear = false

    var body: some View {
        NavigationStack {
            ZStack {
                CoachBackdrop()

                VStack(spacing: 10) {
                    contextPanel
                    conversationPane
                    composer
                }
                .padding(.horizontal, 12)
                .padding(.top, 6)
                .padding(.bottom, 8)
            }
            .navigationTitle("Coach")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                await viewModel.prepareSpeech()
                withAnimation(.easeOut(duration: 0.32)) {
                    didAppear = true
                }
            }
        }
    }

    private var contextPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Operating Context")
                .font(.coachCaption)
                .foregroundStyle(Color.brandPrimary.opacity(0.8))
                .padding(.horizontal, 4)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(viewModel.timelineGoals) { goal in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(goal.horizon.title)
                                .font(.coachCaption)
                                .foregroundStyle(Color.brandMoss)
                            Text(goal.objective)
                                .font(.coachBody)
                                .lineLimit(2)
                        }
                        .padding(10)
                        .frame(width: 218, alignment: .leading)
                        .coachCardSurface()
                    }
                }
                .padding(.vertical, 2)
            }

            if let plan = viewModel.adaptivePlan {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Today \(plan.horizonFocus.title) | Mood \(plan.moodBand.rawValue)")
                        .font(.coachCaption)
                        .foregroundStyle(.secondary)
                    Text(plan.minimumAction)
                        .font(.coachBody)
                        .lineLimit(2)
                }
                .padding(10)
                .coachCardSurface()
            }

            if let question = viewModel.pendingDiscoveryQuestion {
                Text("Calibration: \(question)")
                    .font(.coachCaption)
                    .foregroundStyle(Color.brandInk.opacity(0.82))
                    .padding(.horizontal, 4)
            }

            if !viewModel.researchBriefs.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(viewModel.researchBriefs.prefix(3)) { brief in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Research \(brief.category)")
                                    .font(.coachCaption)
                                    .foregroundStyle(Color.brandAccent)
                                Text(brief.takeaway)
                                    .font(.coachBody)
                                    .lineLimit(3)
                            }
                            .padding(10)
                            .frame(width: 240, alignment: .leading)
                            .coachCardSurface()
                        }
                    }
                    .padding(.vertical, 2)
                }
            }
        }
        .padding(10)
        .coachCardSurface()
        .opacity(didAppear ? 1 : 0)
        .offset(y: didAppear ? 0 : -6)
    }

    private var conversationPane: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 11) {
                    ForEach(viewModel.messages) { message in
                        HStack {
                            if message.role == .coach {
                                bubble(message.text, isCoach: true)
                                Spacer(minLength: 44)
                            } else {
                                Spacer(minLength: 44)
                                bubble(message.text, isCoach: false)
                            }
                        }
                        .id(message.id)
                    }
                }
                .padding(.horizontal, 6)
                .padding(.vertical, 12)
            }
            .scrollIndicators(.hidden)
            .onChange(of: viewModel.messages.count) { _, _ in
                if let last = viewModel.messages.last {
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(Color.white.opacity(0.58))
                    .overlay(
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(Color.white.opacity(0.65), lineWidth: 1)
                    )
            )
        }
    }

    private var composer: some View {
        VStack(spacing: 10) {
            DisclosureGroup("Backend Connection") {
                VStack(spacing: 8) {
                    TextField("Backend URL (https://your-api.onrender.com)", text: $viewModel.backendEndpoint)
                        .textFieldStyle(.roundedBorder)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Backend API key", text: $viewModel.backendAPIKey)
                        .textFieldStyle(.roundedBorder)
                    Button("Save Connection") {
                        viewModel.saveBackendConfig()
                    }
                    .buttonStyle(CoachSecondaryButtonStyle())
                }
                .padding(.top, 4)
            }
            .font(.coachCaption)

            HStack(alignment: .bottom, spacing: 8) {
                TextField("Type or speak in Hindi/English...", text: $viewModel.draftText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(1...3)

                Button(viewModel.isListening ? "Stop" : "Mic") {
                    viewModel.toggleListening()
                }
                .buttonStyle(CoachSecondaryButtonStyle())
            }

            HStack(spacing: 8) {
                Picker("Voice", selection: $viewModel.selectedVoice) {
                    ForEach(CoachVoice.allCases) { voice in
                        Text(voice.rawValue).tag(voice)
                    }
                }
                .pickerStyle(.segmented)

                Button("Speak") {
                    viewModel.speakLastResponse()
                }
                .buttonStyle(CoachSecondaryButtonStyle())

                Button(viewModel.isBusy ? "Working..." : "Send") {
                    viewModel.sendMessage()
                }
                .buttonStyle(CoachPrimaryButtonStyle())
                .disabled(viewModel.isBusy)
            }
        }
        .padding(12)
        .coachCardSurface()
    }

    private func bubble(_ text: String, isCoach: Bool) -> some View {
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
