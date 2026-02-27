import Foundation

final class EvolutionMemoryEngine {
    private static let themeLexicon = [
        "argument", "friend", "board", "team", "family",
        "stress", "donor", "conflict", "sleep", "trust"
    ]

    private let store: LocalStore
    private let messagesFile = "coach_messages.json"
    private let memoryFile = "coach_memory.json"

    private(set) var messages: [CoachMessage]
    private(set) var memory: CoachMemoryProfile

    init(store: LocalStore) {
        self.store = store
        self.messages = store.load([CoachMessage].self, from: messagesFile) ?? []
        self.memory = store.load(CoachMemoryProfile.self, from: memoryFile) ?? .initial
    }

    func append(_ message: CoachMessage) {
        messages.append(message)
        updateMemory(using: message)
        persist()
    }

    func recentContext(limit: Int = 8) -> String {
        let recent = messages.suffix(limit)
        return recent.map { "\($0.role.rawValue): \($0.text)" }.joined(separator: "\n")
    }

    func recentThemes(limit: Int = 5) -> [String] {
        var seen = Set<String>()
        var ordered: [String] = []

        for message in messages.reversed() where message.role == .user {
            let lowered = message.text.lowercased()
            for theme in Self.themeLexicon where lowered.contains(theme) {
                if !seen.contains(theme) {
                    seen.insert(theme)
                    ordered.append(theme)
                    if ordered.count >= limit {
                        return ordered
                    }
                }
            }
        }
        return ordered
    }

    private func updateMemory(using message: CoachMessage) {
        let intentKey = message.intent.rawValue
        memory.dominantIntentCounts[intentKey, default: 0] += 1

        let lowered = message.text.lowercased()
        for theme in Self.themeLexicon {
            if lowered.contains(theme) {
                memory.recurringThemes[theme, default: 0] += 1
            }
        }

        if lowered.contains("nahi") || lowered.contains("ya") || lowered.contains("bhai") {
            memory.languagePreference = "en-hi"
        }
        memory.lastUpdated = .now
    }

    private func persist() {
        store.save(messages, to: messagesFile)
        store.save(memory, to: memoryFile)
    }
}
