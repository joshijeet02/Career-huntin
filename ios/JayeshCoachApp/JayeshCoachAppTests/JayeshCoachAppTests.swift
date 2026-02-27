import XCTest
@testable import JayeshCoachApp

final class JayeshCoachAppTests: XCTestCase {
    func testDecisionQualityScoreImprovesWithInputs() {
        let store = LocalStore()
        let engine = DecisionEngine(profile: .seed, store: store)
        var canvas = DecisionCanvas(topic: "", desiredImpact: "", options: [], assumptions: [], risks: [], decision: "")
        let baseline = engine.qualityScore(for: canvas)

        canvas.topic = "Expand livelihood program"
        canvas.desiredImpact = "Improve resilience across 2 districts"
        canvas.options = ["A", "B", "C"]
        canvas.assumptions = ["Assumption 1", "Assumption 2"]
        canvas.risks = ["Risk 1", "Risk 2"]
        canvas.decision = "Pilot Option B"
        let improved = engine.qualityScore(for: canvas)

        XCTAssertGreaterThan(improved, baseline)
        XCTAssertEqual(improved, 100)
    }

    func testRelationshipHealthHasSafeBounds() {
        let store = LocalStore()
        let engine = RelationshipEngine(profile: .seed, store: store)
        let score = engine.weeklyHealthScore()
        XCTAssertGreaterThanOrEqual(score, 0)
        XCTAssertLessThanOrEqual(score, 100)
    }

    func testScheduleIntelligenceReturnsLoadScoreBounds() {
        let now = Date()
        let events = [
            CalendarEventSummary(id: "1", title: "A", startDate: now, endDate: now.addingTimeInterval(3600), isAllDay: false),
            CalendarEventSummary(id: "2", title: "B", startDate: now.addingTimeInterval(5400), endDate: now.addingTimeInterval(9000), isAllDay: false)
        ]
        let intel = ScheduleIntelligence()
        let insight = intel.analyze(events: events, now: now)
        XCTAssertGreaterThanOrEqual(insight.loadScore, 0)
        XCTAssertLessThanOrEqual(insight.loadScore, 100)
    }
}
