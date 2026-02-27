import Foundation

final class ScheduleIntelligence {
    func analyze(events: [CalendarEventSummary], now: Date = .now) -> DailyScheduleInsights {
        let timedEvents = events.filter { !$0.isAllDay }
        guard !timedEvents.isEmpty else { return .empty }

        let meetingSeconds = timedEvents.reduce(0.0) { partial, event in
            partial + max(event.endDate.timeIntervalSince(event.startDate), 0)
        }

        let firstMeeting = timedEvents.first?.startDate
        let lastMeeting = timedEvents.last?.endDate

        var longestFree: TimeInterval = 0
        let dayStart = Calendar.current.startOfDay(for: now)
        let dayEnd = Calendar.current.date(byAdding: .day, value: 1, to: dayStart) ?? now

        var pointer = dayStart
        for event in timedEvents {
            let gap = event.startDate.timeIntervalSince(pointer)
            longestFree = max(longestFree, gap)
            pointer = max(pointer, event.endDate)
        }
        longestFree = max(longestFree, dayEnd.timeIntervalSince(pointer))

        let meetingHours = meetingSeconds / 3600
        let loadScore = Self.loadScore(meetingCount: timedEvents.count, meetingHours: meetingHours, longestFreeMinutes: Int(longestFree / 60))

        return DailyScheduleInsights(
            meetingCount: timedEvents.count,
            totalMeetingHours: meetingHours,
            longestFreeBlockMinutes: Int(longestFree / 60),
            firstMeeting: firstMeeting,
            lastMeeting: lastMeeting,
            loadScore: loadScore
        )
    }

    private static func loadScore(meetingCount: Int, meetingHours: Double, longestFreeMinutes: Int) -> Int {
        var score = 0
        score += min(meetingCount * 8, 40)
        score += min(Int(meetingHours * 10), 40)
        if longestFreeMinutes < 60 { score += 20 }
        else if longestFreeMinutes < 90 { score += 10 }
        return min(max(score, 0), 100)
    }

    func protectionSuggestion(for insight: DailyScheduleInsights) -> String {
        if insight.loadScore >= 75 {
            return "Schedule is overloaded. Protect one 45-minute focus block and decline one low-leverage meeting."
        }
        if insight.longestFreeBlockMinutes < 90 {
            return "No deep-work window detected. Create a 60-minute strategic block in the afternoon."
        }
        return "Your schedule has workable capacity. Reserve the longest free block for strategic planning."
    }
}
