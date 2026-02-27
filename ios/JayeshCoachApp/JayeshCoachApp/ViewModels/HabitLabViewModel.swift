import Foundation

final class HabitLabViewModel: ObservableObject {
    @Published private(set) var habits: [DailyHabit] = []
    @Published private(set) var execScore: Int = 0
    @Published private(set) var relationScore: Int = 0

    private let engine: HabitEngine

    init(engine: HabitEngine) {
        self.engine = engine
        refresh()
    }

    func complete(_ habit: DailyHabit) {
        engine.complete(habitID: habit.id)
        refresh()
    }

    func refresh() {
        habits = engine.habits
        execScore = engine.weeklyScore(track: .executive)
        relationScore = engine.weeklyScore(track: .relationship)
    }
}
