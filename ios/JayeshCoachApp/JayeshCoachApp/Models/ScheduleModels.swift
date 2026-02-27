import Foundation

struct CalendarEventSummary: Identifiable, Hashable {
    let id: String
    let title: String
    let startDate: Date
    let endDate: Date
    let isAllDay: Bool
}

struct DailyScheduleInsights {
    let meetingCount: Int
    let totalMeetingHours: Double
    let longestFreeBlockMinutes: Int
    let firstMeeting: Date?
    let lastMeeting: Date?
    let loadScore: Int

    static let empty = DailyScheduleInsights(
        meetingCount: 0,
        totalMeetingHours: 0,
        longestFreeBlockMinutes: 0,
        firstMeeting: nil,
        lastMeeting: nil,
        loadScore: 0
    )
}

struct CopilotBrief {
    let headline: String
    let priorities: [String]
    let relationshipNudge: String
    let scheduleProtection: String
    let riskAlert: String
}
