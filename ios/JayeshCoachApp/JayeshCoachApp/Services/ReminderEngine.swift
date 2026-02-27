import Foundation
import UserNotifications

final class ReminderEngine {
    private let center = UNUserNotificationCenter.current()

    func requestPermission() async {
        _ = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
    }

    func scheduleForToday(insight: DailyScheduleInsights) {
        let defaultMessages = [
            insight.loadScore > 75
                ? "Packed day detected. Protect one 45-minute strategic block before noon."
                : "Use your strongest free block today for mission-critical decisions.",
            "Midday reset: keep one high-leverage action moving even on a busy day.",
            "Before closing the day, do one appreciation and one repair check-in."
        ]
        scheduleThreeDailyNudges(messages: defaultMessages)
    }

    func scheduleThreeDailyNudges(messages: [String]) {
        let ids = ["coach-nudge-1", "coach-nudge-2", "coach-nudge-3"]
        center.removePendingNotificationRequests(withIdentifiers: ids)

        let times = [(8, 0), (13, 0), (20, 30)]
        for (idx, id) in ids.enumerated() {
            let message = idx < messages.count ? messages[idx] : "Take 5 minutes for your highest-leverage action."
            let hour = times[idx].0
            let minute = times[idx].1
            schedule(id: id, hour: hour, minute: minute, title: "Jayesh Coach", body: message, repeats: true)
        }
    }

    private func schedule(id: String, hour: Int, minute: Int, title: String, body: String, repeats: Bool) {
        var components = DateComponents()
        components.calendar = Calendar.current
        components.hour = hour
        components.minute = minute

        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: repeats)
        let request = UNNotificationRequest(identifier: id, content: content, trigger: trigger)
        center.add(request)
    }
}
