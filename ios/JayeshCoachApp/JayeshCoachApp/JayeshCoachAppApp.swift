import SwiftUI

@main
struct JayeshCoachAppApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @State private var container: AppContainer
    @State private var needsOnboarding: Bool

    init() {
        let profile = CoachProfileRepository.load()
        _container = State(initialValue: AppContainer(profile: profile))
        _needsOnboarding = State(initialValue: !profile.interviewCompleted)
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if needsOnboarding {
                    OnboardingInterviewView { profile in
                        CoachProfileRepository.save(profile)
                        container = AppContainer(profile: profile)
                        needsOnboarding = false
                    }
                } else {
                    RootTabView()
                        .environmentObject(container)
                        .onChange(of: scenePhase) { _, newValue in
                            if newValue == .active {
                                container.dashboardVM.onAppBecameActive()
                            }
                        }
                }
            }
            .preferredColorScheme(.light)
        }
    }
}
