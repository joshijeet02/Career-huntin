import Foundation

final class HabitEngine {
    private let profile: JayeshProfile
    private let store: LocalStore
    private let file = "habits.json"

    private(set) var habits: [DailyHabit]

    init(profile: JayeshProfile, store: LocalStore) {
        self.profile = profile
        self.store = store
        self.habits = store.load([DailyHabit].self, from: file) ?? HabitEngine.defaultHabits()
    }

    static func defaultHabits() -> [DailyHabit] {
        [
            DailyHabit(title: "Morning Mission Alignment", prompt: "What 3 outcomes matter most for community impact today?", track: .executive, targetPerWeek: 6),
            DailyHabit(title: "Stakeholder Check-in", prompt: "One proactive reach-out to board, donor, or field leader.", track: .executive, targetPerWeek: 5),
            DailyHabit(title: "Delegation with Clarity", prompt: "Delegate one critical item with owner, quality bar, and deadline.", track: .executive, targetPerWeek: 5),
            DailyHabit(title: "Appreciation Ritual", prompt: "Express one sincere appreciation to partner/family.", track: .relationship, targetPerWeek: 7),
            DailyHabit(title: "Conflict Repair", prompt: "If friction happened, initiate repair in <24h.", track: .relationship, targetPerWeek: 3),
            DailyHabit(title: "Evening Reflection", prompt: "Where did stress leak into relationships, and how will you correct?", track: .relationship, targetPerWeek: 6)
        ]
    }

    func complete(habitID: UUID) {
        guard let idx = habits.firstIndex(where: { $0.id == habitID }) else { return }
        habits[idx].completions += 1
        persist()
    }

    func weeklyScore(track: CoachingTrack? = nil) -> Int {
        let filtered = track == nil ? habits : habits.filter { $0.track == track }
        let completed = filtered.map(\.completions).reduce(0, +)
        let target = max(filtered.map(\.targetPerWeek).reduce(0, +), 1)
        return Int((Double(completed) / Double(target)) * 100)
    }

    func resetWeeklyIfNeeded() {
        let calendar = Calendar.current
        let markerFile = "habit_week_marker.json"
        let now = Date()
        let currentWeek = calendar.component(.weekOfYear, from: now)
        let previousWeek = store.load(Int.self, from: markerFile)
        guard previousWeek != currentWeek else { return }
        habits = habits.map {
            DailyHabit(id: $0.id, title: $0.title, prompt: $0.prompt, track: $0.track, targetPerWeek: $0.targetPerWeek, completions: 0)
        }
        store.save(currentWeek, to: markerFile)
        persist()
    }

    private func persist() {
        store.save(habits, to: file)
    }

    func profileAwareTip() -> String {
        let focus = profile.missionPriorities.randomElement() ?? "community impact"
        return "Anchor one leadership choice today to \(focus.lowercased())."
    }
}
