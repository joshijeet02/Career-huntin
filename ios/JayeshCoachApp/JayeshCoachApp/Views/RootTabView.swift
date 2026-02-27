import SwiftUI

struct RootTabView: View {
    @EnvironmentObject var container: AppContainer
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView(viewModel: container.dashboardVM)
                .tag(0)
                .tabItem {
                    Label("Brief", systemImage: "sun.max")
                }

            CoachConsoleView(viewModel: container.coachConsoleVM)
                .tag(1)
                .tabItem {
                    Label("Coach", systemImage: "message.and.waveform")
                }

            HabitLabView(viewModel: container.habitsVM)
                .tag(2)
                .tabItem {
                    Label("Practice", systemImage: "checklist.checked")
                }

            ReflectionView(viewModel: container.reflectionVM)
                .tag(3)
                .tabItem {
                    Label("Reflect", systemImage: "book.pages")
                }
        }
        .tint(Color.brandPrimary)
        .toolbarBackground(.visible, for: .tabBar)
        .toolbarBackground(Color.brandCard.opacity(0.96), for: .tabBar)
    }
}
