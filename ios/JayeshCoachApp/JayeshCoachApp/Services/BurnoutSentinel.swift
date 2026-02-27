import Foundation

final class BurnoutSentinel {
    private let store: LocalStore
    private let file = "energy_checkins.json"

    private(set) var entries: [EnergyCheckin]

    init(store: LocalStore) {
        self.store = store
        self.entries = store.load([EnergyCheckin].self, from: file) ?? []
    }

    func log(_ entry: EnergyCheckin) {
        entries.insert(entry, at: 0)
        entries = Array(entries.prefix(30))
        store.save(entries, to: file)
    }

    func riskBand() -> String {
        guard !entries.isEmpty else { return "Moderate" }
        let recent = Array(entries.prefix(7))
        let avgEnergy = recent.map(\.energy).reduce(0, +) / max(recent.count, 1)
        let avgStress = recent.map(\.stress).reduce(0, +) / max(recent.count, 1)
        if avgEnergy <= 4 || avgStress >= 8 {
            return "High"
        }
        if avgEnergy >= 7 && avgStress <= 5 {
            return "Low"
        }
        return "Moderate"
    }

    func intervention() -> String {
        switch riskBand() {
        case "High":
            return "Block a 90-minute recovery window today. Cancel one non-essential meeting and delegate one task."
        case "Low":
            return "Maintain your rhythm. Protect sleep and keep one no-meeting focus block tomorrow."
        default:
            return "Do a 15-minute reset: walk, breathe, and rewrite today's top 3 priorities."
        }
    }
}
