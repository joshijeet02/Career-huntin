import EventKit
import Foundation

final class CalendarService {
    private let store = EKEventStore()

    func requestAccess() async -> Bool {
        do {
            if #available(iOS 17.0, *) {
                return try await store.requestFullAccessToEvents()
            } else {
                return try await withCheckedThrowingContinuation { continuation in
                    store.requestAccess(to: .event) { granted, error in
                        if let error {
                            continuation.resume(throwing: error)
                        } else {
                            continuation.resume(returning: granted)
                        }
                    }
                }
            }
        } catch {
            return false
        }
    }

    func eventsForToday() -> [CalendarEventSummary] {
        let calendar = Calendar.current
        let start = calendar.startOfDay(for: .now)
        let end = calendar.date(byAdding: .day, value: 1, to: start) ?? .now
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: nil)

        return store.events(matching: predicate)
            .sorted { $0.startDate < $1.startDate }
            .map {
                CalendarEventSummary(
                    id: $0.eventIdentifier ?? UUID().uuidString,
                    title: $0.title ?? "Untitled",
                    startDate: $0.startDate,
                    endDate: $0.endDate,
                    isAllDay: $0.isAllDay
                )
            }
    }
}
